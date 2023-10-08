import zmq
import pickle
import netifaces
import json
from utils import OperationHandler, Operation, Response, TrackerHandler

class Seeder:
    def __init__(self):
        self.context = zmq.Context()

        self.opHandler = OperationHandler(self.context)

        self.trackerHandler = TrackerHandler(self.context)

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler)
        ]

        self.registerToTracker()

    def registerToTracker(self):
        pass

    def run(self):
        while True:
            continue

    def pingHandler(self, args):
        res = Response(status=200, message=f'Received message: {args.get("message")}')
        self.opHandler.send(res.export())

def main():
    seeder = Seeder()

    seeder.run()

if __name__ == '__main__':
    main()
