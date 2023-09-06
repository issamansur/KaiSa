from ctypes import Union
import io
import os
import aiohttp

from discord import File, VoiceClient, FFmpegPCMAudio
from discord.ext.commands import Context, Cog, Context, command, is_owner
import youtube_dl

from vkpymusic import TokenReceiver, Service, Song

from .Settings import *
from .source.actions import *
from .source.answers import *


from .elements.Views import ViewForSong, ViewForPlaylist


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

guilds: dict[int:dict] = {}


async def is_chat(ctx):
    user = ctx.message.author
    try:
        getattr(user, "voice")
        return True
    except AttributeError:
        await ctx.send(ANSWERS.IS_NOT_CHAT)
        return False


async def is_registered(ctx: Context) -> bool:
    if guilds.get(ctx.guild.id, {}).get("Service", None) != None:
        return True
    else:
        await ctx.send(ANSWERS.NO_SERVICE)
        return False


def get_service(ctx: Context) -> Service or None:
    return guilds.get(ctx.guild.id, {}).get("Service", None)


def get_queue(ctx: Context) -> Service:
    return guilds[ctx.guild.id]["Queue"]


def get_is_repeat(ctx: Context) -> Service:
    return guilds[ctx.guild.id]["is_repeat"]


async def join(ctx):
    if not await is_chat(ctx):
        return
    user_voice: VoiceClient = ctx.message.author.voice

    if not user_voice:
        await ctx.send(ANSWERS.NO_VOICE_USER)
        return

    client_voice: VoiceClient = ctx.voice_client
    if client_voice and client_voice.is_connected():
        if client_voice.channel.id == user_voice.channel.id:
            await ctx.send(ANSWERS.JUST_THERE)
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
        return
    client_voice = await user_voice.channel.connect(timeout=60.0, self_deaf=True)
    await ctx.channel.send(ANSWERS.ON_JOIN)
    return client_voice


async def add_track(ctx, song):
    if not await is_chat(ctx):
        return

    client_voice: VoiceClient = ctx.voice_client
    user_voice: VoiceClient = ctx.author.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            pass
        else:
            await ctx.send(ANSWERS.JUST_BUSY)
            return False
    else:
        client_voice = await join(ctx)
        if not client_voice:
            return False

    guild: dict[int:dict] = guilds.setdefault(ctx.guild.id, {})

    service: dict
    queue: list[Song] = guild.get("Queue", [])
    is_repeat: str = guild.setdefault("is_repeat", "off")
    k: int = len(queue)

    if k < 50:
        queue.append(song)
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


async def save(ctx, music: Song):
    async with aiohttp.ClientSession() as session:
        async with session.get(music.url) as resp:
            song = await resp.read()
            with io.BytesIO(song) as file:
                await ctx.channel.send(f"{music}", file=File(file, "{music}.mp3"))
    return


# ---------------------------------------------
def play(ctx: Context, voice, song: Song):
    guild: dict[int:dict] = guilds.get(ctx.guild.id, {})
    queue: list[Song] = guild.get("Queue", [])

    if len(queue) != 0:
        song = Song.safe(queue[0])
        file_name = f"{song}.mp3"
        file_path = os.path.join("Musics", file_name)

        source_path: str = ""
        if os.path.isfile(file_path):
            print(f"File found: {file_name}")
            source_path = file_path
        else:
            print(f"File not found: {file_name}")
            source_path = song.url

        client_voice: VoiceClient = voice
        client_voice.play(
            FFmpegPCMAudio(source=source_path, **FFMPEG_OPTIONS),
            after=lambda _: next(ctx, client_voice),
        )

        if os.path.isfile(file_path):
            get_service(ctx.guild.id).save_song(song)
        return song


def next(ctx):
    guild: dict[int:dict] = guilds.get(ctx.guild.id, {})
    queue: list[Song] = guilds[ctx.guild.id]["Queue"]
    is_repeat: bool = guilds[ctx.guild.id]["is_repeat"]

    if is_repeat == "off":
        queue.pop()
    elif is_repeat == "one":
        pass
    elif is_repeat == "all":
        queue.append(queue.pop(0))
    guilds.get(ctx.guild.id, {})

    if len(queue) == 0:
        # await ctx.channel.send(ANSWERS.ON_END)
        return

    song: Song = queue[0]
    # await ctx.channel.send(ANSWERS.__f(f"Сейчас играет: {song}"))
    play(ctx, song)


