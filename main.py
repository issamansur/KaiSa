import os
import datetime

import asyncio
import aiohttp

from discord import (
    Intents,
    Message,
    utils,
    Status,
    Activity,
    ActivityType,
    app_commands,
    Object,
)

from discord.ext import commands
from youtube_dl import YoutubeDL

from cogs.source.actions import *
from cogs.source.answers import ANSWERS
from cogs.Settings import *

from cogs.Administration import Administration
from cogs.Voice import Voice
from cogs.Auth import Auth

client = commands.Bot(command_prefix="!", intents=Intents.all())

# -------------------------------------------------------
s1 = Status.dnd
a1 = Activity(
    type=ActivityType.watching,
    name="Hentai 🤤🔞",
)

s2 = Status.online
a2 = Activity(
    type=ActivityType.playing,
    name="League of Legends",
)


@client.event
async def on_ready():
    print(f"Has logged in as {client.user}")
    for server in client.guilds:
        await client.tree.sync(guild=Object(id=server.id))

    await client.add_cog(Administration(client))
    await client.add_cog(Voice(client))
    await client.add_cog(Auth(client))

    await client.change_presence(
        status=s2,
        activity=a2,
    )


@client.tree.command(
    name="testtest", description="Test to see if slash commands are working"
)
async def test(interaction):
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
async def reload(ctx: commands.Context):
    await client.close()


# --------------------------------------------------------------------------


client.run()
# os.system(f"start cmd /k python main.py")
