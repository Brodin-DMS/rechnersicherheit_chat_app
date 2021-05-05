from abc import ABCMeta

class BaseMessage(metaclass=ABCMeta):
    def __init__(self, content, senderId):
        self.content = content
        self.senderId = senderId
        self.messageType = None

#class PrivateTextMessage(BaseMessage):
class PrivateTextMessage():
    @staticmethod
    def Create(content, senderId, receiverId):
        return PrivateTextMessage(content, senderId, receiverId)

    def __init__(self, content, senderId, receiverId):
        #super().__init__(content, senderId)
        self.content = content
        self.senderId = senderId
        self.receiverId = receiverId
        self.messageType = MessageType.PrivateTextMessage

class GroupTextMessage(BaseMessage):
    @staticmethod
    def Create(content, senderId, groupId):
        return GroupTextMessage(content, senderId, groupId)

    def __init__(self, content, senderId, groudId):
        super().__init__(content, senderId)
        self.groupId = groudId
        self.messageType = MessageType.GroupTextMessage

class LoginMessage:
    @staticmethod
    def Create(username, password, sender_id):
        return LoginMessage(username, password,sender_id)

    def __init__(self, username, password, senderId):
        self.username = username
        self.password = password
        self.senderId = senderId
        self.messageType = MessageType.LoginMessage


class LoginResponse:
    @staticmethod
    def Create(code):
        return LoginResponse(code)


    def __init__(self, code):
        self.responseCode = code
        self.messageType = MessageType.LoginResponse


class MessageType:
    PrivateTextMessage = 0
    GroupTextMessage = 1
    LoginMessage = 2
    LoginResponse = 3
