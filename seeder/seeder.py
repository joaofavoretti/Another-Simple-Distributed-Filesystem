import zmq
import pickle
import os
import datetime
from utils import OperationHandler, Operation, Response, TrackerHandler, getIpAddress, OperationRequest, File, hash, TRACKER_OPERATIONS, SEEDER_OPERATIONS, getFileDistributedly

HASH_SIZE = 5

class Seeder:
    def __init__(self):
        self.context = zmq.Context()

        self.opHandler = OperationHandler(self.context)

        self.trackerHandler = TrackerHandler(self.context)

        self.OPERATIONS = [
            Operation(operation='PING', args=["message"], handler=self.pingHandler),
            Operation(operation='GET', args=["fileHash", "offset", "count"], handler=self.getHandler),
            Operation(operation='UPLOAD', args=["fileHash", "file", "fileData"], handler=self.uploadHandler),
            Operation(operation='REQUEST_UPLOAD', args=["fileHash", "fileName", "size", "seeders"], handler=self.requestUploadHandler),
        ]

        self.diskDirectory = '/disk'

        self.localFiles = {}

        self.registerToTracker()

    def __del__(self):
        req = OperationRequest(operation=TRACKER_OPERATIONS['SEEDER_SIGNOUT'], args={"address": getIpAddress()})
        self.trackerHandler.send(req.export())

        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

    def registerToTracker(self):        
        
        self.localFiles = {
            hash(os.path.join(self.diskDirectory, filename))[:HASH_SIZE]: File(name=filename, 
                                                                   size=os.path.getsize(os.path.join(self.diskDirectory, filename)), 
                                                                   lastModified=os.path.getmtime(os.path.join(self.diskDirectory, filename)))
            for filename in os.listdir(self.diskDirectory)}
        
        req = OperationRequest(operation=TRACKER_OPERATIONS['SEEDER_REGISTER'], args={"address": getIpAddress(), "files": self.localFiles})
        self.trackerHandler.send(req.export())
        
        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

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

    def uploadHandler(self, args):
        fileHash = args.get('fileHash')
        file = args.get('file')
        fileData = args.get('fileData')

        if fileHash in self.localFiles:
            res = Response(status=200, message=f'File already exists')
            self.opHandler.send(res.export())
            return

        if type(fileData) != bytes:
            res = Response(status=400, message=f'Invalid file data type')
            self.opHandler.send(res.export())
            return
        
        if type(file) != File:
            res = Response(status=400, message=f'Invalid file type')
            self.opHandler.send(res.export())
            return

        if len(fileData) != file.size:
            res = Response(status=400, message=f'Invalid file size')
            self.opHandler.send(res.export())
            return

        # Save the data to disk
        with open(os.path.join(self.diskDirectory, file.name), 'wb') as f:
            f.write(fileData)
            f.close()

        file.lastModified = datetime.datetime.now().strftime('%H:%M')

        self.localFiles[fileHash] = file

        # Update seeder on the Tracker
        req = OperationRequest(operation=TRACKER_OPERATIONS['SEEDER_UPDATE'], args={"address": getIpAddress(), "files": self.localFiles})
        self.trackerHandler.send(req.export())

        res = self.trackerHandler.recv()
        res = Response(**pickle.loads(res))

        # There is no much to doo actually. Could raise an error though
        if res.status != 200:
            os.remove(os.path.join(self.diskDirectory, file.name))
            
            del self.localFiles[fileHash]

            res = Response(status=400, message=f'File not uploaded')
            self.opHandler.send(res.export())
            return
        
        res = Response(status=200, message=f'File uploaded')
        self.opHandler.send(res.export())

    def requestUploadHandler(self, args):
        fileHash = args.get('fileHash')
        fileName = args.get('fileName')
        size = args.get('size')
        seeders = args.get('seeders')

        if type(fileHash) != str or len(fileHash) != 5 or type(fileName) != str or type(size) != int or type(seeders) != list:
            res = Response(status=400, message=f'Invalid file hash, file name, size or seeders')
            self.opHandler.send(res.export())
            return
        
        if fileHash in self.localFiles:
            res = Response(status=200, message=f'File already exists')
            self.opHandler.send(res.export())
            return
        
        fileInformation = {
            'fileHash': fileHash,
            'fileName': fileName,
            'size': size,
            'seeders': seeders
        }
        
        getFileDistributedly(self.context, fileInformation)

        res = Response(status=200, message=f'File downloaded')
        self.opHandler.send(res.export())



def main():
    seeder = Seeder()

    seeder.run()

if __name__ == '__main__':
    main()
