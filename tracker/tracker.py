import zmq
import json
import netifaces
import pickle
from utils import *

class Tracker:
    def __init__(self):

        self.context = zmq.Context()

        self.opHandler = OperationHandler(self.context)
        
        self.seeders = []

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler),
            Operation(operation='SEEDER_REGISTER', args=["index"], handler=self.seederRegisterHandler)
        ]
    
    def run(self)->None:

        while True:
            operation = self.opHandler.getNextOperation(self.OPERATIONS)
            operation.object.callHandler(operation.args)

    def pingHandler(self, args):
        res = Response(status=200, message=f'Received message: {args.get("message")}')
        self.opHandler.send(res.export())

    def seederRegisterHandler(self, args):
        pass

def main():
    tracker = Tracker()

    tracker.run()

if __name__ == '__main__':
    main()
