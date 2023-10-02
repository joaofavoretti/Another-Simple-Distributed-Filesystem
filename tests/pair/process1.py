import zmq

context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.bind("tcp://*:5559")

while True:
    # Wait for next message from pair 2
    message = socket.recv()
    print("Received message: %s" % message)

    # Send reply back to pair 2
    socket.send(b"World")