import zmq
import pickle
import json
import multiprocessing

CONSTS_FILE_PATH = "./consts.json"

def check_storage_node(ipv4, storage_node):
    """
        Sends a heartbeat request to each Storage Node to check if it is still
    """
    global context, CONSTS

    HEARTBEAT_REQ = CONSTS['operation-codes']['HEARTBEAT_REQ']

    sn_port = CONSTS['storage-nodes']['port']

    # Criar um novo socker para conectar aos Storage Nodes
    sock = context.socket(zmq.REQ)
    sock.connect(f"tcp://{ipv4}:{sn_port}")
    sock.setsockopt(zmq.RCVTIMEO, 3000)

    location_to_retrieve_req = {
        "code": HEARTBEAT_REQ,
        "ipv4": "Metadata Server"
    }

    sock.send(pickle.dumps(location_to_retrieve_req))

    # Try to establish a connection with the Storage Node 
    try:
        location_to_retrieve_res = pickle.loads(sock.recv())
    except zmq.error.Again:
        print(f"Storage node {ipv4} is offline", flush=True)
        storage_node['status'] = 'OFF'
        storage_node['file-list'] = []
        return

    if location_to_retrieve_res['status'] == 'OK':
        print(f"Storage node {ipv4} is online", flush=True)
        storage_node['status'] = 'ON'
        # Since the communication is already established, it updates the file list
        storage_node['file-list'] = location_to_retrieve_res['file-list']
    else:
        print(f"Storage node {ipv4} is offline", flush=True)
        storage_node['status'] = 'OFF'
        storage_node['file-list'] = []

