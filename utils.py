import zmq
import pickle
import netifaces
import json
import hashlib
import datetime
import os
import math

TRACKER_OPERATIONS = {
    'PING': 'PING',
    'LIST': 'LIST',
    'GET': 'GET',
    'UPLOAD': 'UPLOAD',
    'SEEDER_REGISTER': 'SEEDER_REGISTER',
    'SEEDER_UPDATE': 'SEEDER_UPDATE',
    'SEEDER_SIGNOUT': 'SEEDER_SIGNOUT',
}

SEEDER_OPERATIONS = {
    'PING': 'PING',
    'GET': 'GET',
    'UPLOAD': 'UPLOAD',
    'REQUEST_UPLOAD': 'REQUEST_UPLOAD',
}

class File:
    def __init__(self, name, size, lastModified):
        self.name = name
        self.size = size
        self.lastModified = datetime.datetime.fromtimestamp(lastModified).strftime('%H:%M')

class Response:

    def __init__(self, status, message):
        self.status = status
        self.message = message

    def export(self)->bytes:
        return pickle.dumps({
            "status": self.status,
            "message": self.message
        })

class OperationRequest:
    def __init__(self, operation, args):
        self.operation = self.parseOperation(operation)
        self.args = self.parseArgs(args)

    def parseOperation(self, operation)->str:
        if not operation:
            raise Exception('Empty operation message')

        return operation
    
    def parseArgs(self, args)->dict:
        if not args:
            return {}
        
        return args
    
    def export(self)->bytes:
        return pickle.dumps({
            "operation": self.operation,
            "args": self.args
        })

class OperationRequestHandler:
    def __init__(self, object, args):
        self.object = object
        self.args = args

class OperationHandler:
    def __init__(self, context, timeoutProcedure=None):

        self.context = context
        self.timeoutProcedure = timeoutProcedure

        self.sock = self.context.socket(zmq.REP)
        self.sock.bind(f"tcp://{getIpAddress()}:5555")
        self.sock.setsockopt(zmq.RCVTIMEO, 5000)

    def send(self, payload):
        return self.sock.send(payload)
    
    def recv(self):
        return self.sock.recv()

    def parseOperation(self, operationMessage, availableOperations)->OperationRequestHandler:
        operationDict = pickle.loads(operationMessage)
        
        # That command is so cool. Used to validate a Operation Message
        operationRequest = OperationRequest(**operationDict)

        for availableOperation in availableOperations:
            if availableOperation.operation == operationRequest.operation:
                
                # That will allow creating operations with the same name but with different args
                for arg in availableOperation.args:
                    if not arg in operationRequest.args:
                        continue

                return OperationRequestHandler(object=availableOperation, args=operationRequest.args)

        raise Exception('Operation not found or invalid arguments')
    
    def getNextOperation(self, trackerOperations)->OperationRequestHandler:
        while True:
            
            try:
                operationMessage = self.recv()
                operationReqHandler = self.parseOperation(operationMessage, trackerOperations)
            except zmq.error.Again:
                if self.timeoutProcedure:
                    self.timeoutProcedure()
                continue
            except Exception as e:
                res = Response(status=500, message=e.args[0])
                self.send(res.export())

            return operationReqHandler
        
class Operation:

    def __init__(self, operation, args, handler):
        self.operation = operation
        self.args = args
        self.handler = handler

    def callHandler(self, args):
        return self.handler(args) 
    
class TrackerHandler:
    def __init__(self, context):
        self.context = context

        self.sock = self.context.socket(zmq.REQ)
        self.sock.connect(f"tcp://11.56.1.21:5555")

    def setsockopt(self, opt, value):
        return self.sock.setsockopt(opt, value)

    def send(self, payload):
        return self.sock.send(payload)
    
    def recv(self):
        return self.sock.recv()
    
class SeederHandler:
    def __init__(self, context, address):
        self.context = context

        self.sock = self.context.socket(zmq.REQ)
        self.sock.connect(f"tcp://{address}:5555")

    def setsockopt(self, opt, value):
        return self.sock.setsockopt(opt, value)

    def send(self, payload):
        return self.sock.send(payload)
    
    def recv(self):
        return self.sock.recv()

def getIpAddress():
    """
    Simple function to retrieve the "main" interface of a machine.
    This is used to index the Storage Nodes in the Metadata Server
    """
    interfaces = netifaces.interfaces()
    for interface in interfaces:
        if interface == "lo":
            continue
        addrs = netifaces.ifaddresses(interface)
        if netifaces.AF_INET in addrs:
            return addrs[netifaces.AF_INET][0]["addr"]

# Calculate that hash from a file path "fpath"
def hash(fpath):
    hasher = hashlib.md5()

    with open(fpath, 'rb') as f:
        hasher.update(f.read())

    file_hash = hasher.hexdigest()
    return file_hash

def getOutputFilename(proposedFilename):
    if not os.path.exists(proposedFilename):
        return proposedFilename

    filename, extension = os.path.splitext(proposedFilename)

    i = 1
    while True:
        filename = f"{filename}({i})"
        if not os.path.exists(filename + extension):
            return filename + extension
        i += 1

# fileInformation = {'fileHash', 'fileName', 'size', 'seeders'}
def getFileDistributedly(context, fileInformation):
    
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

    proposedFilename = fileInformation['fileName']
    outputFilename = getOutputFilename(proposedFilename)

    # Send the requests to the seeders
    for seeder in seederRequestInformation:
        seederHandler = SeederHandler(context, seeder['seeder'])
        req = OperationRequest(operation=SEEDER_OPERATIONS['GET'], args={"fileHash": fileInformation['fileHash'], "offset": seeder['offset'], "count": seeder['count']})
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

    return outputFilename
