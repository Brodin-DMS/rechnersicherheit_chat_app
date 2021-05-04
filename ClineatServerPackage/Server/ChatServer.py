import pickle
import threading
import socket
from ClineatServerPackage.MessagePackage.Message import PrivateTextMessage, MessageType, GroupTextMessage, BaseMessage, \
    LoginMessage, LoginResponse


class User:
    def __init__(self, username, ip, port, user_id):
        self.username = username
        self.ip = ip
        self.port = port
        self.user_id = user_id


class GroupChat:
    def __init__(self, group_name, group_id):
        self.group_name = group_name
        self.users = []
        self.group_id = group_id


class ChatServer:
    def __init__(self):
        self.auth_port = 55443
        self.message_port = 55444
        self.client_ip = "127.0.0.1"
        self.host_ip = "127.0.0.1"
        self.client_port = 37375
        self.user_id_counter = 0
        self.users = []
        self.group_id_counter = 0
        self.groupChats = []
        self.group_chat_message_history = []
        self.private_chat_message_history = []
        self.is_receiving = False
        self.receive_socket = None

    def print_to_screen(self, message):
        print("%s: %s", (message.senderId, message.content))

    def start_message_thread(self, content, message_typ, receiver_id):
        message_thread = threading.Thread(target=self.send_message, args=(self, content, message_typ, receiver_id))
        message_thread.start()

    def start_receiver_thread(self):
        receiver_thread = threading.Thread(target=self.receive_message)
        receiver_thread.start()

    def send_message(self, message, message_type):

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
        self.receive_socket = socket.socket()
        print("Server created Socket")
        self.receive_socket.bind((self.host_ip, self.auth_port))
        print("Server bound socket")
        self.is_receiving = True
        while self.is_receiving:
            self.receive_socket.listen()
            print("Server is listening")
            connection, address = self.receive_socket.accept()
            print(connection, address, " socket accepted")
            data = connection.recv(1024)
            print("received data", data)
            message_object = pickle.loads(data)
            if isinstance(message_object, LoginMessage):
                #TODO check for creds, store user:passowrds persistent
                print(address)
                self.users.append(User(message_object.username, address[0], self.client_port, message_object.senderId))
                response_message = LoginResponse.Create(1)
                response_message_object = pickle.dumps(response_message)
                connection.sendall(response_message_object)
            elif isinstance(message_object, PrivateTextMessage):
                #TODO log
                self.start_message_thread(message_object, message_object.messageType)
            elif isinstance(message_object, GroupTextMessage):
                #TODO log
                self.start_message_thread(message_object, message_object.messageType)
            else:
                #TODO Throw No valid mesageType Execption
                pass
        self.receive_socket.close()

if __name__ == "__main__":
    pass
    chat_server = ChatServer()
    print("stared Server on Ip: %s on port: %i\n", (chat_server.host_ip, chat_server.auth_port))
    chat_server.start_receiver_thread()
    user_input = input("Control Server Application type\n"
                       "exit to close ServerApplication for type anything to exit anyways")
    chat_server.receive_socket.close()