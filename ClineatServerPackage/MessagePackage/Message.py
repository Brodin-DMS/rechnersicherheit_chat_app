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

    def __init__(self, username, password):
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


class AttachmentMessage(BaseMessage):
    @staticmethod
    def create(filename, content, sender_name, receiver_name, receiver_msg_type):
        return AttachmentMessage(filename, content, sender_name, receiver_name, receiver_msg_type)

    def __init__(self, filename, content, sender_name, receiver_name, receiver_msg_type):
        super().__init__(content)
        self.sender_name = sender_name
        self.receiver_name = receiver_name
        self.messageType = MessageType.AttachmentMessage
        self.filename = filename
        self.receiver_msg_type = receiver_msg_type


class PrivateHistoryRequest:
    @staticmethod
    def create(username, receiver_name):
        return PrivateHistoryRequest(username, receiver_name)

    def __init__(self, username, receiver_name):
        self.username = username
        self.receiver_name = receiver_name


class PrivateHistoryMessage:
    @staticmethod
    def create(content):
        return PrivateHistoryMessage(content)

    def __init__(self, content):
        self.rows = content


class GroupHistoryRequest:
    @staticmethod
    def create(username, group_name):
        return GroupHistoryRequest(username, group_name)

    def __init__(self, username, group_name):
        self.username = username
        self.group_name = group_name


class GroupHistoryMessage:
    @staticmethod
    def create(content):
        return GroupHistoryMessage(content)

    def __init__(self, content):
        self.rows = content


class MessageType:
    PrivateTextMessage = 0
    GroupTextMessage = 1
    LoginMessage = 2
    LoginResponse = 3
    SignUpMessage = 4
    CreateGroupMessage = 5
    PrivateHistoryMessage = 6
    GroupHistoryMessage = 7
    PrivateHistoryRequest = 8
    GroupHistoryRequest = 9
    AttachmentMessage = 10

