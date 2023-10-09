import zmq
import pickle
import netifaces
import json
import os
import hashlib
import datetime
from utils import OperationHandler, Operation, Response, TrackerHandler, getIpAddress, OperationRequest, File

TRACKER_OPERATIONS = {
    'SEEDER_REGISTER': 'SEEDER_REGISTER'
}

# Calculate that hash from a file path "fpath"
def hash(fpath):
    hasher = hashlib.sha256()

    with open(fpath, 'rb') as f:
        hasher.update(f.read())

    file_hash = hasher.hexdigest()
    return file_hash

class Seeder:
    def __init__(self):
        self.context = zmq.Context()

        self.opHandler = OperationHandler(self.context)

        self.trackerHandler = TrackerHandler(self.context)

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler)
        ]

        self.diskDirectory = '/disk'

        self.registerToTracker()

    def registerToTracker(self):        
        
        files = {
            hash(os.path.join(self.diskDirectory, filename)): File(name=filename, 
                                                                   size=os.path.getsize(os.path.join(self.diskDirectory, filename)), 
                                                                   lastModified=datetime.datetime.fromtimestamp(os.path.getmtime(os.path.join(self.diskDirectory, filename))).strftime('%H:%M'))
            for filename in os.listdir(self.diskDirectory)}
        
        req = OperationRequest(operation=TRACKER_OPERATIONS['SEEDER_REGISTER'], args={"address": getIpAddress(), "files": files})
        self.trackerHandler.send(req.export())
        
        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))
        print(res.message)

        if res.status != 200:
            exit()

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
