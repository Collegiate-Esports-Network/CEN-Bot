"""Shared embed helpers."""

__author__ = "Justin Panchula"
__copyright__ = "Copyright CEN"
__credits__ = ["Justin Panchula"]
__version__ = "1.0.0"
__status__ = "Production"

# Third-party
import discord

BRAND_COLOR = 0x2374A5


def requester_footer(embed: discord.Embed, interaction: discord.Interaction) -> discord.Embed:
    """Stamp an embed with the requester's name, avatar, and the current UTC time.

    :param embed: the embed to stamp
    :type embed: discord.Embed
    :param interaction: the discord interaction from which the requester is derived
    :type interaction: discord.Interaction
    :returns: the same embed, mutated
    :rtype: discord.Embed
    """
    embed.set_footer(
        text=f"Requested by {interaction.user.display_name} • {discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}",
        icon_url=interaction.user.display_avatar.url,
    )
    return embed


def timestamp_footer(embed: discord.Embed) -> discord.Embed:
    """Stamp an embed with the current UTC time.

    :param embed: the embed to stamp
    :type embed: discord.Embed
    :returns: the same embed, mutated
    :rtype: discord.Embed
    """
    embed.set_footer(text=discord.utils.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC'))
    return embed