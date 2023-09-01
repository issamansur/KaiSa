from discord import utils, Status, Activity, ActivityType
from discord.ext.commands import Cog, command, event, Context

from cogs.Settings import *
from source.actions import actions

class Administration(Cog):
    def __init__(self, bot):
        self.client = bot
        self._last_member = None