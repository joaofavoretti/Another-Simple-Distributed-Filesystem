import zmq
import time

class Tracker:
    def __init__(self):
        self.context = zmq.Context()

        self.sock = self.context.socket(zmq.REQ)
        self.sock.bind(f"tcp://11.56.1.21:5555")
        # sock.setsockopt(zmq.RCVTIMEO, 5000)
    
    def listen(self):
        while True:
            message = self.sock.recv()
            print("Received request: %s" % message)
            self.sock.send(b"World")
            time.sleep(1)


def main():
    tracker = Tracker()

    tracker.listen()
        
    

if __name__ == '__main__':
    main()
