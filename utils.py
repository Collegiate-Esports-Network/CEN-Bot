__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Utility functions for discord.py"""

# Imports
import os
from pathlib import Path
import json

# Typing
from typing import Dict
from aiohttp import JsonPayload


class JsonInteracts():
    """.json file interactions
    """
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

    def write_json(path: Path, data: Dict) -> None:
        """Appends to a json file

        Args:
            filename (str): The name of the file to write to
            data (Any): The data to be written
        """
        with open(path, 'w') as f:
            json.dump(data, f, indent=4)
        return


def get_id(txt: str) -> int:
    """Strips inputs for ids

    Args:
        txt (str): Input text

    Returns:
        int: Stripped ID
    """
    return(int(txt.strip('<, #, @, &, >')))
