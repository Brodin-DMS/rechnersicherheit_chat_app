from abc import ABCMeta, abstractmethod
import sys
import socket
import threading
import pickle
from getpass import getpass
from MessagePackage.Message import MessageType, PrivateTextMessage, \
    GroupTextMessage, LoginMessage, MessageResponse, SignUpMessage, CreateGroupMessage


class ChatClient:
    def __init__(self):
        self.host_ip = "127.0.0.1"
        self.sender_ip = socket.gethostbyname("localhost")
        self.host_port = 55443
        self.is_auth = False
        self.username = None
        self.is_receiving = True
        self.stop_app = False
        self.socket = None
        self.current_message_receiver_name = None
        self.current_message_type = None

    def start_message_thread(self, content, username, receiver_name):
        message_thread = threading.Thread(target=self.send_message, args=(content, username, receiver_name))
        message_thread.start()

    def start_user_input(self):
        user_input_thread = threading.Thread(target=self.user_input)
        user_input_thread.start()

    def sign_up(self, username, password):
        print("trying to sign-up. Please wait...")
        message_object = SignUpMessage.create(username, password)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host_ip, self.host_port))
        data = pickle.dumps(message_object)
        self.socket.sendall(data)
        sign_up_response = self.socket.recv(1024)
        sign_up_response = pickle.loads(sign_up_response)
        if (sign_up_response.responseCode == 1):
            print("sign_up success\n")
            self.is_receiving = True
            self.is_auth = True
            threading.Thread(target=self.receive_messages()).start()
        elif (sign_up_response.responseCode == 2):
            print("username already in use")
            self.socket.close()
        else:
            print("Unknown error during sign_up occured")
            self.socket.close()

    def login(self, username, password):
        print("trying to login. Please wait...")
        message_object = LoginMessage.create(username, password)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.connect((self.host_ip, self.host_port))
        data = pickle.dumps(message_object)
        self.socket.sendall(data)
        login_response = self.socket.recv(1024)
        login_response_object = pickle.loads(login_response)
        if login_response_object.responseCode == 1:
            print("loggin success\n")
            self.is_receiving = True
            self.is_auth = True
            self.username = username
            threading.Thread(target=self.receive_messages).start()
        else:
            print("Login Failed")
            self.socket.close()

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

    def send_message(self, content, username, receiver_name):
        message_object = None
        if content == "--create":
            message_object = CreateGroupMessage(self.username, receiver_name)
        elif self.current_message_type == MessageType.PrivateTextMessage:
            message_object = PrivateTextMessage.create(content, username, receiver_name)
        elif self.current_message_type == MessageType.GroupTextMessage:
            message_object = GroupTextMessage.create(content, username, receiver_name)
        else:
            print("throw exc here")
            # TODO noValid message exception
            pass
        data = pickle.dumps(message_object)
        self.socket.sendall(data)

    def user_input(self):
        print("use --help to list options")
        while self.is_receiving:
            if not self.is_auth:
                login_create_decision = int(input("Enter:\n1) To Login\n2) To Sign-Up\n"))
                if login_create_decision == 1:
                    username = input("Enter Username:")
                    password = getpass("Enter Password:")
                    self.login(username, password)
                elif login_create_decision == 2:
                    username = input("Enter Username:")
                    password = getpass("Enter Password:")
                    self.sign_up(username, password)
                else:
                    print("Command not found")
            else:
                message_content = input()
                if message_content.strip() == "--help":
                    print("--quit ,Exit application\n"
                          "--list ,display all known chats\n"
                          "--swap_to_group groupname ,start chatting with group\n"
                          "--swap_to_person username ,start chatting with person\n"
                          "--create groupname ,create a groupname")
                elif message_content.strip() == "--quit":
                    self.exit_application()
                    return True
                elif message_content.strip() == "--list":
                    # TODO display list of possible chats --therefore we have to keep a list of known users and groups in a file
                    pass
                elif len(message_content.split(" ", 1)) == 2 and message_content.split(" ", 1)[0] == "--swap_to_person":
                    self.current_message_type = MessageType.PrivateTextMessage
                    self.current_message_receiver_name = message_content.split(" ", 1)[1]
                    print("Privatechat with " + self.current_message_receiver_name + ".")
                elif len(message_content.split(" ", 1)) == 2 and message_content.split(" ", 1)[0] == "--swap_to_group":
                    self.current_message_type = MessageType.GroupTextMessage
                    self.current_message_receiver_name = message_content.split(" ", 1)[1]
                    print("Groupchat with " + self.current_message_receiver_name + ".")
                elif len(message_content.split(" ", 1)) == 2 and message_content.split(" ", 1)[0] == "--create":
                    self.start_message_thread("--create", self.username, message_content.split(" ", 1)[1])
                else:
                    if self.current_message_receiver_name is None or self.current_message_type is None:
                        print("Please select a person or group to chat with first.\n")
                    else:
                        self.start_message_thread(message_content, self.username, self.current_message_receiver_name)

    @staticmethod
    def print_to_screen(message):
        print("%s: %s" % (message.sender_name, message.content))

    def exit_application(self):
        print("Quitting, Please wait...")
        self.is_receiving = False


def run_client():
    client = ChatClient()
    client.start_user_input()
