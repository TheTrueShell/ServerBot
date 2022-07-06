class server:
    def __init__(self, name, address, emojiStr, location):
        self.name = name
        self.address = address
        self.emojiStr = emojiStr
        self.location = location


# Server list
example_server = server(
    "Example Server",
    "mc.example.com",
    "😀",
    "Example Server"
)


serverList = [example_server]

def getServerList():
    return serverList