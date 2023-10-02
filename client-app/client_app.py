import zmq
import json
import pickle
import re
import os

CONSTS_FILE_PATH = "../consts.json"

COMMANDS = {
    "UPLOAD": "UPLOAD",
    "HELP": "HELP",
    "EXIT": "EXIT",
    "LIST_FILES": "LIST_FILES",
    "DOWNLOAD": "DOWNLOAD",
    "REMOVE": "REMOVE",
    "CAT": "CAT"
}

REGEXES = {
    "UPLOAD": r"^upload\s+(\.?(/?[a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)\s+(([a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)$",
    "DOWNLOAD": r"^download\s+(([a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)\s+(\.?(/?[a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)$",
    "REMOVE": r"^remove\s+(([a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)$",
    "CAT": r"^cat\s+(([a-zA-Z0-9\-_]+)+(\.[a-zA-Z0-9]+)?)$",
    "HELP": r"^help$",
    "EXIT": r"^exit$",
    "LIST_FILES": r"^ls$"
}

def valid_command(command_str, command_type):
    """
    Returns True if the command_str is a valid command of type command_type, based on the regexes defined in REGEXES

    For example:
    If "upload file.txt" was written in the prompt, it would be wrong because upload requires 2 arguments, not 1
    """
    return re.search(REGEXES[command_type], command_str)

def parse_command(command_str, command_type):
    """
    Returns a tuple with the parsed command. Depends on the command_type that is used.

    Gets each of the groups of the regex according.
    """
    if command_type == COMMANDS["UPLOAD"]:
        match = re.search(REGEXES[command_type], command_str)

        file_name_origin = match.group(1)
        file_name_dest = match.group(4)

        return (command_type, file_name_origin, file_name_dest)
    elif command_type == COMMANDS["DOWNLOAD"]:
        match = re.search(REGEXES[command_type], command_str)

        file_name_origin = match.group(1)
        file_name_dest = match.group(4)

        return (command_type, file_name_origin, file_name_dest)
    
    elif command_type == COMMANDS["REMOVE"]:
        match = re.search(REGEXES[command_type], command_str)

        file_name_origin = match.group(1)

        return (command_type, file_name_origin)

    elif command_type == COMMANDS["CAT"]:
        match = re.search(REGEXES[command_type], command_str)

        file_name_origin = match.group(1)

        return (command_type, file_name_origin)

