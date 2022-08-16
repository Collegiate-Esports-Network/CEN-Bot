__author__ = 'Justin Panchula'
__copyright__ = 'Copyright 2022'
__credits__ = 'Justin Panchula, Zach Lesniewski'
__license__ = 'MIT License'
__version__ = '1.0.0'
__status__ = 'Production'
__doc__ = """Utility functions for discord.py"""

# Imports
from pathlib import Path
import json

# Read json files
def json_read(path: Path):
    with open(path, 'r') as f:
        payload = json.load(f)
        return payload

def get_id(txt) -> int:
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
