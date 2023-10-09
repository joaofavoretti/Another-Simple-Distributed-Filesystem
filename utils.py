import zmq
import pickle
import netifaces
import json

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

class File:
    def __init__(self, name, size, lastModified):
        self.name = name
        self.size = size
        self.lastModified = lastModified

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
    def __init__(self, context):

        self.context = context

        self.sock = self.context.socket(zmq.REP)
        self.sock.bind(f"tcp://{getIpAddress()}:5555")

        # sock.setsockopt(zmq.RCVTIMEO, 5000)

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

        raise Exception('Operation not found')
    
    def getNextOperation(self, trackerOperations)->OperationRequestHandler:
        while True:
            operationMessage = self.recv()
            
            try:
                operationReqHandler = self.parseOperation(operationMessage, trackerOperations)
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
        # self.sock.connect(f"tcp://12.56.1.21:5555")
        self.sock.connect(f"tcp://11.56.1.21:5555")

    def send(self, payload):
        return self.sock.send(payload)
    
    def recv(self):
        return self.sock.recv()