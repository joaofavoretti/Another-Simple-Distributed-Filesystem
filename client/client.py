import zmq
import re
import pickle
import json
from utils import OperationRequest, Response, TrackerHandler

TRACKER_OPERATIONS = {
    'PING': 'PING',
    'LIST': 'LIST'
}

class EmptyException(Exception):
    pass



class CommandRequestHandler:
    def __init__(self, object, string):
        self.object = object
        self.string = string

class CommandHandler:
    PROMPT_STYLE = '\033[1;32m$ \033[0m'

    def __init__(self):
        pass

    def parseCommand(self, commandString, clientCommands):
        if not commandString:
            # Raise empty exception
            raise EmptyException('Empty command string')
        
        for commandObject in clientCommands:
            for regex in commandObject.regexes:
                match = re.search(regex, commandString)
                if match:
                    return CommandRequestHandler(object=commandObject, string=commandString)

        raise Exception(commandString.split()[0])

    def getNextCommand(self, clientCommands):
        while True:
            command = input(self.PROMPT_STYLE)
            
            try:
                commandObject = self.parseCommand(command, clientCommands)
                return commandObject
            except EmptyException as e:
                continue
            except Exception as e:
                commandLabel = e.args[0]
                print(f'Command not found: {commandLabel}')

class Command:
    def __init__(self, label, regexes, description, handler):
        self.label = label
        self.regexes = regexes
        self.description = description
        self.handler = handler

    def callHandler(self, commandString):
        for regex in self.regexes:
            match = re.search(regex, commandString)
            if match:
                return self.handler(commandString, regex)

class Client:

    def __init__(self):
        self.context = zmq.Context()

        self.trackerHandler = TrackerHandler(self.context)

        self.COMMANDS = [
            Command(label=["help", "h"], regexes=[r"^help$", r"^h$"], description="Show this help message", handler=self.helpHandler),
            Command(label=["exit", "e"], regexes=[r"^exit$", r"^e$"], description="Exit the client", handler=self.exitHandler),
            Command(label=["ping"], regexes=[r"^ping$"], description="Ping the Tracker", handler=self.pingHandler),
            Command(label=["list [-l]", "ls [-l]"], regexes=[r"^list(\s+-l)?$", r"^ls(\s+-l)?$"], description="List all files in the filesystem", handler=self.listHandler),
        ]

    def run(self):
        comHandler = CommandHandler()

        while True:
            command = comHandler.getNextCommand(self.COMMANDS)
            command.object.callHandler(command.string)

    def helpHandler(self, commandString, commandRegex):
        print("Help message")
        print("Commands:")
        for commandObject in self.COMMANDS:
            print(f"{commandObject.label}:\t\t{commandObject.description}")

    def exitHandler(self, commandString, commandRegex):
        print("Exiting...")
        exit()

    def pingHandler(self, commandString, commandRegex):
        req = OperationRequest(operation=TRACKER_OPERATIONS['PING'], args={"message": "Hello Tracker"})
        self.trackerHandler.send(req.export())
        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))
        if res.status == 200:
            print(res.message)

    def listHandler(self, commandString, commandRegex):
        # Using the re match to check if the -l flag is present
        match = re.search(commandRegex, commandString)

        longListing = True if match and match.group(1) else False
        
        req = OperationRequest(operation=TRACKER_OPERATIONS['LIST'], args={})
        self.trackerHandler.send(req.export())

        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

        if res.status != 200:
            print(res.message)

        # Message is a dictionary of {filehash: File}. Print it nicely
        if longListing:
            for fileHash, file in res.message.items():
                print(f"{file.size}\t{file.lastModified}\t{fileHash[:5]} {file.name}")
        else:
            for fileHash, file in res.message.items():
                print(f"({fileHash[:5]}) {file.name} \t")

def main():
    client = Client()
    
    client.run()

if __name__ == '__main__':
    main()
