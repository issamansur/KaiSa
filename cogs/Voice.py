import io
import os
import aiohttp

from discord import app_commands, Interaction, VoiceClient, FFmpegPCMAudio, File
from discord.ext.commands import Cog, Context, command, is_owner
import youtube_dl

from vkpymusic import Service, Song, Playlist

from .Settings import *
from .source.actions import *
from .source.anaswers import ANSWERS

from .elements.Views import ViewForSong, ViewForPlaylist


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}

guilds: dict[int:dict] = {}


async def is_chat(interaction: Interaction):
    channel = interaction.channel
    return channel != None


async def is_registered(ctx: Interaction) -> bool:
    if guilds.get(ctx.guild.id, {}).get("Service", None) != None:
        return True
    else:
        await ctx.response.send_message(ANSWERS.NO_SERVICE)
        return False


def get_service(ctx: Context) -> Service or None:
    return guilds.get(ctx.guild.id, {}).get("Service", None)


def get_queue(ctx: Context) -> Service:
    return guilds[ctx.guild.id]["Queue"]


def get_is_repeat(ctx: Context) -> Service:
    return guilds[ctx.guild.id]["is_repeat"]


async def join(interaction: Interaction):
    user_voice: VoiceClient = interaction.user.voice

    if not user_voice:
        await interaction.channel.send(ANSWERS.NO_VOICE_USER)
        return

    client_voice: VoiceClient = interaction.guild.voice_client
    if client_voice and client_voice.is_connected():
        if client_voice.channel.id == user_voice.channel.id:
            await interaction.channel.send(ANSWERS.JUST_THERE)
        else:
            await interaction.channel.send(ANSWERS.JUST_BUSY)
        return
    client_voice = await user_voice.channel.connect(timeout=60.0, self_deaf=True)
    await interaction.channel.send(ANSWERS.ON_JOIN)
    return client_voice


async def add_track(interaction: Interaction, song: Song):
    client_voice: VoiceClient = interaction.guild.voice_client
    user_voice: VoiceClient = interaction.user.voice

    if client_voice and client_voice.is_connected():
        if user_voice and client_voice.channel.id == user_voice.channel.id:
            pass
        else:
            await interaction.channel.send(ANSWERS.JUST_BUSY)
            return False
    else:
        client_voice = await join(interaction)
        if not client_voice:
            return False

    queue: list[Song] = guilds[interaction.guild.id]["Queue"]
    length: int = len(queue)
    if length < 50:
        guilds[interaction.guild.id]["Queue"].append(song)
        await interaction.channel.send(
            # ANSWERS.__f(f"Трек добавлен в очередь! ({length + 1}/15)")
            "123"
        )
    else:
        await interaction.channel.send(ANSWERS.ON_LIST_FULL)
        return

    if length == 0:
        title = play(interaction, client_voice, song)
        if title:
            await interaction.channel.send(ANSWERS.ON_ADDING_TRACK)
        else:
            await interaction.channel.send(ANSWERS.ON_END)
    return True


async def save(interaction: Interaction, music: Song):
    async with aiohttp.ClientSession() as session:
        async with session.get(music.url) as resp:
            song = await resp.read()
            with io.BytesIO(song) as file:
                await interaction.channel.send(
                    f"{music}", file=File(file, "{music}.mp3")
                )
    return


# ---------------------------------------------
def play(interaction: Context, voice: VoiceClient, song: Song):
    queue = guilds[interaction.guild.id]["Queue"]

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
            after=lambda _: next(interaction, client_voice),
        )

        if os.path.isfile(file_path):
            get_service(interaction.guild.id).save_song(song)
        return song


