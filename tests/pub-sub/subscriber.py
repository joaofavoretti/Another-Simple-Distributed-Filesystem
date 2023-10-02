import zmq

context = zmq.Context()
socket = context.socket(zmq.SUB)
socket.connect("tcp://localhost:5556")
socket.subscribe(b"")

while True:
    # Wait for next message from publisher
    message = socket.recv()
    print("Received message: %s" % message)