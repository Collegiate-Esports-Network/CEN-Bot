"""General-purpose formatting helpers."""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula"]
__version__ = "1.0.0"
__status__ = "Production"


def format_duration(seconds: int) -> str:
    """Format a duration in seconds as ``H:MM:SS`` or ``M:SS``.

    :param seconds: the total duration in seconds
    :type seconds: int
    :returns: human-readable duration string
    :rtype: str
    """
    m, s = divmod(seconds, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"
