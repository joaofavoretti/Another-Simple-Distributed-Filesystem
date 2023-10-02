import zmq
import time

context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:5556")

while True:
    # Send message to all subscribers
    message = b"Hello"
    socket.send(message)
    time.sleep(5)