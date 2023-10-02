import zmq

context = zmq.Context()
socket = context.socket(zmq.PUSH)
socket.bind("tcp://*:5557")

while True:
    # Send message to puller
    message = b"Hello"
    socket.send(message)