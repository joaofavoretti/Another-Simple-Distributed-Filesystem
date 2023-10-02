import zmq

context = zmq.Context()
socket = context.socket(zmq.PAIR)
socket.connect("tcp://localhost:5559")

# Send message to pair 1
message = b"Hello"
socket.send(message)

# Wait for reply from pair 1
message = socket.recv()
print("Received reply: %s" % message)