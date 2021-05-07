import pickle
import threading
import socket
from MessagePackage.Message import PrivateTextMessage, MessageType, \
    GroupTextMessage, BaseMessage, LoginMessage, LoginResponse


class User:
    def __init__(self, username, user_id, connection):
        self.username = username
        self.user_id = user_id
        self.connection = connection


class GroupChat:
    def __init__(self, group_name, group_id):
        self.group_name = group_name
        self.users = []
        self.group_id = group_id


class ChatServer:
    def __init__(self):
        self.auth_port = 55443
        self.host_ip = socket.gethostbyname("localhost")
        self.users = dict()
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
                match = [k for k in self.users if self.users[k].connection == connection]
                if match is not None:
                    self.users.pop(match[0])
                connection_is_alive = False
            except socket.timeout:
                continue
        connection.close()

    def forward_message(self, message, connection):

        if isinstance(message, LoginMessage):
            self.users[message.senderId] = User(message.username, message.senderId, connection)
            response_message = LoginResponse.Create(1)
            response_message_object = pickle.dumps(response_message)
            connection.sendall(response_message_object)
        elif isinstance(message, PrivateTextMessage):
            # TODO log
            match = self.users[message.receiverId]
            sending_message_object = pickle.dumps(message)
            match.connection.sendall(sending_message_object)
        elif isinstance(message, GroupTextMessage):
            user_list = self.groupChats[message.receiverId]
            for user in user_list:
                user.connection.sendall(message)
        else:
            # TODO Throw No valid mesageType Execption
            pass

    def receive_message(self):
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_socket.bind((self.host_ip, self.auth_port))
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
    print("stared Server on Ip: %s on port: %i\n", (chat_server.host_ip, chat_server.auth_port))
    chat_server.start_receiver_thread()
    while True:
        user_input = input("type exit to close ServerApplication\n")
        print(user_input)
        if user_input == "exit":
            chat_server.is_receiving = False
            print("closing Server gracefully please Wait")
            break
        if user_input == "show users":
            print(chat_server.users)
        if user_input == "show groups":
            print(chat_server.groupChats)
    for thread in threading.enumerate():
        print(thread.name)
