from abc import ABCMeta


class BaseMessage(metaclass=ABCMeta):
    def __init__(self, content):
        self.content = content
        self.messageType = None


class PrivateTextMessage(BaseMessage):
    @staticmethod
    def create(content, sender_name, receiver_name):
        return PrivateTextMessage(content, sender_name, receiver_name)

    def __init__(self, content, sender_name, receiver_name):
        super().__init__(content)
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.messageType = MessageType.PrivateTextMessage


class GroupTextMessage(BaseMessage):
    @staticmethod
    def create(content, sender_name, receiver_name):
        return GroupTextMessage(content, sender_name, receiver_name)

    def __init__(self, content, sender_name, receiver_name):
        super().__init__(content)
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.messageType = MessageType.GroupTextMessage


class LoginMessage:
    @staticmethod
    def create(username, password):
        return LoginMessage(username, password)

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.messageType = MessageType.LoginMessage


class MessageResponse:
    @staticmethod
    def create(code):
        return MessageResponse(code)

    def __init__(self, code):
        self.responseCode = code
        self.messageType = MessageType.LoginResponse


class SignUpMessage:
    @staticmethod
    def create(username, password):
        return SignUpMessage(username, password)

    def __int__(self, username, password):
        self.username = username
        self.password = password
        self.messageType = MessageType.SignUpMessage


class CreateGroupMessage:
    @staticmethod
    def create(username, group_name):
        return CreateGroupMessage(username, group_name)

    def __init__(self, username, group_name):
        self.username = username
        self.group_name = group_name


class MessageType:
    PrivateTextMessage = 0
    GroupTextMessage = 1
    LoginMessage = 2
    LoginResponse = 3
    SignUpMessage = 4
    CreateGroupMessage = 5
