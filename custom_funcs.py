__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Custom Functions"""

# Imports


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
        return int(txt.strip('<#@&>'))


# Testing
if __name__ == "__main__":
    print(0)