import os
import datetime

import asyncio
import aiohttp

from discord import (
    app_commands,
    utils,
    
    Client,
    Intents,
    
    Object,
    Message,

    Status,
    ActivityType,
    Activity,
    Game,
    Streaming,
)

from discord.ext import commands
from youtube_dl import YoutubeDL

from cogs.source.actions import *
from cogs.source.answers import ANSWERS
from cogs.Settings import *

from cogs.Administration import Administration
from cogs.Voice import Voice
from cogs.Auth import Auth

MY_GUILD = Object(id=DEFAULT_GUILD_ID)

class SlashBot(commands.Bot):
    def __init__(self, *, command_prefix: str,  intents: Intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        '''
        for server in client.guilds:
            self.tree.copy_global_to(guild=Object(id=server.id))
            await self.tree.sync(guild=Object(id=server.id))
        '''
        self.tree.copy_global_to(guild=MY_GUILD)
        await self.tree.sync(guild=MY_GUILD)

client = SlashBot(command_prefix="!", intents=Intents.all())

# -------------------------------------------------------
activities = [
    Game(
        name="League of Legends",
    ),
    # ...
]


@client.event
async def on_ready():
    print(f"Has logged in as {client.user}")

    # set cogs
    await client.add_cog(Administration(client))
    await client.add_cog(Voice(client))
    await client.add_cog(Auth(client))

    # set slash commands

    # set status
    await client.change_presence(
        status=Status.online,
        activity=activities[0],
    )


@client.tree.command(
    name="test", 
    description="Test to see if slash commands are working"
)
async def _test(interaction):
    await interaction.response.send_message("Test")


@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return

    text = message.content
    words = text.split()
    author = message.author
    channel = message.channel

    if f"<@{ADMIN_USER_ID}>" in text:
        await channel.send(f"<@{author.id}>, Владелец заблокировал функцию упоминания.")
        await message.delete()
        return

    if str(words[0]).lower() in actions:
        try:
            member = await client.fetch_user(words[1][2:-1])
            await channel.send(
                content=f"{author.display_name} {formatting(words[0])} {member.display_name} {' '.join(words[2:])}"
            )
        except Exception as e:
            await channel.send(f"Something went wrong: {e}")
        return

    await client.process_commands(message)


@client.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        return
    raise error


@commands.is_owner()
@client.command(pass_context=False)
async def off(ctx: commands.Context):
    await client.close()


# --------------------------------------------------------------------------


client.run("")
# os.system(f"start cmd /k python main.py")
