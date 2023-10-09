import zmq
import re
import pickle
import math
import os
import json
import signal
from utils import OperationRequest, Response, TrackerHandler, SeederHandler, hash, File

TRACKER_OPERATIONS = {
    'PING': 'PING',
    'LIST': 'LIST',
    'GET': 'GET'
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
            try:
                command = input(self.PROMPT_STYLE)
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
            Command(label=["get <filehash>"], regexes=[r"^get\s+([a-f0-9]{5})$"], description="Download a file", handler=self.getHandler),
            Command(label=["upload <filePath>"], regexes=[r"^upload\s+([a-zA-Z0-9_\-\.]+)$"], description="Upload a file", handler=self.uploadHandler)
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
                print(f"{file.size}\t{file.lastModified}\t{fileHash} {file.name}")
        else:
            for fileHash, file in res.message.items():
                print(f"({fileHash}) {file.name} \t")

    def getHandler(self, commandString, commandRegex):
        match = re.search(commandRegex, commandString)
        fileHash = match.group(1)

        req = OperationRequest(operation=TRACKER_OPERATIONS['GET'], args={"fileHash": fileHash})
        self.trackerHandler.send(req.export())

        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

        if res.status != 200:
            print(res.message)

        # fileInformation = {'fileHash', 'fileName', 'size', 'seeders'}
        fileInformation = res.message

        # Download the file distributedly between all the seeders that contain it
        chunkSize = 4096

        chunkCountTotal = fileInformation['size'] / chunkSize

        chunkCountPerSeeder = int(chunkCountTotal // len(fileInformation['seeders']))

        seederRequestInformation = [{
            "seeder": seeder,
            "offset": None,
            "count": chunkCountPerSeeder * chunkSize
        } for seeder in fileInformation['seeders']]


        for i in range(math.ceil(chunkCountTotal % len(fileInformation['seeders']))):
            seederRequestInformation[len(fileInformation['seeders']) - i - 1]['count'] += chunkSize

        # Update the offset
        offset = 0
        for seeder in seederRequestInformation:
            seeder['offset'] = offset
            offset += seeder['count']

        outputFilename = f'{fileHash}-{fileInformation["fileName"]}'

        if os.path.exists(outputFilename):
            os.remove(outputFilename)

        # Send the requests to the seeders
        for seeder in seederRequestInformation:
            seederHandler = SeederHandler(self.context, seeder['seeder'])
            req = OperationRequest(operation=TRACKER_OPERATIONS['GET'], args={"fileHash": fileHash, "offset": seeder['offset'], "count": seeder['count']})
            seederHandler.send(req.export())

            res = seederHandler.recv()
            res = Response(**pickle.loads(res))

            if res.status != 200:
                print(res.message)
                return

            data = res.message["data"]
            count = res.message["count"]
            
            with open(outputFilename, 'ab') as f:
                f.write(data)
                f.close()

        print(f"Downloaded file {outputFilename}")

    def uploadHandle(self, commandString, commandRegex):
        match = re.search(commandRegex, commandString)
        filePath = match.group(1)
        fileHash = hash(filePath)

        if not os.path.exists(filePath):
            print(f"File {filePath} does not exist")
            return

        # Send the file to the tracker
        with open(filePath, 'rb') as f:
            fileData = f.read()
            fileSize = len(fileData)
            lastModified = os.path.getmtime(filename)

            req = OperationRequest(operation=TRACKER_OPERATIONS['UPLOAD'], args={"fileHash": fileHash, "fileName": filename, "size": fileSize, "lastModified": lastModified})
            self.trackerHandler.send(req.export())

            res = self.trackerHandler.recv()
            res = Response(**pickle.loads(res))

            if res.status != 200:
                print(res.message)
                return

            print(f"File {filename} uploaded successfully")

def disable_interruption(signal, frame):
    print()
    raise EmptyException('Empty command string')

def main():
    signal.signal(signal.SIGINT, disable_interruption)

    client = Client()
    
    client.run()

if __name__ == '__main__':
    main()
