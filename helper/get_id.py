__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Given a discord reference, returns the id"""


# get_id
def get_id(txt: str) -> int:
    """Strips inputs for ids

    Args:
        txt (str): Input text

    Returns:
        int: Stripped ID
    """
    if type(txt) is int:
        return txt
    else:
        return int(txt.strip('<#@&>'))