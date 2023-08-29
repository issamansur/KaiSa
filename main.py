import os
import datetime

import asyncio
import aiohttp

from vkpymusic import Service, Music

import discord
from discord.ext import commands
from youtube_dl import YoutubeDL

from _elements import ViewWithButtons
from actions import *
from answers import *
from ids import *


client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


guilds: dict = {}

service: Service = Service.parse_config()


@client.event
async def on_ready():
    print(f"Has logged in as {client.user}")
    await client.change_presence(
        status=discord.Status.dnd,
        activity=discord.Activity(
            type=discord.ActivityType.watching,
            name="Hentai 🤤🔞",
        ),
    )


@client.event
async def on_member_join(member):
    await member.send(f"Добро пожаловать в клуб стримера EDEXADE, {member}!")
    role = discord.utils.get(member.guild.roles, id=DEFAULT_ROLE)
    await member.add_roles(role, reason="Вход на сервер")
    print("Роль успешно выдана!")


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    text = message.content
    words = text.split()
    author = message.author
    channel = message.channel

    if f"<@{MY_ROLE}>" in text:
        await message.channel.send(
            f"<@{message.author.id}>, Владелец заблокировал функцию упоминания."
        )
        await message.delete()

    if str(words[0]).lower() in actions:
        try:
            member = await client.fetch_user(words[1][2:-1])
            await channel.send(
                f"{author.display_name} {formatting(words[0])} {member.display_name} {' '.join(words[2:])}"
            )
        except Exception as e:
            await channel.send(f"Something went wrong: {e}")

    else:
        await client.process_commands(message)


# ------------------------------------------------------------


async def timeout_user(*, user_id: int, guild_id: int, until):
    headers = {"Authorization": f"Bot {client.http.token}"}
    url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
    timeout = (
        datetime.datetime.utcnow() + datetime.timedelta(minutes=until)
    ).isoformat()
    json = {"communication_disabled_until": timeout}
    client.session = aiohttp.ClientSession()
    async with client.session.patch(url, json=json, headers=headers) as session:
        status = session.status
        await client.session.close()
        if status in range(200, 299):
            return True
        return False


@client.command(pass_context=False)
async def mute(ctx: commands.Context, member: discord.Member, until: int):
    if ctx.author.id != MY_ROLE:
        await ctx.send("Атятя")
        return
    handshake = await timeout_user(
        user_id=member.id, guild_id=ctx.guild.id, until=until
    )
    if handshake:
        return await ctx.send(
            f"Successfully timed out user {member} for {until} minutes."
        )
    await ctx.send("Something went wrong")


@client.command(pass_context=False)
async def version(ctx: commands.Context):
    await ctx.send("1.0.3")


