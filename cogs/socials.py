__author__ = 'Justin Panchula'
__copyright__ = 'Copyright CEN'
__credits__ = 'Justin Panchula'
__version__ = '2.0.0'
__status__ = 'Production'
__doc__ = """Uses APIs to pull from Twitter and other socials"""

# Imports

class socials(commands.GroupCog, name='socials'):
    """These are all the logging functions
    """
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        super().__init__()