def next(interaction: Interaction, voice: VoiceClient):
    guild: dict[int:dict] = guilds.get(interaction.guild.id, {})
    queue: list[Song] = guilds[interaction.guild.id]["Queue"]
    is_repeat: bool = guilds[interaction.guild.id]["is_repeat"]

    if is_repeat == "off":
        queue.pop()
    elif is_repeat == "one":
        pass
    elif is_repeat == "all":
        queue.append(queue.pop(0))
    guilds.get(interaction.guild.id, {})

    if len(queue) == 0:
        # await ctx.channel.send(ANSWERS.ON_END)
        return

    song: Song = queue[0]
    # await ctx.channel.send(ANSWERS.__f(f"Сейчас играет: {song}"))
    play(interaction, voice, song)


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
    async def services(self, ctx: Context):
        if not await is_chat(ctx):
            return
        await ctx.send(guilds)

    @app_commands.command(
        name="search",
        description="Search a song by title/artist",
    )
    @app_commands.describe(text="Song title or artist")
    async def _search(self, interaction: Interaction, text: str):
        if not await is_chat(interaction):
            return
        if not await is_registered(interaction):
            return

        await interaction.response.send_message(ANSWERS.ON_SEARCH)
        songs = get_service(interaction).search_songs_by_text(text)

        if len(songs) == 0:
            await interaction.channel.send(ANSWERS.ON_TRACKS_NOT_FOUND)
            return

        await interaction.channel.send(ANSWERS.ON_TRACKS_FOUND)

        for song in songs:
            view: ViewForSong = ViewForSong(interaction, song)

            view.on_play = add_track
            view.on_save = save

            view.message = await interaction.channel.send(
                f"""```
Название: {song.title}
Исполнитель: {song.artist}
Длительность: {song.duration}
```
""",
                view=view,
            )

    @app_commands.command(
        name="list",
        description="Show list/queue of songs",
    )
    async def _list(self, interaction: Interaction):
        if not await is_chat(interaction):
            return
        if not await is_registered(interaction):
            return

        queue: list[Song] = guilds[interaction.guild.id]["Queue"]

        if len(queue) == 0:
            await interaction.response.send_message(ANSWERS.ON_LIST_EMPTY)
        else:
            list = ""
            for i, track in enumerate(queue, start=1):
                queue_list += f"{i}. {track}\n"
            await interaction.response.send_message(f"```> Список:\n{queue_list}```")

    @app_commands.command(
        name="skip",
        description="Skip current song",
    )
    async def _skip(self, ctx: Context):
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

    @app_commands.command(
        name="repeat",
        description="Change repeat mode",
    )
    @app_commands.describe(name="mode", description="mode of repeating [off, one, all]")
    async def _repeat(self, interaction: Interaction, mode: str):
        if not await is_chat(interaction):
            return
        if not await is_registered(interaction):
            return

        client_voice: VoiceClient = interaction.guild.voice_client
        user_voice = VoiceClient = interaction.user.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:
                if mode in ["one", "all", "off"]:
                    guilds[interaction.guild.id]["is_repeat"] = mode
                    await interaction.response.send_message(f"```Repeat mode: {mode}```")
                else:
                    await interaction.response.send_message(ANSWERS.INVALID_REPEAT_TYPE)
            else:
                await interaction.response.send_message(ANSWERS.JUST_BUSY)
        else:
            await interaction.response.send_message(ANSWERS.NO_VOICE_BOT)

    @app_commands.command(
        name="quit",
        description="Makes bot to quit/leave the channel",
    )
    async def _quit(self, interaction: Interaction):
        if not await is_chat(interaction):
            return
        if not await is_registered(interaction):
            return

        client_voice: VoiceClient = interaction.guild.voice_client
        user_voice = VoiceClient = interaction.user.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:

                guilds[interaction.guild.id]["Queue"] = []
                guilds[interaction.guild.id]["is_repeat"] = 'off'
                
                await interaction.response.send_message(ANSWERS.ON_QUIT)
                await client_voice.disconnect()
            else:
                await interaction.response.send_message(ANSWERS.JUST_BUSY)
        else:
            await interaction.response.send_message(ANSWERS.NO_VOICE_BOT)

    # YOUTUBE

    @command(
        pass_context=True,
        brief="This will play audio from youtube url",
        aliases=["youtube"],
    )
    async def yt(self, ctx: Context, url: str):
        if not await is_chat(ctx):
            return
        client_voice: VoiceClient = ctx.guild.voice_client
        user_voice = VoiceClient = ctx.user.voice

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