def main():
    global context, CONSTS
    
    CONSTS = json.load(open(CONSTS_FILE_PATH, "r"))
    
    MS_IPV4 = CONSTS['metadata-server']['ipv4']
    MS_PORT = CONSTS['metadata-server']['port']

    STORAGE_NODE_SIGN_IN_REQ = CONSTS['operation-codes']['STORAGE_NODE_SIGN_IN_REQ']
    STORAGE_NODE_SIGN_OUT_REQ = CONSTS['operation-codes']['STORAGE_NODE_SIGN_OUT_REQ']
    LOCATION_TO_STORE_REQ = CONSTS['operation-codes']['LOCATION_TO_STORE_REQ']
    LIST_FILES_REQ = CONSTS['operation-codes']['LIST_FILES_REQ']
    UPDATE_NODE_FILE_LIST_REQ = CONSTS['operation-codes']['UPDATE_NODE_FILE_LIST_REQ']
    LOCATION_TO_RETRIEVE_REQ = CONSTS['operation-codes']['LOCATION_TO_RETRIEVE_REQ']

    # Dictionary used to keep track of the index of the entire file system
    storage_nodes = {}

    context = zmq.Context()

    sock = context.socket(zmq.REP)
    sock.bind(f"tcp://{MS_IPV4}:{MS_PORT}")
    sock.setsockopt(zmq.RCVTIMEO, 5000)

    print('Server started...', flush=True)

    while True:
        
        # This exception handlihg sequence is used to check the Storage Node status when it does not have any requests to process 
        try:
            operation_req = pickle.loads(sock.recv())
        except zmq.error.Again:
            # Execute a heartbeat check on all storage nodes
            for ipv4, storage_node in storage_nodes.items():
                check_storage_node(ipv4, storage_node)
            continue

        # Simple loggin sinformation about the request
        source = operation_req['ipv4'] if 'ipv4' in operation_req else 'Client App'
        print(f"""
        == Metadata Server - Received Request ==
        Code: {operation_req['code']}
        IP Address: {source}
        """, flush=True)

        # Handling the request from Storage Nodes to be Signed In to the Metadata Server index
        if operation_req["code"] == STORAGE_NODE_SIGN_IN_REQ:
            sign_in_req = operation_req

            storage_nodes[sign_in_req["ipv4"]] = {
                "status": "ON",
                "file-list": sign_in_req["file-list"]
            }

            print(f"Received request from {sign_in_req['ipv4']} with file list {sign_in_req['file-list']}", flush=True)
            
            STORAGE_NODE_SIGN_IN_RES = CONSTS['operation-codes']['STORAGE_NODE_SIGN_IN_RES']

            sign_in_res = {
                "code": STORAGE_NODE_SIGN_IN_RES,
                "status": "OK"
            }
            sock.send(pickle.dumps(sign_in_res))
        
        # Handling the request from Storage Nodes to be Signed Out from the Metadata Server index
        elif operation_req["code"] == STORAGE_NODE_SIGN_OUT_REQ:
            sign_out_req = operation_req

            storage_nodes[sign_out_req["ipv4"]] = {
                "status": "OFF",
                "file-list": []
            }

            print(f"Received request from {sign_out_req['ipv4']} to sign out", flush=True)

            STORAGE_NODE_SIGN_OUT_RES = CONSTS['operation-codes']['STORAGE_NODE_SIGN_OUT_RES']

            sign_out_res = {
                "code": STORAGE_NODE_SIGN_OUT_RES,
                "status": "OK"
            }
            sock.send(pickle.dumps(sign_out_res))
        
        # Handling requests from the used to check where to store a new file.
        # It uses a very simple balancing technique to do not overload a single node
        elif operation_req["code"] == LOCATION_TO_STORE_REQ:
            
            fewer_files_num = 0
            fewer_files_ipv4 = None

            for ipv4, storage_node in storage_nodes.items():
                if storage_node["status"] == "ON":
                    if fewer_files_ipv4 == None:
                        fewer_files_ipv4 = ipv4
                        fewer_files_num = len(storage_node["file-list"])
                    elif len(storage_node["file-list"]) < fewer_files_num:
                        fewer_files_ipv4 = ipv4
                        fewer_files_num = len(storage_node["file-list"])

            LOCATION_TO_STORE_RES = CONSTS['operation-codes']['LOCATION_TO_STORE_RES']

            location_to_store_res = None

            if fewer_files_ipv4 == None:
                location_to_store_res = {
                    "code": LOCATION_TO_STORE_RES,
                    "status": "ERROR",
                }
            else:
                location_to_store_res = {
                    "code": LOCATION_TO_STORE_RES,
                    "status": "OK",
                    "ipv4": fewer_files_ipv4
                }
            
            sock.send(pickle.dumps(location_to_store_res))

        # Handling requests to update the information about the files stored in a node
        elif operation_req["code"] == UPDATE_NODE_FILE_LIST_REQ:
            update_node_file_list_req = operation_req

            storage_nodes[update_node_file_list_req["ipv4"]]["file-list"] = update_node_file_list_req["file-list"]

            print(f"Received request from {update_node_file_list_req['ipv4']} to update file list", flush=True)

            UPDATE_NODE_FILE_LIST_RES = CONSTS['operation-codes']['UPDATE_NODE_FILE_LIST_RES']

            update_node_file_list_res = {
                "code": UPDATE_NODE_FILE_LIST_RES,
                "status": "OK"
            }
            sock.send(pickle.dumps(update_node_file_list_res))

        # Handling requests to list all the files stored in all the nodes available
        elif operation_req["code"] == LIST_FILES_REQ:
            list_files_req = operation_req

            list_files_res = {
                "code": LIST_FILES_REQ,
                "status": "OK",
                "files": set()
            }

            for ipv4, storage_node in storage_nodes.items():
                if storage_node["status"] == "ON":
                    for file in storage_node["file-list"]:
                        list_files_res["files"].add(file)
            
            sock.send(pickle.dumps(list_files_res))

        # Handling requests to retrieve the location of a file
        elif operation_req["code"] == LOCATION_TO_RETRIEVE_REQ:
            location_to_retrieve_req = operation_req

            file_name = location_to_retrieve_req["file-name"]
            storage_node_ipv4 = None

            for ipv4, storage_node in storage_nodes.items():
                if storage_node["status"] == "ON" and file_name in storage_node["file-list"]:
                    storage_node_ipv4 = ipv4
                    break

            if storage_node_ipv4:
                location_to_retrieve_res = {
                    "code": LOCATION_TO_RETRIEVE_REQ,
                    "status": "OK",
                    "ipv4": storage_node_ipv4
                }
            else:
                location_to_retrieve_res = {
                    "code": LOCATION_TO_RETRIEVE_REQ,
                    "status": "FILE NOT FOUND",
                }

            sock.send(pickle.dumps(location_to_retrieve_res))

        else:
            operation_res ={
                "code": operation_req['code'],
                "status": "ERROR"
            }
            sock.send(pickle.dumps(operation_res))

        
if __name__ == "__main__":
    main()