# ---------------------------------------------
class Voice(Cog):
    # ctor
    def __init__(self, bot):
        self.bot = bot

    # for Auth.py
    async def is_registered(self, guild_id: int) -> bool:
        if guilds.get(guild_id, {}).get("Service", None) != None:
            return True
        else:
            return False

    async def set_service(self, guild_id: int, service: Service):
        guilds.setdefault(guild_id, {})
        guilds[guild_id]["Service"] = service
        guilds[guild_id]["is_repeat"] = "off"
        guilds[guild_id]["Queue"] = []

    @command()
    @is_owner()
    async def services(self, ctx):
        if not await is_chat(ctx):
            return
        await ctx.send(guilds)

    @command(
        pass_context=True,
        brief="This will search a song by name/author",
        aliases=["search"],
    )
    async def s(self, ctx, *, text: str):
        if not await is_chat(ctx):
            return
        if not await is_registered(ctx):
            return

        await ctx.channel.send(ANSWERS.ON_SEARCH)
        songs = get_service(ctx).search_songs_by_text(text)

        if len(songs) == 0:
            await ctx.channel.send(ANSWERS.ON_TRACKS_NOT_FOUND)
            return

        await ctx.channel.send(ANSWERS.ON_TRACKS_FOUND)

        for song in songs:
            view: ViewForSong = ViewForSong(ctx, song)

            view.on_play = add_track
            view.on_save = save

            view.message = await ctx.channel.send(
                f"""```
Название: {song.title}
Исполнитель: {song.artist}
Длительность: {song.duration}
```
""",
                view=view,
            )

    @command(pass_context=True, brief="This show list/queue of songs", aliases=["list"])
    async def l(self, ctx):
        if not await is_chat(ctx):
            return
        if not await is_registered(ctx):
            return

        guild: dict[int:dict] = guilds.get(ctx.guild.id, {})
        queue: list[Song] = guild.get("Queue", [])

        if len(queue) == 0:
            await ctx.channel.send(ANSWERS.ON_LIST_EMPTY)
        else:
            list = ""
            for i, track in enumerate(queue, start=1):
                queue_list += f"{i}. {track}\n"
            await ctx.channel.send(f"```> Список:\n{queue_list}```")

    @command(pass_context=True, brief="This will skip current song", aliases=["sk"])
    async def skip(self, ctx):
        if not await is_chat(ctx):
            return
        if not await is_registered(ctx):
            return

        client_voice: VoiceClient = ctx.voice_client
        user_voice = VoiceClient = ctx.author.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:
                await ctx.send(ANSWERS.ON_SKIP)
                client_voice.stop()
            else:
                await ctx.send(ANSWERS.JUST_BUSY)
        else:
            await ctx.send(ANSWERS.NO_VOICE_BOT)

    @command()
    async def r(self, ctx, repeat_type: str):
        if not await is_chat(ctx):
            return
        if not await is_registered(ctx):
            return

        client_voice: VoiceClient = ctx.voice_client
        user_voice = VoiceClient = ctx.author.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:
                is_repeat: bool = guilds[ctx.guild.id]["is_repeat"]
                if repeat_type in ["one", "all", "off"]:
                    guilds[ctx.guild.id]["is_repeat"] = repeat_type
                else:
                    await ctx.send(ANSWERS.INVALID_REPEAT_TYPE)
            else:
                await ctx.send(ANSWERS.JUST_BUSY)
        else:
            await ctx.send(ANSWERS.NO_VOICE_BOT)

    @command(
        pass_context=True,
        brief="Makes the bot leave/quit your channel",
        aliases=["quit"],
    )
    async def q(self, ctx):
        if not await is_chat(ctx):
            return
        if not await is_registered(ctx):
            return

        client_voice: VoiceClient = ctx.voice_client
        user_voice = VoiceClient = ctx.author.voice

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

    @command(
        pass_context=True,
        brief="This will play audio from youtube url",
        aliases=["youtube"],
    )
    async def yt(self, ctx, url):
        if not await is_chat(ctx):
            return
        client_voice: VoiceClient = ctx.voice_client
        user_voice = VoiceClient = ctx.author.voice

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

        with youtube_dl(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(url, download=False)
        URL = info["formats"][0]["url"]
        client_voice.play(FFmpegPCMAudio(source=URL, **FFMPEG_OPTIONS))
        client_voice.is_playing()

        client_voice.volume = 100
        await ctx.send(ANSWERS.ON_PLAY)
