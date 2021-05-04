from abc import ABCMeta, abstractmethod
import socket
import threading
import pickle
from ClineatServerPackage.MessagePackage.Message import MessageType, PrivateTextMessage, GroupTextMessage, LoginMessage, \
    LoginResponse


class IChatClient(metaclass=ABCMeta):
    @abstractmethod
    def login(self, username, password):
        """authenticateUserAccount"""

    @abstractmethod
    def send_message(self, content, message_type, receiver_id):
        """SendsNormalChatMessage"""

    @abstractmethod
    def receive_messages(self):
        """"ReiceiverMessages"""

    @abstractmethod
    def print_to_screen(self, message):
        """output data to terminal"""


class ChatClient(IChatClient):
    def __init__(self, sender_id, username, password):
        self.sender_id = sender_id
        self.host_ip = "127.0.0.1"
        self.sender_ip = "127.0.0.1"
        self.host_auth_port = 55443
        self.host_message_port = 55444
        self.client_receiving_port = 37375
        self.is_auth = False
        self.username = username
        self.password = password
        self.is_receiving = False
        self.receiving_sock = None
        self.stop_app = False

    def start_auth_thread(self):
        auth_thread = threading.Thread(target=self.login, args=(self.username, self.password))
        auth_thread.start()

    def start_message_thread(self, content, message_type, receiver_id):
        message_thread = threading.Thread(target=self.send_message, args=(content, message_type, receiver_id))
        message_thread.start()

    def start_receiving_thread(self):
        receiving_thread = threading.Thread(target=self.receive_messages)
        receiving_thread.start()

    # @override
    def login(self, username, password):
        message_object = LoginMessage.Create(username, password, self.sender_id)
        sock = socket.socket()
        sock.connect((self.host_ip, self.host_auth_port))
        data = pickle.dumps(message_object)
        sock.sendall(data)
        login_response = sock.recv(1024)
        login_response_object = pickle.loads(login_response)
        if login_response_object.responseCode == 1:
            print("Login Succsess")
            self.start_receiving_thread()
        else:
            print("Login Failed")
        sock.close()

    def print_to_screen(self, message):
        print("%s: %s", (message.senderId, message.content))

    # @override
    def receive_messages(self):
        self.receiving_sock = socket.socket()
        self.receiving_sock.bind(("127.0.0.1", 37375))
        self.receiving_sock.listen()
        self.is_receiving = True
        connection, address = self.receiving_sock.accept()
        while self.is_receiving:
            received_data = self.receiving_sock.recv(1024)
            received_message = pickle.loads(received_data)
            self.print_to_screen(received_message)
        self.receiving_sock.close()

    # @override
    def send_message(self, content, message_type, receiver_id):
        sock = socket.socket()
        sock.connect((self.host_ip, self.host_message_port))
        message_object = None
        if message_type == MessageType.PrivateTextMessage:
            message_object = PrivateTextMessage.Create(content, self.sender_id, receiver_id)
        elif message_type == MessageType.GroupTextMessage:
            message_object = GroupTextMessage.Create(content, self.sender_id, receiver_id)
        data = pickle.dumps(message_object)
        sock.sendall(data)
        sock.close()

    def exit_application(self):
        self.is_receiving = False
        self.receiving_sock.close()

    def user_input(self):
        while True:
            message_content = input("Type exit to close application or Enter MessagePackage:")
            if message_content == "exit":
                self.exit_application()
                return True
            message_type_input = input(
                "Enter 1 to send message to Group Chat MessagePackage\n 2 to send private message)")
            message_id = input("Please Enter group/person id")
            message_type = PrivateTextMessage if message_type_input == str(2) else GroupTextMessage
            self.start_message_thread(message_content, message_type, message_id)
            return False



if __name__ == "__main__":
    import sys
    user_id = int(sys.argv[1])
    name = str(sys.argv[2])
    password = str(sys.argv[3])
    client = ChatClient(user_id, name, password)
    client.start_auth_thread()
    client.stop_app = False
    client.stop_app = input_thread = threading.Thread(target=client.user_input)
    while not client.stop_app:
        pass

