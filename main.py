import os
import datetime

import asyncio
import aiohttp

from vkpymusic import TokenReceiver, Service, Music

import discord
from discord.ext import commands
from youtube_dl import YoutubeDL

from _elements import ViewWithButtons
from actions import *
from answers import ANSWERS
from ids import *


client = commands.Bot(command_prefix="!", intents=discord.Intents.all())


guilds: dict = {}
service: Service = Service.parse_config()


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


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
    role = discord.utils.get(member.guild.roles, id=DEFAULT_ROLE_ID)
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

    if f"<@{ADMIN_USER_ID}>" in text:
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
    if ctx.author.id != ADMIN_USER_ID:
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
    await ctx.send("1.0.1")


@client.command(pass_context=False)
async def mute_micro(ctx: commands.Context, member: discord.Member):
    if ctx.author.id != ADMIN_USER_ID:
        await ctx.send("Атятя")
        return
    try:
        await member.edit(mute=True)
        await ctx.send(f"Successfully mute micro of user {member}.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


@client.command(pass_context=False)
async def unmute_micro(ctx: commands.Context, member: discord.Member):
    if ctx.author.id != ADMIN_USER_ID:
        await ctx.send("Атятя")
        return
    try:
        await member.edit(mute=False)
        await ctx.send(f"Successfully unmute micro of user {member}.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


@client.command(pass_context=False)
async def ban(ctx: commands.Context, member: discord.Member, *, reason: str = ""):
    if ctx.author.id != ADMIN_USER_ID:
        await ctx.send("Атятя")
        return
    try:
        await ctx.guild.ban(user=member, reason=reason)
        await ctx.send(f"Successfully ban user {member}.")
    except Exception as e:
        await ctx.send(f"Something went wrong: {e}")


# -------------------------------------------------------


@client.command(
    pass_context=True, brief="This check a status of the bot", aliases=["bot"]
)
async def b(ctx):
    await ctx.send(ANSWERS.GREETING)


# -------------------------------------------------------
async def is_chat(ctx):
    user = ctx.message.author
    try:
        getattr(user, "voice")
        return True
    except AttributeError:
        await ctx.send(ANSWERS.IS_NOT_CHAT)
        return False


async def join(ctx):
    if not await is_chat(ctx):
        return
    user_voice: discord.VoiceClient = ctx.message.author.voice

    if not user_voice:
        await ctx.send(ANSWERS.NO_VOICE_USER)
        return

    client_voice: discord.VoiceClient = ctx.voice_client
    if client_voice and client_voice.is_connected():
        if client_voice.channel.id == user_voice.channel.id:
            await ctx.send(ANSWERS.JUST_THERE)
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
        return
    print(-2)
    client_voice = await user_voice.channel.connect(timeout=60.0, self_deaf=True)
    print(-1)
    await ctx.channel.send(ANSWERS.ON_JOIN)
    return client_voice


@client.command(
    pass_context=True,
    brief="This will search a song by name/author",
    aliases=["search"],
)
async def s(ctx, *, text: str):
    await ctx.channel.send(ANSWERS.ON_SEARCH)
    musics = service.search(text)

    if len(musics) == 0:
        await ctx.channel.send(ANSWERS.ON_TRACKS_NOT_FOUND)
        return
    
    await ctx.channel.send(ANSWERS.ON_TRACKS_FOUND)

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
    
    guild: dict[int: dict] = guilds.get(ctx.guild.id, {})
    queue: list[Music] = guild.get("queue", [])

    if len(queue) == 0:
        await ctx.channel.send(ANSWERS.ON_LIST_EMPTY)
    else:
        list = ""
        for i, track in enumerate(queue, start=1):
            queue_list += f"{i}. {track}\n"
        await ctx.channel.send(f"```> Список:\n{queue_list}```")


def play(ctx, voice, music: Music):
    guild: dict[int: dict] = guilds.get(ctx.guild.id, {})
    queue: list[Music] = guild.get("queue", [])

    if len(queue) != 0:
        music = Music.safe(queue[0])
        file_name = f"{music}.mp3"
        file_path = os.path.join("Music", file_name)

        source_path: str = ''
        if os.path.isfile(file_path):
            print(f"File found: {file_name}")
            source_path = file_path
        else:
            print(f"File not found: {file_name}")
            source_path=music.url

        
        client_voice: discord.VoiceClient = voice
        client_voice.play(
            discord.FFmpegPCMAudio(source=source_path, **FFMPEG_OPTIONS),
            after=lambda _: next(ctx, client_voice),
        )

        if os.path.isfile(file_path):
            service.save_music(music)
        return music


async def next(ctx, client_voice):
    guild: dict[int: dict] = guilds.get(ctx.guild.id, {})
    queue: list[Music] = guild.get("queue", [])
    is_repeat: bool = guilds[ctx.guild.id]["is_repeat"]

    if is_repeat == 'off':
        queue.pop()
    elif is_repeat == 'one':
        pass
    elif is_repeat == 'all':
        queue.append(queue.pop(0))


    if len(queue) == 0:
        await ctx.channel.send(ANSWERS.ON_END)
    else:
        music: Music = queue[0]
        await ctx.channel.send(ANSWERS.__f(f"Сейчас играет: {music}"))
        play(ctx, client_voice, music)


async def add_track(ctx, music):
    if not await is_chat(ctx):
        return
    
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice: discord.VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            pass
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
            return False
    else:
        print(0)
        client_voice = await join(ctx)
        print(1)
        if not client_voice:
            return False

    print(2)
    guild: dict[int: dict] = guilds.setdefault(ctx.guild.id, {})
    is_repeat: str = guild.setdefault("is_repeat", "off")
    queue: list[Music] = guild.get("queue", [])
    k: int = len(queue)

    if k < 15:
        print(3)
        queue.append(music)
        await ctx.channel.send(ANSWERS.__f(f"Трек добавлен в очередь! ({k + 1}/15)"))
    else:
        await ctx.channel.send(ANSWERS.ON_LIST_FULL)
        return

    if not client_voice.is_playing():
        title = play(ctx, client_voice)
        if title:
            await ctx.channel.send(ANSWERS.ON_ADDING_TRACK)
        else:
            await ctx.channel.send(ANSWERS.ON_END)
    return True


@client.command(pass_context=True, brief="This will skip current song", aliases=["sk"])
async def skip(ctx):
    if not await is_chat(ctx):
        return
    
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice = discord.VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            await ctx.send(ANSWERS.ON_SKIP)
            client_voice.stop()
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
    else:
        await ctx.send(ANSWERS.NO_VOICE_BOT)


@client.command()
async def r(ctx, repeat_type:str):
    if not await is_chat(ctx):
        return
    
    client_voice: discord.VoiceClient = ctx.voice_client
    user_voice = discord.VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            is_repeat: bool = guilds[ctx.guild.id]["is_repeat"]
            if repeat_type in ['one', 'all', 'off']:
                guilds[ctx.guild.id]["is_repeat"] = repeat_type
            else:
                await ctx.send(ANSWERS.INVALID_REPEAT_TYPE)
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
    else:
        await ctx.send(ANSWERS.NO_VOICE_BOT)


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
            await ctx.send(ANSWERS.ON_QUIT)
            guilds[ctx.guild.id] = {}
            await client_voice.disconnect()
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
    else:
        await ctx.send(ANSWERS.NO_VOICE_BOT)

# YOUTUBE

@client.command(
    pass_context=True,
    brief="This will play audio from youtube url",
    aliases=["youtube"],
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
            await ctx.send(ANSWERS.JUST_BUSY)
    else:
        client_voice = await join(ctx)
        if not client_voice:
            return False

    YDL_OPTIONS = {"format": "bestaudio", "noplaylist": "True"}

    with YoutubeDL(YDL_OPTIONS) as ydl:
        info = ydl.extract_info(url, download=False)
    URL = info["formats"][0]["url"]
    client_voice.play(discord.FFmpegPCMAudio(source=URL, **FFMPEG_OPTIONS))
    client_voice.is_playing()

    client_voice.volume = 100
    await ctx.send(ANSWERS.ON_PLAY)


# --------------------------------------------------------------------------


client.run()
input()