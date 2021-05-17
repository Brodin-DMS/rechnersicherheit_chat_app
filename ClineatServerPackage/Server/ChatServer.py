import pickle
import threading
import socket
from MessagePackage.Message import PrivateTextMessage, MessageType, \
    GroupTextMessage, BaseMessage, LoginMessage, MessageResponse, CreateGroupMessage


class User:
    def __init__(self, username, connection):
        self.username = username
        self.connection = connection


class GroupChat:
    def __init__(self, group_name):
        self.group_name = group_name
        self.users = []


class ChatServer:
    def __init__(self):
        self.port = 55443
        self.host_ip = socket.gethostbyname("localhost")
        self.active_users = dict()
        self.groupChats = dict()
        self.group_chat_message_history = []
        self.private_chat_message_history = []
        self.is_receiving = True
        self.receive_socket = None

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
        connection.settimeout(5.0)
        while connection_is_alive and self.is_receiving:
            try:
                data = connection.recv(1024)
                message_object = pickle.loads(data)
                self.forward_message(message_object, connection)
            except EOFError:
                match = [k for k in self.active_users if self.active_users[k].connection == connection]
                if match is not None:
                    self.active_users.pop(match[0])
                connection_is_alive = False
            except socket.timeout:
                continue
        connection.close()

    def forward_message(self, message, connection):

        if isinstance(message, LoginMessage):
            #TODO check if authenticated, instead authenticate on login, but im testinf this for now
            self.active_users[message.username] = User(message.username, connection)
            response_message = MessageResponse.create(1)
            response_message_object = pickle.dumps(response_message)
            connection.sendall(response_message_object)
        elif isinstance(message, PrivateTextMessage):
            # TODO log
            try:
                match = self.active_users[message.receiver_name]
                #deny spoofing of sender name
                sender_match = [k for k in self.active_users if self.active_users[k].connection == connection]
            except KeyError:
                return
            message.sender_name = sender_match[0]
            sending_message_object = pickle.dumps(message)
            match.connection.sendall(sending_message_object)
        elif isinstance(message, GroupTextMessage):
            try:
                user_list = self.groupChats[message.receiver_name]
            except KeyError:
                return
            for user in user_list:
                message_bytes = pickle.dumps(message)
                user.connection.sendall(message_bytes)
        elif isinstance(message, CreateGroupMessage):
            if message.group_name in self.groupChats.keys():
                if self.active_users[message.username] in self.groupChats[message.group_name]:
                    return
                #TODO this is spoofable check for connection and match to username --otherwise anyone can sign a stranger up to a groupchat
                self.groupChats[message.group_name].append(User(message.username, connection))
            else:
                self.groupChats[message.group_name] = [User(message.username, connection)]


        else:
            # TODO Throw No valid mesageType Execption
            pass

    def receive_message(self):
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_socket.bind((self.host_ip, self.port))
        self.is_receiving = True
        self.receive_socket.listen()
        self.receive_socket.settimeout(5.0)
        while self.is_receiving:
            try:
                connection, address = self.receive_socket.accept()
                self.start_connection_thread(connection)
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
        if user_input == "show groups":
            print(chat_server.groupChats)
    for thread in threading.enumerate():
        print(thread.name)
