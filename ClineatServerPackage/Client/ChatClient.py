from abc import ABCMeta, abstractmethod
import sys
import socket
import threading
import pickle
from MessagePackage.Message import MessageType, PrivateTextMessage, \
    GroupTextMessage, LoginMessage, LoginResponse


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
        self.sender_ip = socket.gethostbyname("localhost")
        self.host_auth_port = 55443
        self.is_auth = False
        self.username = username
        self.password = password
        self.is_receiving = False
        self.receiving_sock = None
        self.stop_app = False
        self.socket = None

    def start_auth_thread(self):
        auth_thread = threading.Thread(target=self.login, args=(self.username, self.password))
        auth_thread.start()

    def start_message_thread(self, content, message_type, receiver_id):
        message_thread = threading.Thread(target=self.send_message, args=(content, message_type, receiver_id))
        message_thread.start()

    # @override
    def login(self, username, password):
        message_object = LoginMessage.Create(username, password, self.sender_id)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host_ip, self.host_auth_port))
        data = pickle.dumps(message_object)
        self.socket.sendall(data)
        login_response = self.socket.recv(1024)
        login_response_object = pickle.loads(login_response)
        if login_response_object.responseCode == 1:
            print("loggin success")
            self.is_receiving = True
            input_thread = threading.Thread(target=self.user_input)
            input_thread.daemon=True
            input_thread.start()
            threading.Thread(target=self.receive_messages()).start()

        else:
            print("Login Failed")
            self.socket.close()

    def print_to_screen(self, message):
        print("%i: %s" % (message.senderId, message.content))

    # @override
    def receive_messages(self):
        self.socket.settimeout(5.0)
        while self.is_receiving:
            try:
                received_data = self.socket.recv(1024)
                received_message = pickle.loads(received_data)
                self.print_to_screen(received_message)
            except socket.timeout:
                continue
            except EOFError:
                print("Server apears to be offline")
                self.exit_application()
                break
        self.socket.close


    # @override
    def send_message(self, content, message_type, receiver_id):
        message_object = None
        if message_type == MessageType.PrivateTextMessage:
            message_object = PrivateTextMessage.Create(content, self.sender_id, receiver_id)
        elif message_type == MessageType.GroupTextMessage:
            message_object = GroupTextMessage.Create(content, self.sender_id, receiver_id)
        else:
            print("throw exc here")
            # TODO noValid messge exception
            pass
        data = pickle.dumps(message_object)
        print("sending data")
        self.socket.sendall(data)

    def exit_application(self):
        self.is_receiving = False

    def user_input(self):
        while self.is_receiving:
            try:
                message_content = input("Type exit to close application or Enter Message:\n")
                if message_content.strip() == "exit":
                    self.exit_application()
                    return True
                message_type_input = int(input(
                    "1 to send message to Group Chat MessagePackage\n 0 to send private message\n"))
                message_id = int(input("Please Enter group/person id\n"))

                message_type = message_type_input
                self.start_message_thread(message_content, message_type, message_id)
            except ValueError:
                print("No valid value")
                continue


def run_client():
    user_id = int(sys.argv[1])
    name = str(sys.argv[2])
    password = str(sys.argv[3])
    client = ChatClient(user_id, name, password)
    client.start_auth_thread()