@client.command(pass_context=False)
async def mute_micro(ctx: commands.Context, member: discord.Member):
    if ctx.author.id != MY_ROLE:
        await ctx.send("Атятя")
        return
    try:
        await member.edit(mute=True)
        await ctx.send(f"Successfully mute micro of user {member}.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


@client.command(pass_context=False)
async def unmute_micro(ctx: commands.Context, member: discord.Member):
    if ctx.author.id != MY_ROLE:
        await ctx.send("Атятя")
        return
    try:
        await member.edit(mute=False)
        await ctx.send(f"Successfully unmute micro of user {member}.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


@client.command(pass_context=False)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = ""):
    if ctx.author.id != MY_ROLE:
        await ctx.send("Атятя")
        return
    try:
        await ctx.guild.ban(user=member, reason=reason)
        await ctx.send(f"Successfully ban user {member}.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


# -------------------------------------------------------


@client.command(
    pass_context=True, brief="This check a status of the bot", aliases=["b"]
)
async def bot(ctx):
    await ctx.send(GREETING)


# -------------------------------------------------------
async def is_chat(ctx):
    user = ctx.message.author
    try:
        getattr(user, "voice")
        return True
    except AttributeError:
        await ctx.send(IS_NOT_CHAT)
        return False


async def join(ctx):
    if not await is_chat(ctx):
        return
    user_voice: discord.VoiceClient = ctx.message.author.voice

    if not user_voice:
        await ctx.send(NO_VOICE_USER)
        return

    client_voice: discord.VoiceClient = ctx.voice_client
    if client_voice and client_voice.is_connected():
        if client_voice.channel.id == user_voice.channel.id:
            await ctx.send(JUST_THERE)
        else:
            await ctx.send(JUST_BUSY)
        return

    client_voice = await user_voice.channel.connect(timeout=60.0, self_deaf=True)
    await ctx.send(ON_JOIN)
    return client_voice


@client.command(
    pass_context=True,
    brief="This will search a song 'search [name/author]'",
    aliases=["search"],
)
async def s(ctx, *, text: str):
    await ctx.channel.send(ON_SEARCH)
    musics = service.search(text)

    if len(musics) == 0:
        await ctx.channel.send(ON_NOT_FOUND)
        return
    else:
        await ctx.channel.send(ON_FOUND)

    for music in musics:
        view: ViewWithButtons = ViewWithButtons(ctx, music)
        view.on_play = add_track

        view.message = await ctx.channel.send(
            f"""```
Название: {music.title}
Исполнитель: {music.artist}
Длительность: {music.duration}
```
    """,
            view=view,
        )


@client.command(
    pass_context=True, brief="This show list/queue of songs", aliases=["list"]
)
async def l(ctx):
    if not await is_chat(ctx):
        return
    lst = guilds.setdefault(ctx.guild.id, [])
    if len(lst) == 0:
        await ctx.channel.send(ON_LIST_EMPTY)
    else:
        list = ""
        for i, track in enumerate(lst, start=1):
            list += f"{i}. {track}\n"
        await ctx.channel.send(f"```> Список:\n{list}```")


def play(ctx, voice, first=False):
    client_voice: discord.VoiceClient = voice

    if not first:
        guilds[ctx.guild.id].pop(0)

    musics: list[Music] = guilds.setdefault(ctx.guild.id, [])
    if len(musics) != 0:
        music = Music.safe(musics[0])
        file_name = f"{music}.mp3"
        file_path = os.path.join("Music", file_name)

        if os.path.isfile(file_path):
            print(f"File found: {file_name}")
            client_voice.play(
                discord.FFmpegPCMAudio(source=file_path),
                after=lambda _: play(ctx, client_voice),
            )
        else:
            print(f"File not found: {file_name}")
            FFMPEG_OPTIONS = {
                "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
                "options": "-vn",
            }
            client_voice.play(
                discord.FFmpegPCMAudio(
                    source=music.url,
                    **FFMPEG_OPTIONS,
                ),
                after=lambda _: play(ctx, client_voice),
            )
            service.save_music(music)
        return music


async def add_track(ctx, music):
    if not await is_chat(ctx):
        return
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice: discord.VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            pass
        else:
            await ctx.send(JUST_BUSY)
            return False
    else:
        client_voice = await join(ctx)
        if not client_voice:
            return False

    k = len(guilds.setdefault(ctx.guild.id, []))
    if k < 15:
        guilds[ctx.guild.id].append(music)

        await ctx.channel.send(f"```> Трек добавлен в очередь! ({k + 1}/15)```")
    else:
        await ctx.channel.send("```> В очереди уже 15 треков! ```")

    if not client_voice.is_playing():
        title = play(ctx, client_voice, True)
        if title:
            await ctx.channel.send(title)
        else:
            await ctx.channel.send(ON_END)
    return True


@client.command(
    pass_context=True,
    brief="This will play a song from youtube 'play [url]'",
    aliases=["play_"],
)
async def yt(ctx, url):
    if not await is_chat(ctx):
        return
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice = discord.VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            if client_voice.is_playing():
                return  # !!!
            else:
                pass
        else:
            await ctx.send(JUST_BUSY)
    else:
        client_voice = await join(ctx)
        if not client_voice:
            return False

    YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}
    FFMPEG_OPTIONS = {
        "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        "options": "-vn",
    }

    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
    URL = info["formats"][0]["url"]
    client_voice.play(discord.FFmpegPCMAudio(source=URL, **FFMPEG_OPTIONS))
    client_voice.is_playing()

    client_voice.volume = 100
    await ctx.send(ON_PLAY)


@client.command(pass_context=True, brief="This will stop a song 'stop'", aliases=["st"])
async def skip(ctx):
    if not await is_chat(ctx):
        return
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice = discord.VoiceClient = ctx.author.voice
    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            await ctx.send(ON_SKIP)
            client_voice.stop()
        else:
            await ctx.send(JUST_BUSY)
    else:
        await ctx.send(NO_VOICE_BOT)


@client.command()
async def r(ctx):
    if not await is_chat(ctx):
        return
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice = discord.VoiceClient = ctx.author.voice
    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            is_repeat: bool = guilds[ctx.guild.id]["is_repeat"]
            guilds[ctx.guild.id]["is_repeat"] = not is_repeat
        else:
            await ctx.send(JUST_BUSY)
    else:
        await ctx.send(NO_VOICE_BOT)


@client.command(
    pass_context=True,
    brief="Makes the bot leave/quit your channel",
    aliases=["quit"],
)
async def q(ctx):
    if not await is_chat(ctx):
        return
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice = discord.VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            await ctx.send(ON_QUIT)
            guilds[ctx.guild.id] = []
            await client_voice.disconnect()
        else:
            await ctx.send(JUST_BUSY)
    else:
        await ctx.send(NO_VOICE_BOT)


# --------------------------------------------------------------------------


client.run()
