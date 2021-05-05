import pickle
import threading
import socket
from MessagePackage.Message import PrivateTextMessage, MessageType, \
    GroupTextMessage, BaseMessage, LoginMessage, LoginResponse


class User:
    def __init__(self, username, ip, user_id, connection, adress):
        self.username = username
        self.ip = ip
        self.user_id = user_id
        self.connection = connection
        self.adress = adress


class GroupChat:
    def __init__(self, group_name, group_id):
        self.group_name = group_name
        self.users = []
        self.group_id = group_id


class ChatServer:
    def __init__(self):
        self.auth_port = 55443
        self.client_ip = "127.0.0.1"
        self.host_ip = "127.0.0.1"
        self.user_id_counter = 0
        self.users = dict()
        self.group_id_counter = 0
        self.groupChats = dict()
        self.group_chat_message_history = []
        self.private_chat_message_history = []
        self.is_receiving = False
        self.receive_socket = None

    def print_to_screen(self, message):
        print("%s: %s", (message.senderId, message.content))

    def start_message_thread(self, content, message_typ, receiver_id):
        message_thread = threading.Thread(target=self.forward_message, args=(self, content, message_typ, receiver_id))
        message_thread.start()


    def start_receiver_thread(self):
        receiver_thread = threading.Thread(target=self.receive_message)
        receiver_thread.start()

    def start_connection_thread(self, connection, address):
        threading.Thread(target=self.connection_receive_message, args=(connection, address)).start()


    def connection_receive_message(self,connection, address):
        while self.is_receiving:
            print("Server is listening")
            print(connection, address, " socket accepted")
            print("receiving any message")
            data = connection.recv(1024)
            print("received data", data)
            message_object = pickle.loads(data)
            print(type(message_object))
            if isinstance(message_object, LoginMessage):
                #TODO check for creds, store user:passowrds persistent

                self.users[message_object.senderId] = User(message_object.username, address[0], message_object.senderId, connection, address)
                response_message = LoginResponse.Create(1)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
            elif isinstance(message_object, PrivateTextMessage):
                print("receive Private Message")
                #TODO log
                print(self.users)
                print(message_object.receiverId)
                match = self.users[message_object.receiverId]
                print(match)
                sending_message_object = pickle.dumps(message_object)
                match.connection.sendall(sending_message_object )
            elif isinstance(message_object, GroupTextMessage):
                user_list = self.groupChats[message_object.receiverId]
                for u in user_list:
                    u.connection.sendall(message_object)
            else:
                #TODO Throw No valid mesageType Execption
                pass



    def forward_message(self, message, message_type):

        if message_type == MessageType.PrivateTextMessage:
            match = next((user for user in self.users if user.user_id == PrivateTextMessage(message).receiverId), None)
            if match != None:
                sock = socket.socket()
                sock.connect(User(match).ip, User(match).port)
                data = pickle.dumps(message)
                sock.sendall(data)
                sock.close()
        elif message_type == MessageType.GroupTextMessage:
            match = next((group for group in self.groupChats if group.group_id == GroupTextMessage(message).groupId), None)
            if match != None:
                for user in GroupChat(match).users:
                    sock = socket.socket()
                    sock.connect(User(match).ip, User(match).port)
                    data = pickle.dumps(message)
                    sock.sendall(data)
                    sock.close()
        else:
            #TODO throw invalid chat group exception
            pass

    def receive_message(self):
        #nimmt connections an
        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        print("Server created Socket")
        self.receive_socket.bind((self.host_ip, self.auth_port))
        print("Server bound socket")
        self.is_receiving = True
        self.receive_socket.listen()
        while True:
            connection, address = self.receive_socket.accept()
            self.start_connection_thread(connection, address)
            #start thread for connection
        self.receive_socket.close()

def run_server():
    chat_server = ChatServer()
    print("stared Server on Ip: %s on port: %i\n", (chat_server.host_ip, chat_server.auth_port))
    chat_server.start_receiver_thread()
    user_input = input("Control Server Application type\n"
                       "exit to close ServerApplication for type anything to exit anyways")
    chat_server.receive_socket.close()

