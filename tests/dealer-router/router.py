import zmq

context = zmq.Context()
socket = context.socket(zmq.ROUTER)
socket.bind("tcp://*:5558")

while True:
    # Wait for next message from dealer
    message = socket.recv_multipart()
    print("Received message: %s" % message)

    # Send reply back to dealer
    socket.send_multipart([message[0], b"World"])