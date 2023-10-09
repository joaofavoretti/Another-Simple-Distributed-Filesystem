import zmq
import json
import netifaces
import pickle
import re
from utils import *

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

        self.opHandler = OperationHandler(self.context)
        
        self.seeders = []

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler),
            Operation(operation='SEEDER_REGISTER', args=["address", "files"], handler=self.seederRegisterHandler),
            Operation(operation='LIST', args=[], handler=self.listHandler)
        ]
    
    def run(self)->None:

        while True:
            operation = self.opHandler.getNextOperation(self.OPERATIONS)
            operation.object.callHandler(operation.args)

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
        
        self.seeders.append(seeder)
        res = Response(status=200, message=f'Registered seeder {seeder.address}:{seeder}')
        self.opHandler.send(res.export())

    def listHandler(self, args):
        files = {}
        for seeder in self.seeders:
            for fileHash, file in seeder.files.items():
                if fileHash not in files:
                    files[fileHash] = file
        
        res = Response(status=200, message=files)
        self.opHandler.send(res.export())

def main():
    tracker = Tracker()

    tracker.run()

if __name__ == '__main__':
    main()
