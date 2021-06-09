import hashlib
import json
import os
import pickle
import threading
import socket
import ssl
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

    def store(self, user: StoredUser):
        self.user_hashes[user.username] = user
        with open(self.path, "a") as key_file:
            key_file.write(f"{user.username},{user.salt.hex()},{user.hashed_password.hex()}\n")

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
        connection.close()

    def send_private_message(self, message, connection) -> None:
        try:
            match = self.active_users[message.receiver_name]
            #deny spoofing of sender name
            sender_match = [k for k in self.active_users if self.active_users[k].connection == connection]
        except KeyError:
            return
        message.sender_name = sender_match[0]
        sending_message_object = pickle.dumps(message)
        match.connection.sendall(sending_message_object)

    def send_group_message(self, message, connection) -> None:
        try:
            user_list = self.groupChats[message.receiver_name]
        except KeyError:
            return
        for user in user_list:
            message_bytes = pickle.dumps(message)
            user.connection.sendall(message_bytes)

    def forward_message(self, message, connection):

        if isinstance(message, SignUpMessage):
            if self.storage.check_user(message.username):
                response_message = MessageResponse.create(2)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
            else:
                self.active_users[message.username] = User(message.username, connection)
                self.storage.store(StoredUser.create(message.username, message.password))
                response_message = MessageResponse.create(1)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
        if isinstance(message, LoginMessage):
            stored_password: int = self.storage.user_hashes[message.username].hashed_password
            salt = self.storage.user_hashes[message.username].salt
            if StoredUser.salted_hash(salt, message.password) == stored_password:
                self.active_users[message.username] = User(message.username, connection)
                response_message = MessageResponse.create(1)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
            else:
                response_message = MessageResponse.create(3)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
        elif isinstance(message, PrivateTextMessage):
            # TODO log
            self.send_private_message(message, connection)
        elif isinstance(message, GroupTextMessage):
            self.send_group_message(message, connection)
        elif isinstance(message, CreateGroupMessage):
            if message.group_name in self.groupChats.keys():
                if self.active_users[message.username] in self.groupChats[message.group_name]:
                    return
                #TODO this is spoofable check for connection and match to username --otherwise anyone can sign a stranger up to a groupchat
                self.groupChats[message.group_name].append(User(message.username, connection))
            else:
                self.groupChats[message.group_name] = [User(message.username, connection)]
        elif isinstance(message, AttachmentMessage):
            # save file locally
            # TODO prevent overwriting already existing files
            try:
                with open(message.filename, "wb") as attachment:
                    attachment.write(message.content)
            except IOError as e:
                print(f"Could not write file to server: {e}")
            if message.receiver_msg_type == MessageType.PrivateTextMessage:
                self.send_private_message(message, connection)
            elif message.receiver_msg_type == MessageType.GroupTextMessage:
                self.send_group_message(message, connection)
            else:
                raise AssertionError("Invalid receiver message type!")

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
                self.start_connection_thread(secure_connection)
            except socket.timeout:
                continue
        self.receive_socket.close()


def run_server():
    chat_server = ChatServer()
    print("stared Server on Ip: %s on port: %i\n", (chat_server.host_ip, chat_server.port))
    chat_server.start_receiver_thread()
    while True:
        user_input = input("type exit to close ServerApplication\n")
        print(user_input)
        if user_input == "exit":
            chat_server.is_receiving = False
            print("closing Server gracefully please Wait")
            break
        if user_input == "show users":
            print(chat_server.active_users)
        if user_input == "show storage":
            chat_server.storage.print_user_hashes()
        if user_input == "show groups":
            print(chat_server.groupChats)
    for thread in threading.enumerate():
        print(thread.name)
