__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Utility functions for discord.py"""

# Imports
from pathlib import Path
import os
import json

class JsonInteracts():
    """.json file helper functions
    """
    def read(path: Path) -> dict:
        """Reads data from a .json file

        Args:
            path (Path): The path of the file to read

        Returns:
            Dict: The .json payload
        """
        if path.is_file():
            with open(path, 'r') as f:
                if os.path.getsize(path) == 0:
                    return {}
                else:
                    payload = json.load(f)
                return payload
        else:
            return {}

    def write(path: Path, data: dict) -> None:
            """Appends to a json file
            Args:
                filename (Path): The path of the file to write
                data (dict): The data to be written
            """
            # Check if file exists
            if not path.is_file():
                path.touch()
            
            # Commit update to file
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
    if type(txt) == int:
        return txt
    else:
        return(int(txt.strip('<#@&>')))
