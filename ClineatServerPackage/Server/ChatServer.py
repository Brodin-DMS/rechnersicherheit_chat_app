import hashlib
import json
import os
import pickle
import threading
import socket
import ssl
import logging
import sqlite3
# FIXME this is bad and should later be replaced with an import as ...
from MessagePackage.Message import *

HOSTNAME = "localhost"
HOSTPORT = 55443
CERTIFICATE_PATH = "chatcert.crt"
PRIVATE_KEY_PATH = "chatcert.key"

BUFFERSIZE = 1024
# maximum size of a message that can be received (mostly important for file
# attachments) to prevent DOS by using large files
MAX_MSG_SIZE = 1048576

class User:
    def __init__(self, username, connection):
        self.username = username
        self.connection = connection


class GroupChat:
    def __init__(self, group_name):
        self.group_name = group_name
        self.users = []


class StoredUser:
    def __init__(self, username: str, salt: bytes, password: bytes):
        self.username: str = username
        self.salt: bytes = salt
        self.hashed_password: bytes = password

    @staticmethod
    def create(username: str, password: str):
        salt: bytes = os.urandom(32)
        return StoredUser(username, salt, StoredUser.salted_hash(salt, password))

    @staticmethod
    def salted_hash(salt, password):
        return hashlib.pbkdf2_hmac(
            'sha256',  # The hash digest algorithm for HMAC
            password.encode('utf-8'),  # Convert the password to bytes
            salt,  # Provide the salt
            100000  # It is recommended to use at least 100,000 iterations of SHA-256
        )


class Storage:
    def __init__(self, path: str):
        self.path: str = path
        self.user_hashes = dict()
        self.load()
        #create database for history
        self.con = sqlite3.connect('history.db')
        self.cur = self.con.cursor()
        self.cur.execute('''CREATE TABLE IF NOT EXISTS private_history
        (id INTEGER PRIMARY KEY, sender_name TEXT NOT NULL, receiver_name TEXT NOT NULL, message TEXT, attachment BLOB)''')
        self.cur.execute('''CREATE TABLE IF NOT EXISTS group_history
        (id INTEGER PRIMARY KEY, sender_name TEXT NOT NULL, group_name TEXT NOT NULL, message TEXT, attachment BLOB)''')
        #TODO add user/pwd data to database
        self.con.commit()
        self.con.close()

    def store(self, user: StoredUser):
        self.user_hashes[user.username] = user
        with open(self.path, "a") as key_file:
            key_file.write(f"{user.username},{user.salt.hex()},{user.hashed_password.hex()}\n")
        logging.info("Stored user '%s'", user.username)

    def load(self):
        try:
            with open(self.path, "r") as key_file:
                lines = key_file.readlines()
                for line in lines:
                    username, salt, hashed_password = line.rstrip().split(",")
                    new_user = StoredUser(username,
                                          bytes.fromhex(salt),
                                          bytes.fromhex(hashed_password))
                    self.user_hashes[username] = new_user
        except FileNotFoundError:
            logging.warning("Storage file '%s' not found", self.path)
            pass

    def check_user(self, username: str) -> bool:
        return username in self.user_hashes

    def print_user_hashes(self):
        for stored_user in self.user_hashes.values():
            print(f"{stored_user.username}")


