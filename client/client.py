import zmq
import re
import pickle
import json

class TrackerHandler:
    def __init__(self):
        self.context = zmq.Context()

        self.sock = self.context.socket(zmq.REQ)
        self.sock.bind(f"tcp://11.56.1.21:5555")

class CommandParser:
    PROMPT_STYLE = '\033[1;32m$ \033[0m'

    def __init__(self):
        pass

    def parseCommand(self, commandString, clientCommands):
        for commandObject in clientCommands:
            for regex in commandObject.regexes:
                match = re.search(regex, commandString)
                if match:
                    return {
                        "object": commandObject,
                        "string": commandString
                    }

        raise Exception(commandString.split()[0])

    def getNextCommand(self, clientCommands):
        while True:
            command = input(self.PROMPT_STYLE)
            
            if not command:
                continue
            
            try:
                commandObject = self.parseCommand(command, clientCommands)
                return commandObject
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
                return self.handler(commandString, self.regexes)

class Client:

    def __init__(self):
        self.tracker = TrackerHandler()

        self.COMMANDS = [
            Command(label=["help", "h"], regexes=[r"^help$", r"^h$"], description="Show this help message", handler=self.helpHandler),
            Command(label=["exit", "e"], regexes=[r"^exit$", r"^e$"], description="Exit the client", handler=self.exitHandler),
        ]

    def run(self):
        parser = CommandParser()

        while True:
            command = parser.getNextCommand(self.COMMANDS)
            command['object'].callHandler(command['string'])

    def helpHandler(self, commandString, commandRegex):
        print("Help message")
        print("Commands:")
        for commandObject in self.COMMANDS:
            print(f"{commandObject.label}:\t\t{commandObject.description}")

    def exitHandler(self, commandString, commandRegex):
        print("Exiting...")
        exit()


def main():
    client = Client()
    
    client.run()

if __name__ == '__main__':
    main()
