import zmq
import re
import pickle
import os
import signal
import heapq
from utils import OperationRequest, Response, TrackerHandler, SeederHandler, hash, File, TRACKER_OPERATIONS, SEEDER_OPERATIONS, getFileDistributedly

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
            try:
                command = input(self.PROMPT_STYLE)
                commandObject = self.parseCommand(command, clientCommands)
                return commandObject
            except EmptyException as e:
                continue
            except Exception as e:
                commandLabel = e.args[0]
                print(f'Incorrect parsing: {commandLabel}')

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
            Command(label=["get <fileHash>"], regexes=[r"^get\s+([a-f0-9]{5})$"], description="Download a file", handler=self.getHandler),
            Command(label=["upload <filePath>"], regexes=[r"^upload\s+(\.?(/?[a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)$"], description="Upload a file", handler=self.uploadHandler),
            Command(label=["clear"], regexes=[r"^clear$"], description="Clear the screen", handler=self.clearHandler),
            Command(label=["list-local [-l]", "ll [-l]"], regexes=[r"^list-local(\s+-l)?$", r"^ll(\s+-l)?$"], description="List files in the local filesystem", handler=self.listLocalHandler),
        ]

    def run(self):
        comHandler = CommandHandler()

        while True:
            command = comHandler.getNextCommand(self.COMMANDS)
            command.object.callHandler(command.string)

    def helpHandler(self, commandString, commandRegex):
        print("Help message")
        print("Commands:")

        max_label_length = max([len(", ".join(commandObject.label)) for commandObject in self.COMMANDS])

        for commandObject in self.COMMANDS:
            print(f"\t{', '.join(commandObject.label).ljust(max_label_length)}\t{commandObject.description}")

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

    def clearHandler(self, commandString, commandRegex):
        os.system('clear')

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
                print(f"{file.size}\t{file.lastModified}\t{fileHash} {file.name}")
        else:
            for fileHash, file in res.message.items():
                print(f"({fileHash}) {file.name} \t")

    def listLocalHandler(self, commandString, commandRegex):
        # Using the re match to check if the -l flag is present
        match = re.search(commandRegex, commandString)

        longListing = True if match and match.group(1) else False

        files = []
        for filename in os.listdir('.'):
            if os.path.isfile(filename):
                heapq.heappush(files, (filename, File(name=filename, size=os.path.getsize(filename), lastModified=os.path.getmtime(filename))))

        if longListing:
            for _, file in files:
                print(f"{file.size}\t{file.lastModified}\t{hash(file.name)[:5]} {file.name}")
        else:
            for _, file in files:
                print(f"({hash(file.name)[:5]}) {file.name} \t")

    def getHandler(self, commandString, commandRegex):
        match = re.search(commandRegex, commandString)
        fileHash = match.group(1)

        req = OperationRequest(operation=TRACKER_OPERATIONS['GET'], args={"fileHash": fileHash})
        self.trackerHandler.send(req.export())

        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

        if res.status != 200:
            print(res.message)
            return

        fileInformation = res.message

        outputFilename = getFileDistributedly(self.context, fileInformation)

        print(f"Downloaded file {outputFilename}")

    def uploadHandler(self, commandString, commandRegex):
        match = re.search(commandRegex, commandString)
        filePath = match.group(1)

        if not os.path.exists(filePath):
            print(f"File {filePath} does not exist")
            return
        
        fileHash = hash(filePath)[:5]
        fileSize = os.path.getsize(filePath)
        fileLastModified = os.path.getmtime(filePath)

        file = File(name=os.path.basename(filePath), size=fileSize, lastModified=fileLastModified)

        req = OperationRequest(operation=TRACKER_OPERATIONS['UPLOAD'], args={"fileHash": fileHash, "fileSize": fileSize})
        self.trackerHandler.send(req.export())

        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

        if res.status != 200:
            print(res.message)
            return

        seederAddress = res.message['address']

        with open(filePath, 'rb') as f:
            fileData = f.read()
            f.close()

        seederHandler = SeederHandler(self.context, seederAddress)
        req = OperationRequest(operation=SEEDER_OPERATIONS['UPLOAD'], args={"fileHash": fileHash, "file":file, "fileData": fileData})
        seederHandler.send(req.export())

        res = seederHandler.recv()
        res = Response(**pickle.loads(res))

        if res.status != 200:
            print(res.message)
            return
        
        print(f"Uploaded file {filePath}")

def ctrl_c_handler(signal, frame):
    print()
    raise EmptyException('Empty command string')

def main():
    # Handle CTRL+C
    signal.signal(signal.SIGINT, ctrl_c_handler)

    client = Client()
    
    client.run()

if __name__ == '__main__':
    main()
