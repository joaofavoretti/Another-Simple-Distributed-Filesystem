import zmq

context = zmq.Context()
socket = context.socket(zmq.REQ)
socket.connect("tcp://localhost:5555")

# Send request to server
socket.send(b"Hello")

# Wait for reply from server
message = socket.recv()
print("Received reply: %s" % message)