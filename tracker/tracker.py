import zmq
import pickle
import re
import heapq
from math import *
from datetime import datetime
from utils import OperationHandler, Operation, Response, OperationRequest, SeederHandler, SEEDER_OPERATIONS, File

class Seeder:
    def __init__(self, address, files):
        self.address = self.parseAddress(address)
        self.files = self.parseFiles(files)
    
    def parseAddress(self, address)->str:
        if not address:
            raise Exception('Empty address')
        
        if not re.search(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', address):
            raise Exception('Invalid address')

        return address

    def parseFiles(self, files)->dict:
        if not type(files) == dict:
            raise Exception('Invalid files type')
        
        return files

class Tracker:
    def __init__(self):

        self.context = zmq.Context()

        self.opHandler = OperationHandler(self.context, timeoutProcedure=self.timeoutProcedure)
        
        # That could be a set, ugh?
        self.seeders = []

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler),
            Operation(operation='LIST', args=[], handler=self.listHandler),
            Operation(operation='GET', args=["fileHash"], handler=self.getHandler),
            Operation(operation='UPLOAD', args=["fileHash", "fileSize"], handler=self.uploadHandler),
            Operation(operation='SEEDER_REGISTER', args=["address", "files"], handler=self.seederRegisterHandler),
            Operation(operation='SEEDER_UPDATE', args=["address", "files"], handler=self.seederUpdateHandler),
            Operation(operation='SEEDER_SIGNOUT', args=["address"], handler=self.seederSignoutHandlers)
        ]

    def timeoutProcedure(self):
        print('Routine Check', flush=True)
        self.seedersConnectivityCheck()
        self.seedersFileBalancing()

    def run(self)->None:
        while True:
            operation = self.opHandler.getNextOperation(self.OPERATIONS)
            operation.object.callHandler(operation.args)

    def seedersConnectivityCheck(self):
        for seeder in self.seeders:
            seederHandler = SeederHandler(self.context, seeder.address)
            seederHandler.setsockopt(zmq.RCVTIMEO, 3000)

            req = OperationRequest(operation='PING', args={"message": "Just a ping message"})
            seederHandler.send(req.export())

            try:
                res = seederHandler.recv()
                res = Response(**pickle.loads(res))
            except zmq.error.Again:
                self.seeders.remove(seeder)
                print(f'Seeder {seeder.address} is offline', flush=True)
                continue

    def seedersFileBalancing(self):
        filesStats = {}
        for seeder in self.seeders:
            for fileHash in seeder.files:
                if fileHash not in filesStats:
                    filesStats[fileHash] = {
                        "seeders": set(),
                        "fileName": seeder.files[fileHash].name,
                        "size": seeder.files[fileHash].size
                    }
                filesStats[fileHash]["seeders"].add(seeder)

        # For each file if less than ceil(log(n)) seeders have it, distribute the file to a seeders that don't have it
        for fileHash, fileInformation in filesStats.items():
            requiredSeedersAmount = ceil(log(len(self.seeders)))
            currentSeedersAmount = len(fileInformation["seeders"])
            
            if currentSeedersAmount >= requiredSeedersAmount:
                continue

            # Find the Seeders that contains less stored data based on the file.size and that doesn't have the file
            distributionSeeders = heapq.nsmallest(requiredSeedersAmount - currentSeedersAmount, self.seeders, key=lambda seeder: sum([file.size for file in seeder.files.values()]) if fileHash not in seeder.files else float('inf'))

            for seeder in distributionSeeders:
                seederHandler = SeederHandler(self.context, seeder.address)
                req = OperationRequest(operation=SEEDER_OPERATIONS['REQUEST_GET'], args={"fileHash": fileHash, "fileName": fileInformation["fileName"], "size": fileInformation["size"], "seeders": [seeder.address for seeder in fileInformation["seeders"]]})
                seederHandler.send(req.export())

                res = seederHandler.recv()
                res = Response(**pickle.loads(res))

                if res.status != 200:
                    print(res.message)
                    continue

                seeder.files[fileHash] = File(name=fileInformation["fileName"], size=fileInformation["size"], lastModified=datetime.now().timestamp())

    def pingHandler(self, args):
        res = Response(status=200, message=f'Received message: {args.get("message")}')
        self.opHandler.send(res.export())

    # Receive a message from a seeder to register it to the tracker
    def seederRegisterHandler(self, args):
        try:
            seeder = Seeder(**args)
        except Exception as e:
            res = Response(status=400, message=f'Invalid arguments')
            self.opHandler.send(res.export())
            return
        
        # Check if the seeder is already registered
        for registeredSeeder in self.seeders:
            if registeredSeeder.address == seeder.address:
                res = Response(status=400, message=f'Seeder already registered')
                self.opHandler.send(res.export())
                return

        self.seeders.append(seeder)
        res = Response(status=200, message=f'Registered seeder {seeder.address}:{seeder}')
        self.opHandler.send(res.export())

    def seederUpdateHandler(self, args):
        try:
            seeder = Seeder(**args)
        except Exception as e:
            res = Response(status=400, message=f'Invalid arguments')
            self.opHandler.send(res.export())
            return
        
        # Check if the seeder is already registered
        for registeredSeeder in self.seeders:
            if registeredSeeder.address == seeder.address:
                registeredSeeder.files = seeder.files
                res = Response(status=200, message=f'Updated seeder {seeder.address}:{seeder}')
                self.opHandler.send(res.export())
                return

        res = Response(status=400, message=f'Seeder not registered')
        self.opHandler.send(res.export())

    def seederSignoutHandlers(self, args):
        address = args.get('address')

        try:
            seeder = Seeder(address=address, files={})
        except Exception as e:
            res = Response(status=400, message=f'Invalid arguments')
            self.opHandler.send(res.export())
            return
        
        for seeder in self.seeders:
            if seeder.address == address:
                self.seeders.remove(seeder)
                res = Response(status=200, message=f'Seeder {address} signed out')
                self.opHandler.send(res.export())
                return
        
        res = Response(status=400, message=f'Seeder {address} not registered')
        self.opHandler.send(res.export())

    def listHandler(self, args):
        files = {}
        for seeder in self.seeders:
            for fileHash, file in seeder.files.items():
                if fileHash not in files:
                    files[fileHash] = file
        
        res = Response(status=200, message=files)
        self.opHandler.send(res.export())

    def getHandler(self, args):
        fileHash = args.get('fileHash')
        
        fileInformation = {
            'fileHash': fileHash,
            'fileName': None,
            'size': None,
            'seeders': []
        }

        for seeder in self.seeders:
            if fileHash in seeder.files:
                fileInformation['seeders'].append(seeder.address)
                
                if not fileInformation['fileName']:
                    fileInformation['fileName'] = seeder.files[fileHash].name

                if not fileInformation['size']:
                    fileInformation['size'] = seeder.files[fileHash].size
        
        if len(fileInformation['seeders']) == 0:
            res = Response(status=404, message=f'File not found')
            self.opHandler.send(res.export())
            return
        
        res = Response(status=200, message=fileInformation)
        self.opHandler.send(res.export())

    def uploadHandler(self, args):
        fileHash = args.get('fileHash')
        fileSize = args.get('fileSize')

        if type(fileHash) != str or type(fileSize) != int:
            res = Response(status=400, message=f'Invalid file hash or file size')
            self.opHandler.send(res.export())
            return
        
        for seeder in self.seeders:
            if fileHash in seeder.files:
                res = Response(status=400, message=f'File already exists')
                self.opHandler.send(res.export())
                return
            
        # Find the Seeder that contains less stored data based on the file.size
        seeder = min(self.seeders, key=lambda seeder: sum([file.size for file in seeder.files.values()]))

        # Answer back to the client with the seeder address
        res = Response(status=200, message={
            "address": seeder.address
        })

        self.opHandler.send(res.export())



def main():
    tracker = Tracker()

    tracker.run()

if __name__ == '__main__':
    main()