class ChatServer:
    def __init__(self):
        self.port = HOSTPORT
        self.host_ip = socket.gethostbyname(HOSTNAME)
        self.active_users = dict()
        self.groupChats = dict()
        self.group_chat_message_history = []
        self.private_chat_message_history = []
        self.is_receiving = True
        self.receive_socket = None
        self.storage: Storage = Storage("storage.csv")

    @staticmethod
    def print_to_screen(message):
        print("%i: %s", (message.senderId, message.content))

    def start_receiver_thread(self):
        receiver_thread = threading.Thread(target=self.receive_message)
        receiver_thread.start()

    def start_connection_thread(self, connection):
        threading.Thread(target=self.connection_receive_message, args=(connection,)).start()

    def connection_receive_message(self, connection):
        logging.info("Handling connection to %s:%d",
                     connection.getpeername()[0],
                     connection.getpeername()[1])
        connection_is_alive = True
        connection.settimeout(10.0)
        while connection_is_alive and self.is_receiving:
            try:
                # FIXME DRY: This exact code fragment is also used in ChatClient.receive_messages(...)
                data = b''
                while True:
                    part = connection.recv(BUFFERSIZE)
                    data += part
                    # stop receiving when nothing is received or the upper
                    # limit of the message size is reached
                    if len(part) < BUFFERSIZE or len(part) > MAX_MSG_SIZE:
                        break
                message_object = pickle.loads(data)
                self.forward_message(message_object, connection)
            except EOFError:
                match = [k for k in self.active_users if self.active_users[k].connection == connection]
                if match:
                    self.active_users.pop(match[0])
                connection_is_alive = False
            except pickle.UnpicklingError:
                print(f"Invalid attachment: The chosen attachment is larger than the current buffer size of {BUFFERSIZE} bytes.")
                continue
            except socket.timeout:
                continue
        logging.info("Closing connection to %s:%d",
                     connection.getpeername()[0],
                     connection.getpeername()[1])
        connection.close()

    def send_private_message(self, message, connection) -> None:
        logging.info("Forwarding private message from '%s' to '%s'",
             message.sender_name,
             message.receiver_name)
        try:
            match = self.active_users[message.receiver_name]
            #deny spoofing of sender name
            sender_match = [k for k in self.active_users if self.active_users[k].connection == connection]
        except KeyError:
            logging.info("No such user: '%s'", message.receiver_name)
            return
        message.sender_name = sender_match[0]
        sending_message_object = pickle.dumps(message)
        match.connection.sendall(sending_message_object)
        #save to history
        if isinstance(message, PrivateTextMessage):
            # TODO change NONE to attachment once private and group message implement attachment
            private_history_data = (message.sender_name, message.receiver_name, message.content, None)
        elif isinstance(message, AttachmentMessage):
            private_history_data = (message.sender_name, message.receiver_name, None, message.content)
        con = sqlite3.connect('history.db')
        cur = con.cursor()
        cur.execute('INSERT INTO private_history(sender_name, receiver_name, message, attachment) VALUES (?,?,?,?)',
                    private_history_data)
        con.commit()
        con.close()
    def send_group_message(self, message, connection) -> None:
        logging.info("Forwarding group message from '%s' to '%s'",
             message.sender_name,
             message.receiver_name)
        try:
            # deny spoofing of sender name
            sender_match = [k for k in self.active_users if self.active_users[k].connection == connection]
        except KeyError:
            return
        logging.info(f"spoofing of sendername did not occured {message.sender_name == sender_match[0]}")
        try:
            user_list = self.groupChats[message.receiver_name]
        except KeyError:
            logging.info("No such group: '%s'", message.receiver_name)
            return
        message.sender_name = sender_match[0]
        for user in user_list:
            message_bytes = pickle.dumps(message)
            user.connection.sendall(message_bytes)

        #save to history
        if isinstance(message, PrivateTextMessage):
            # TODO change NONE to attachment once private and group message implement attachment
            group_history_data = (message.sender_name, message.receiver_name, message.content, None)
        elif isinstance(message, AttachmentMessage):
            group_history_data = (message.sender_name, message.receiver_name, None, message.content)
        con = sqlite3.connect('history.db')
        cur = con.cursor()
        cur.execute('INSERT INTO group_history(sender_name, group_name, message, attachment) '
                    'VALUES (?,?,?,?)', group_history_data)
        con.commit()
        con.close()

    def forward_message(self, message, connection):

        if isinstance(message, SignUpMessage):
            logging.info("Sign-up attempt from %s:%d with username '%s'",
                          connection.getpeername()[0],
                          connection.getpeername()[1],
                          message.username)
            if self.storage.check_user(message.username):
                response_message = MessageResponse.create(2)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
                logging.info("Username '%s' already in use", message.username)
            else:
                self.active_users[message.username] = User(message.username, connection)
                self.storage.store(StoredUser.create(message.username, message.password))
                response_message = MessageResponse.create(1)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
                logging.info("Sign-up with username '%s' successful", message.username)
        if isinstance(message, LoginMessage):
            logging.info("Login attempt from %s:%d with username '%s'",
                          connection.getpeername()[0],
                          connection.getpeername()[1],
                          message.username)
            stored_password: int = self.storage.user_hashes[message.username].hashed_password
            salt = self.storage.user_hashes[message.username].salt
            if StoredUser.salted_hash(salt, message.password) == stored_password:
                self.active_users[message.username] = User(message.username, connection)
                response_message = MessageResponse.create(1)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
                logging.info("Login with username '%s' successful", message.username)
            else:
                response_message = MessageResponse.create(3)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
                logging.info("Login with username '%s' failed", message.username)
        elif isinstance(message, PrivateTextMessage):
            self.send_private_message(message, connection)
        elif isinstance(message, GroupTextMessage):
            self.send_group_message(message, connection)
        elif isinstance(message, CreateGroupMessage):
            logging.info("User '%s' attempts to create or join group '%s'",
                         message.username,
                         message.group_name)
            if message.group_name in self.groupChats.keys():
                if self.active_users[message.username] in self.groupChats[message.group_name]:
                    return
                #TODO this is spoofable check for connection and match to username --otherwise anyone can sign a stranger up to a groupchat
                self.groupChats[message.group_name].append(User(message.username, connection))
                logging.info("Added user '%s' to group '%s'",
                             message.username,
                             message.group_name)
            else:
                self.groupChats[message.group_name] = [User(message.username, connection)]
                logging.info("Created group '%s'", message.group_name)
                logging.info("Added user '%s' to group '%s'",
                             message.username,
                             message.group_name)
        elif isinstance(message, AttachmentMessage):
            # save file locally
            # TODO prevent overwriting already existing files
            logging.info("User '%s' tries to send attachment '%s'", message.sender_name, message.filename)
            try:
                with open(message.filename, "wb") as attachment:
                    attachment.write(message.content)
            except IOError as e:
                logging.warning(f"Could not write file to server: {e}")
            if message.receiver_msg_type == MessageType.PrivateTextMessage:
                self.send_private_message(message, connection)
            elif message.receiver_msg_type == MessageType.GroupTextMessage:
                self.send_group_message(message, connection)
            else:
                raise AssertionError("Invalid receiver message type!")

        elif isinstance(message, PrivateHistoryRequest):
            try:
                # deny spoofing of sender name
                sender_match = [k for k in self.active_users if self.active_users[k].connection == connection]
            except KeyError:
                return
            message.sender_name = sender_match[0]
            con = sqlite3.connect('history.db')
            cur = con.cursor()
            cur.execute('SELECT * FROM private_history WHERE sender_name = ? AND receiver_name = ? OR  receiver_name = ? AND sender_name = ?',
                                              (message.sender_name, message.receiver_name, message.sender_name, message.receiver_name))
            result = cur.fetchall()
            con.close()
            new_message = PrivateHistoryMessage.create(result)
            sending_message_object = pickle.dumps(new_message)
            connection.sendall(sending_message_object)
        elif isinstance(message, GroupHistoryRequest):
            con = sqlite3.connect('history.db')
            cur = con.cursor()
            cur.execute('SELECT * FROM group_history WHERE group_name = ?', [message.group_name])
            result = cur.fetchall()
            con.close()
            new_message = GroupHistoryMessage.create(result)
            sending_message_object = pickle.dumps(new_message)
            connection.sendall(sending_message_object)
        else:
            # TODO Throw No valid mesageType Execption
            logging.info("Received invalid message object from %s:%d",
                         connection.getpeername()[0],
                         connection.getpeername()[1])
            pass

    def receive_message(self):
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #FIXME Remove the next line for security reasons
        self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.receive_socket.bind((self.host_ip, self.port))
        self.is_receiving = True
        self.receive_socket.listen()
        self.receive_socket.settimeout(5.0)
        while self.is_receiving:
            try:
                connection, address = self.receive_socket.accept()
                # replace unencrypted with tls-encrypted socket
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(CERTIFICATE_PATH, PRIVATE_KEY_PATH)
                secure_connection = context.wrap_socket(connection, server_side=True)
                logging.info("New connection to %s:%d", address[0], address[1])
                self.start_connection_thread(secure_connection)
            except socket.timeout:
                continue
        self.receive_socket.close()


def run_server():
    logging.basicConfig(filename="server.log",
                        format="%(levelname)s %(asctime)s %(threadName)s: %(message)s",
                        level=logging.INFO)
    chat_server = ChatServer()
    chat_server.start_receiver_thread()
    print("Started Server on IP: %s on port: %i" % (chat_server.host_ip, chat_server.port))
    logging.info("Started Server on IP: %s on port: %i", chat_server.host_ip, chat_server.port)
    while True:
        user_input = input("type exit to close ServerApplication\n")
        print(user_input)
        logging.info("User input: '%s'", user_input)
        if user_input == "exit":
            chat_server.is_receiving = False
            print("closing Server gracefully please Wait")
            logging.info("Closing server")
            break
        if user_input == "show users":
            print(chat_server.active_users)
        if user_input == "show storage":
            chat_server.storage.print_user_hashes()
        if user_input == "show groups":
            print(chat_server.groupChats)
    for thread in threading.enumerate():
        print(thread.name)
    logging.shutdown()