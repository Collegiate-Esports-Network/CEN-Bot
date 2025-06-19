__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = "Justin Panchula"
__version__ = "1.0.0"
__status__ = "Production"
__doc__ = """Custom error modules"""

# Imports
from discord.ext.commands import CheckFailure


class ModuleNotEnabled(CheckFailure):
    """Module is not enabled.
    """
    def __init__(self) -> None:
        super().__init__("This module is not enabled.")