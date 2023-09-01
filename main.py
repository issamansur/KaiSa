import os
import datetime

import asyncio
import aiohttp

import discord
from discord.ext import commands
from youtube_dl import YoutubeDL

from elements.Views import ViewForPlaylist
from cogs.source.actions import *
from cogs.source.answers import ANSWERS
from cogs.Settings import *

from cogs.Administration import Administration

client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


guilds: dict = {}


# -------------------------------------------------------


@client.event()
async def on_ready():
    print(f"Has logged in as {client.user}")
    await client.add_cog(Administration(client))
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Hentai 🤤🔞",
        ),
    )

@client.event()
async def on_message(message: discord.Message):
    if message.author == client.user:
        return

    text = message.content
    words = text.split()
    author = message.author
    channel = message.channel

    if f"<@{ADMIN_USER_ID}>" in text:
        await channel.send(
            f"<@{author.id}>, Владелец заблокировал функцию упоминания."
        )
        await message.delete()
        return

    if str(words[0]).lower() in actions:
        try:
            member = await client.fetch_user(words[1][2:-1])
            await channel.send(
                content=
f"{author.display_name} {formatting(words[0])} {member.display_name} {' '.join(words[2:])}"
            )
        except Exception as e:
            await channel.send(f"Something went wrong: {e}")
        return

    await client.process_commands(message)


# --------------------------------------------------------------------------


client.run()
