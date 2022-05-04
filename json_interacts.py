# Imports
import os
from pathlib import Path
import json

# Typing
from typing import Any
from aiohttp import JsonPayload


def read_json(path: Path) -> JsonPayload:
    """Reads data from a .json file

    Args:
        filename (str): The filename to be read

    Returns:
        JsonPayload: The returned json object
    """
    with open(path, 'r') as f:
        if os.path.getsize(path) == 0:
            return
        else:
            return json.load(f)


def write_json(path: Path, data: Any) -> None:
    """Appends to a json file

    Args:
        filename (str): The name of the file to write to
        data (Any): The data to be written
    """
    with open(path, 'w') as f:
        json.dump(data, f, indent=4)
    return