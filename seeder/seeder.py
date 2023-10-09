import zmq
import pickle
import os
import datetime
from utils import OperationHandler, Operation, Response, TrackerHandler, getIpAddress, OperationRequest, File, hash

TRACKER_OPERATIONS = {
    'SEEDER_REGISTER': 'SEEDER_REGISTER'
}

HASH_SIZE = 5

class Seeder:
    def __init__(self):
        self.context = zmq.Context()

        self.opHandler = OperationHandler(self.context)

        self.trackerHandler = TrackerHandler(self.context)

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler),
            Operation(operation='GET', args=["fileHash", "offset", "count"], handler=self.getHandler)
        ]

        self.diskDirectory = '/disk'

        self.localFiles = {}

        self.registerToTracker()

    def registerToTracker(self):        
        
        self.localFiles = {
            hash(os.path.join(self.diskDirectory, filename))[:HASH_SIZE]: File(name=filename, 
                                                                   size=os.path.getsize(os.path.join(self.diskDirectory, filename)), 
                                                                   lastModified=datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.diskDirectory, filename))).strftime('%H:%M'))
            for filename in os.listdir(self.diskDirectory)}
        
        req = OperationRequest(operation=TRACKER_OPERATIONS['SEEDER_REGISTER'], args={"address": getIpAddress(), "files": self.localFiles})
        self.trackerHandler.send(req.export())
        
        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))
        print(res.message)

        if res.status != 200:
            exit()

    def run(self):
        while True:
            operation = self.opHandler.getNextOperation(self.OPERATIONS)
            operation.object.callHandler(operation.args)

    def pingHandler(self, args):
        res = Response(status=200, message=f'Received message: {args.get("message")}')
        self.opHandler.send(res.export())

    def getHandler(self, args):
        fileHash = args.get('fileHash')
        offset = args.get('offset')
        count = args.get('count')

        if type(offset) != int or type(count) != int:
            res = Response(status=400, message=f'Invalid offset or count type')
            self.opHandler.send(res.export())
            return

        if fileHash not in self.localFiles:
            res = Response(status=404, message=f'File not found')
            self.opHandler.send(res.export())
            return
        
        file = self.localFiles[fileHash]

        if offset > file.size:
            res = Response(status=400, message=f'Invalid offset')
            self.opHandler.send(res.export())
            return
        
        if offset + count > file.size:
            count = file.size - offset

        with open(os.path.join(self.diskDirectory, file.name), 'rb') as f:
            f.seek(offset)
            data = f.read(count)
            res = Response(status=200, message={
                "count": count,
                "data": data
            })
            self.opHandler.send(res.export())

def main():
    seeder = Seeder()

    seeder.run()

if __name__ == '__main__':
    main()
