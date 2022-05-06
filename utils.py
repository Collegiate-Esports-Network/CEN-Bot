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
from typing import Any


class JsonInteracts():
    """.json file interactions
    """
    class Guilds():
        """.json file interactions for guild specific functions
        """
        def read_json(path: Path, guildID: int) -> dict:
            """Reads data from a .json file

            Args:
                filename (str): The filename to be read
                guildID (int): The guildID

            Returns:
                dict: The data recalled for the guild
            """
            with open(path, 'r') as f:
                if os.path.getsize(path) == 0:
                    return
                else:
                    payload = json.load(f)
                    return payload[str(guildID)]

        def write_json(path: Path, data: Any, guildID: int) -> None:
            """Appends to a json file

            Args:
                filename (str): The name of the file to write to
                data (Any): The data to be written
                guildID (int): The guild ID
            """
            with open(path, 'r') as f:
                if os.path.getsize(path) == 0:
                    payload = {}
                    payload[str(guildID)] = data
                    with open(path, 'w') as f:
                        json.dump(payload, f, indent=4)
                    return
                else:
                    payload[str(guildID)] = data
                    print(payload)
                    with open(path, 'w') as f:
                        json.dump(payload, f, indent=4)
                    return

    class Standard():
        def read_json(path: Path) -> dict:
            """Reads data from a .json file

            Args:
                filename (str): The filename to be read
                guildID (int): The guildID

            Returns:
                dict: The data recalled for the guild
            """
            with open(path, 'r') as f:
                if os.path.getsize(path) == 0:
                    return
                else:
                    payload = json.load(f)
                    return payload

        def write_json(path: Path, data: dict) -> None:
            """Appends to a json file

            Args:
                filename (str): The name of the file to write to
                data (dict): The data to be written
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
    return(int(txt.strip('<#@&>')))
