import zmq

context = zmq.Context()
socket = context.socket(zmq.DEALER)
socket.connect("tcp://localhost:5558")

# Send message to router
message = b"Hello"
socket.send(message)

# Wait for reply from router
message = socket.recv()
print("Received reply: %s" % message)