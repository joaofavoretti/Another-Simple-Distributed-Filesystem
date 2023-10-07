import zmq
import json
import pickle

class ClientCommandRequest:
    def __init__(self, operation):
        self.operation = operation

class ClientCommandParser:
    def __init__(self, context):

        self.context = context

        self.sock = self.context.socket(zmq.REQ)
        self.sock.bind(f"tcp://11.56.1.21:5555")

        # It is necessary to use the timebeat functionality and to allow a SeederCommandParser
        # Thinking of using the Publisher and Subscriber pattern for the Seeder and Tracker communication
        # sock.setsockopt(zmq.RCVTIMEO, 5000)

    def parseCommand(self, commandMessage):
        commandDict = pickle.loads(commandMessage)
        commandObject = ClientCommandRequest(operation=commandDict['operation'])
        pass

    def getNextCommand(self):
        while True:
            commandMessage = self.sock.recv()
            commandObject = self.parseCommand(commandMessage)

class Tracker:
    def __init__(self):
        self.clientParser = ClientCommandParser()
        
        
    
    def run(self):

        while True:
            command = self.clientParser.getNextCommand()


def main():
    tracker = Tracker()

    tracker.run()
        
    

if __name__ == '__main__':
    main()
