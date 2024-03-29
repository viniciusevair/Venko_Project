import json
import os
import shutil
import socket
from pathlib import Path
from typing import Any, Dict

INT_SIZE = 4
ENCODING_FORMAT = "utf-8"


def tree_list_content(directory: str) -> str:
    """Mimics the output of the 'tree' command from the terminal. Return it as a string."""
    directory = os.path.expanduser(directory or ".")

    # Tree function lightly adapted from https://stackoverflow.com/a/59109706
    # prefix components:
    space = "    "
    branch = "│   "
    # pointers:
    tee = "├── "
    last = "└── "

    def tree(dir_path: Path, prefix: str = ""):
        """
        A recursive generator, given a directory Path object
        will yield a visual tree structure line by line
        with each line prefixed by the same characters
        """

        contents = [path for path in dir_path.iterdir()]
        # contents each get pointers that are ├── with a final └── :
        pointers = [tee] * (len(contents) - 1) + [last]
        for pointer, path in zip(pointers, contents):
            yield prefix + pointer + path.name
            if path.is_dir():  # extend the prefix and recurse:
                extension = branch if pointer == tee else space
                # i.e. space because last, └── , above so no more |
                yield from tree(path, prefix=prefix + extension)

    string = str(Path(os.path.basename(directory))) + "\n"
    for line in tree(Path(directory)):
        string += line + "\n"

    return string


def list_content(directory: str) -> str:
    """Mimics the output of the 'ls' command from the terminal. Return it as a string."""
    directory = os.path.expanduser(directory or ".")
    string = ""
    for line in os.listdir(directory):
        string += line + "\n"
    return string


def file_encode(file_path: str, file_compressed: bool) -> bytes:
    """
    Receives a file with full path and returns a binary containing the length of the file name, the file
    name, the length of the file and the file concatenated.
    """
    file_info = {}
    file_info["is_compressed"] = file_compressed
    file_info["file_name"] = os.path.basename(file_path)
    file_info["permissions"] = os.stat(file_path).st_mode

    try:
        with open(file_path, "rb") as file:
            file_data = file.read()
    except PermissionError:
        raise PermissionError(
            f"You don't have permission to read {file_info['file_name']}."
        )

    file_info["file_len"] = len(file_data)
    metadata_bytes = json.dumps(file_info).encode(ENCODING_FORMAT)
    metadata_length_bytes = len(metadata_bytes).to_bytes(INT_SIZE)
    encoded_file = metadata_length_bytes + metadata_bytes + file_data

    return encoded_file


def get_file_metadata(client_socket: socket.socket) -> Dict[str, Any]:
    """
    Receives metadata from the socket as JSON, decodes it to a Python dictionary,
    and returns it to the caller.
    """
    metadata_length_bytes = client_socket.recv(INT_SIZE)
    metadata_length = int.from_bytes(metadata_length_bytes)

    metadata_bytes = client_socket.recv(metadata_length)
    file_metadata = json.loads(metadata_bytes)

    return file_metadata


def text_message_encode(message: str) -> bytes:
    """
    Receives a string and returns its length along with the encoded string,
    allowing the caller to handle sending text through the socket.
    """
    message_bytes = message.encode(ENCODING_FORMAT)
    text_len = len(message_bytes)

    binary_data = text_len.to_bytes(INT_SIZE)
    binary_data += message_bytes

    return binary_data


def delete_file(file_path: str):
    """
    Delete a file from the server.

    The function can also delete a directory.
    All validation was made before calling this function.
    """
    try:
        if os.path.isdir(file_path):
            shutil.rmtree(file_path)
        else:
            os.remove(file_path)
    except FileNotFoundError:
        raise FileNotFoundError(f"Error: {file_path} was not found.")
    except PermissionError:
        raise PermissionError(
            f"Error: You don't have permission to delete {file_path}."
        )
