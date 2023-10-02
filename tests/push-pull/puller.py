import zmq

context = zmq.Context()
socket = context.socket(zmq.PULL)
socket.connect("tcp://localhost:5557")

while True:
    # Wait for next message from pusher
    message = socket.recv()
    print("Received message: %s" % message)