def main():
    global context, CONSTS

    # Create a ZeroMQ context. Need to be used if we want to the zmq library
    context = zmq.Context()

    # Load the constants defined in the consts.json file
    CONSTS = json.load(open(CONSTS_FILE_PATH, "r"))

    MS_IPV4 = CONSTS['metadata-server']['ipv4']
    MS_PORT = CONSTS['metadata-server']['port']

    # Creates the socket used to communicate with the Metadata Server
    ms_sock = context.socket(zmq.REQ)
    ms_sock.connect(f"tcp://{MS_IPV4}:{MS_PORT}")

    # Simple prompt
    while True:
        command_str = input("> ")

        # Printing the result of the help command
        if valid_command(command_str, COMMANDS["HELP"]):
            print("Commands:")
            print("upload <file_path_origin> <file_name_dest>")
            print("download <file_name_origin> <file_path_dest>")
            print("remove <file_name_origin>")
            print("cat <file_name_origin>")
            print("ls")
            print("exit")

        # Exiting
        elif valid_command(command_str, COMMANDS["EXIT"]):
            print("Exiting...")
            break
        
        # Listing files feature
        elif valid_command(command_str, COMMANDS["UPLOAD"]):
            # Get the correct arguments
            _, file_name_origin, file_name_dest = parse_command(command_str, COMMANDS["UPLOAD"])
            
            if not os.path.exists(file_name_origin):
                print("File does not exist")
                continue

            print(f"Uploading {file_name_origin} as {file_name_dest}")

            # Checking in which node the file is stored
            LOCATION_TO_STORE_REQ = CONSTS['operation-codes']['LOCATION_TO_STORE_REQ']

            location_to_store_req = {
                "code": LOCATION_TO_STORE_REQ,
                "file-name": file_name_dest
            }

            ms_sock.send(pickle.dumps(location_to_store_req))

            location_to_store_res = pickle.loads(ms_sock.recv())

            if location_to_store_res["status"] != "OK":
                print("Could not find a node to store the file")
                continue

            # Requesting the file to the correct Storage Node
            sn_ipv4 = location_to_store_res["ipv4"] # Storage Node IPv4
            sn_port = CONSTS['storage-nodes']['port']   # Storage Node Port

            sn_sock = context.socket(zmq.REQ)   # Storage Node Socket
            sn_sock.connect(f"tcp://{sn_ipv4}:{sn_port}")

            UPLOAD_FILE_REQ = CONSTS['operation-codes']['UPLOAD_FILE_REQ']

            upload_file_req = {
                "code": UPLOAD_FILE_REQ,
                "file-name": file_name_dest,
                "file-content": open(file_name_origin, "rb").read()
            }

            sn_sock.send(pickle.dumps(upload_file_req))

        # Requesting information about all the files to the Metadata Server
        elif valid_command(command_str, COMMANDS["LIST_FILES"]):
            LIST_FILES_REQ = CONSTS['operation-codes']['LIST_FILES_REQ']

            list_files_req = {
                "code": LIST_FILES_REQ
            }

            ms_sock.send(pickle.dumps(list_files_req))

            list_files_res = pickle.loads(ms_sock.recv())

            if list_files_res["status"] != "OK":
                print("Could not list files")
                continue

            for file_name in list_files_res["files"]:
                print(f"{file_name}")

        # Downloading a file to the local machine
        elif valid_command(command_str, COMMANDS["DOWNLOAD"]):
            _, file_name_origin, file_name_dest = parse_command(command_str, COMMANDS["DOWNLOAD"])

            print(f"Downloading {file_name_origin} as {file_name_dest}")

            # Request the machine which the file is stored
            LOCATION_TO_RETRIEVE_REQ = CONSTS['operation-codes']['LOCATION_TO_RETRIEVE_REQ']

            location_to_retrieve_req = {
                "code": LOCATION_TO_RETRIEVE_REQ,
                "file-name": file_name_origin
            }

            ms_sock.send(pickle.dumps(location_to_retrieve_req))

            location_to_retrieve_res = pickle.loads(ms_sock.recv())

            if location_to_retrieve_res["status"] != "OK":
                print("Could not find a node to retrieve the file from")
                continue

            # Sending a command directly to the Storage Node to download the file
            sn_ipv4 = location_to_retrieve_res["ipv4"] # Storage Node IPv4
            sn_port = CONSTS['storage-nodes']['port']   # Storage Node Port

            sn_sock = context.socket(zmq.REQ)   # Storage Node Socket
            sn_sock.connect(f"tcp://{sn_ipv4}:{sn_port}")
            
            DOWNLOAD_FILE_REQ = CONSTS['operation-codes']['DOWNLOAD_FILE_REQ']

            download_file_req = {
                "code": DOWNLOAD_FILE_REQ,
                "file-name": file_name_origin
            }

            sn_sock.send(pickle.dumps(download_file_req))

            download_file_res = pickle.loads(sn_sock.recv())

            if download_file_res["status"] != "OK":
                print("Could not download file")
                continue

            with open(file_name_dest, "wb") as file:
                file.write(download_file_res["file-content"])

        # Removing a file from the system
        elif valid_command(command_str, COMMANDS["REMOVE"]):
            _, file_name_origin = parse_command(command_str, COMMANDS["REMOVE"])

            print(f"Removing {file_name_origin}")

            # Requesting the location of the file to the Metadata Server
            LOCATION_TO_RETRIEVE_REQ = CONSTS['operation-codes']['LOCATION_TO_RETRIEVE_REQ']

            location_to_retrieve_req = {
                "code": LOCATION_TO_RETRIEVE_REQ,
                "file-name": file_name_origin
            }

            ms_sock.send(pickle.dumps(location_to_retrieve_req))

            location_to_retrieve_res = pickle.loads(ms_sock.recv())

            if location_to_retrieve_res["status"] != "OK":
                print("Could not find a node to retrieve the file from")
                continue

            # Sending a command directly to the Storage Node to remove the file
            sn_ipv4 = location_to_retrieve_res["ipv4"] # Storage Node IPv4
            sn_port = CONSTS['storage-nodes']['port']   # Storage Node Port

            sn_sock = context.socket(zmq.REQ)   # Storage Node Socket
            sn_sock.connect(f"tcp://{sn_ipv4}:{sn_port}")

            REMOVE_FILE_REQ = CONSTS['operation-codes']['REMOVE_FILE_REQ']

            remove_file_req = {
                "code": REMOVE_FILE_REQ,
                "file-name": file_name_origin
            }

            sn_sock.send(pickle.dumps(remove_file_req))

            remove_file_res = pickle.loads(sn_sock.recv())

            if remove_file_res["status"] != "OK":
                print("Could not remove file")
                continue

        # Simple cat command to see the content of the file in the system
        elif valid_command(command_str, COMMANDS["CAT"]):
            _, file_name_origin = parse_command(command_str, COMMANDS["CAT"])

            # Requesting the location of the file to the Metadata Server
            LOCATION_TO_RETRIEVE_REQ = CONSTS['operation-codes']['LOCATION_TO_RETRIEVE_REQ']

            location_to_retrieve_req = {
                "code": LOCATION_TO_RETRIEVE_REQ,
                "file-name": file_name_origin
            }

            ms_sock.send(pickle.dumps(location_to_retrieve_req))

            location_to_retrieve_res = pickle.loads(ms_sock.recv())

            if location_to_retrieve_res["status"] != "OK":
                print("Could not find a node to retrieve the file from")
                continue

            # Requesting the content of the file from the corrent Storage Node
            sn_ipv4 = location_to_retrieve_res["ipv4"] # Storage Node IPv4
            sn_port = CONSTS['storage-nodes']['port']   # Storage Node Port

            sn_sock = context.socket(zmq.REQ)   # Storage Node Socket
            sn_sock.connect(f"tcp://{sn_ipv4}:{sn_port}")

            CAT_FILE_REQ = CONSTS['operation-codes']['CAT_FILE_REQ']

            cat_file_req = {
                "code": CAT_FILE_REQ,
                "file-name": file_name_origin
            }

            sn_sock.send(pickle.dumps(cat_file_req))

            cat_file_res = pickle.loads(sn_sock.recv())

            if cat_file_res["status"] != "OK":
                print("Could not cat file")
                continue

            print(cat_file_res["file-content"].decode())

        # Handling miss typed commands
        else:
            print("Invalid command")


if __name__ == "__main__":
    main()
