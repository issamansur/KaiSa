import io
from typing import Literal
import aiohttp

from discord import (
    app_commands,
    Interaction,
    VoiceClient,
    FFmpegPCMAudio,
    Embed,
    File,
    Color,
)
from discord.ext.commands import Cog, Context, command, is_owner
from components import ViewForSong, ViewForPlaylist
from source import ANSWERS
from vkpymusic import Service, Song, Playlist


# CONSTS
FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}
QUEUE_LIMIT = 15

# dict of guild with settings
guilds: dict[int:dict] = {}
RepeatMode: list[str] = ["OFF", "ONE", "ALL"]


# getter of Service
def get_service(interaction: Interaction) -> Service or None:
    return guilds.get(interaction.guild.id, {}).get("Service", None)


########
# CHECKS


# check: is guild?
async def is_guild(interaction: Interaction):
    channel = interaction.channel
    if channel is not None:
        return True
    else:
        await interaction.response.send_message(ANSWERS.IS_NOT_GUILD)
        return False


# check: is service registered?
async def is_registered(interaction: Interaction) -> bool:
    if get_service(interaction) is not None:
        return True
    else:
        await interaction.response.send_message(ANSWERS.NO_SERVICE)
        return False


# check: is user in voice?
async def is_user_in_voice(interaction: Interaction) -> bool:
    user_voice: VoiceClient = interaction.user.voice
    if user_voice is not None:
        return True
    else:
        await interaction.response.send_message(ANSWERS.NO_VOICE_USER)
        return False


# check: is ready to use?
async def is_ready(interaction: Interaction) -> bool:
    return (
        await is_guild(interaction)
        and await is_registered(interaction)
        and await is_user_in_voice(interaction)
    )


################
# Handler funcs:
# --------------
# 1. songs's
# 1.1. on_play
async def add_track(interaction: Interaction, song: Song):
    # main checks
    if not await is_ready(interaction):
        return False

    client_voice: VoiceClient = interaction.guild.voice_client
    user_voice: VoiceClient = interaction.user.voice

    # other checks
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

    # main logic
    queue: list[Song] = guilds[interaction.guild.id]["Queue"]
    length: int = len(queue)
    if length < QUEUE_LIMIT:
        guilds[interaction.guild.id]["Queue"].append(song)
        await interaction.channel.send(
            f"```> Трек добавлен в очередь! ({length + 1}/15)```"
        )
    else:
        await interaction.channel.send(ANSWERS.ON_LIST_FULL)
        return False

    if length == 0:
        play(interaction, client_voice, song)
    return True


# 1.2. on_save
async def save(interaction: Interaction, music: Song):
    async with aiohttp.ClientSession() as session:
        async with session.get(music.url) as resp:
            song = await resp.read()
            with io.BytesIO(song) as file:
                await interaction.channel.send(
                    f"{music}", file=File(file, f"{music}.mp3")
                )
    return True


# --------------
# 2. playlsits's
# 2.1. on_show
async def show_playlist(interaction: Interaction, playlist: Playlist):
    # main checks
    if not await is_ready(interaction):
        return None

    service: Service = get_service(interaction)
    songs: list[Song] = service.get_songs_by_playlist(playlist, 15)

    if len(songs) == 0:
        await interaction.response.send_message(ANSWERS.ON_LIST_EMPTY)
        return None
    else:
        songs_list = "**Список песен:**"
        for i, song in enumerate(songs, start=1):
            songs_list += f"\n**{i})** {song.title}"

        embed = Embed(
            title=playlist.title,
            url=None,
            description=songs_list,
            color=Color.dark_purple(),
        )
        embed.set_thumbnail(url=playlist.photo)
        embed.set_footer(text=f"Показано {len(songs)}/{playlist.count} из песен")

        return embed


# 2.2. on_play
async def add_playlist(interaction: Interaction, playlist: Playlist):
    #  main checks
    if not await is_ready(interaction):
        return False

    client_voice: VoiceClient = interaction.guild.voice_client
    user_voice: VoiceClient = interaction.user.voice

    # other checks
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

    # main logic
    service: Service = get_service(interaction)
    songs: list[Song] = service.get_songs_by_playlist(playlist, 15)
    queue: list[Song] = guilds[interaction.guild.id]["Queue"]
    for song in songs:
        queue.append(song)
    length: int = len(songs)
    length2: int = len(queue)
    await interaction.channel.send(f"```> Треки ({length}) добавлены в очередь!```")

    if length == length2:
        play(interaction, client_voice, queue[0])
    return True


#############
# Main funcs:
async def join(interaction: Interaction):
    # base checks
    if not await is_ready(interaction):
        return

    # other checks
    user_voice: VoiceClient = interaction.user.voice
    client_voice: VoiceClient = interaction.guild.voice_client
    if client_voice and client_voice.is_connected():
        if client_voice.channel.id == user_voice.channel.id:
            await interaction.channel.send(ANSWERS.JUST_THERE)
        else:
            await interaction.channel.send(ANSWERS.JUST_BUSY)
        return

    # joining
    client_voice = await user_voice.channel.connect(timeout=60.0, self_deaf=True)
    await interaction.channel.send(ANSWERS.ON_JOIN)
    return client_voice


def play(interaction: Interaction, voice: VoiceClient, song: Song):
    queue = guilds[interaction.guild.id]["Queue"]

    if len(queue) != 0:
        song = queue[0]
        source_path = song.url
        """
        # if need to save

        song.to_safe()
        file_name = f"{song}.mp3"
        file_path = os.path.join("Musics", file_name)

        if os.path.isfile(file_path):
            print(f"File found: {file_name}")
            source_path = file_path
        else:
            print(f"File not found: {file_name}")
        """

        client_voice: VoiceClient = voice
        client_voice.play(
            FFmpegPCMAudio(source=source_path, **FFMPEG_OPTIONS),
            after=lambda _: next(interaction, client_voice),
        )
        """
        if not os.path.isfile(file_path):
            get_service(interaction.guild.id).save_song(song)
        """
        return song


def next(interaction: Interaction, voice: VoiceClient):
    queue: list[Song] = guilds[interaction.guild.id]["Queue"]
    repeat_mode: bool = guilds[interaction.guild.id]["repeat_mode"]

    if len(queue) == 0:
        # await ctx.channel.send(ANSWERS.ON_END)
        return

    if repeat_mode == "OFF":
        queue.pop(0)
    elif repeat_mode == "ONE":
        pass
    elif repeat_mode == "ALL":
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
        guilds[guild_id]["repeat_mode"] = "OFF"
        guilds[guild_id]["Queue"] = []

    @command()
    @is_owner()
    async def services(self, ctx: Context):
        if not await is_guild(ctx):
            return
        await ctx.send(guilds)

    @app_commands.command(
        name="search",
        description="Search a song by query: title/artist",
    )
    @app_commands.describe(query="Song title or artist")
    async def _search(self, interaction: Interaction, query: str):
        if not await is_ready(interaction):
            return

        await interaction.response.send_message(ANSWERS.ON_SEARCH)
        songs = get_service(interaction).search_songs_by_text(query)

        if len(songs) == 0:
            await interaction.channel.send(ANSWERS.ON_NOT_FOUND)
            return

        # await interaction.channel.send(ANSWERS.ON_FOUND)

        for song in songs:
            view: ViewForSong = ViewForSong(song)

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
        name="search-playlist",
        description="Search user's playlist by query: title/artist",
    )
    @app_commands.describe(query="Playlist title or artist")
    async def _search_playlist(self, interaction: Interaction, query: str):
        if not await is_ready(interaction):
            return

        await interaction.response.send_message(ANSWERS.ON_SEARCH)
        playlists = get_service(interaction).search_playlists_by_text(query, 3)

        if len(playlists) == 0:
            await interaction.channel.send(ANSWERS.ON_NOT_FOUND)
            return

        # await interaction.channel.send(ANSWERS.ON_FOUND)

        for playlist in playlists:
            view: ViewForPlaylist = ViewForPlaylist(playlist)

            view.on_show = show_playlist
            view.on_play = add_playlist

            embed = Embed(
                title=playlist.title,
                description=f"{playlist.description}\n**{playlist.count}** песен",
                color=Color.dark_purple(),
            )
            embed.set_thumbnail(url=playlist.photo)

            view.message = await interaction.channel.send(
                embed=embed,
                view=view,
            )

    @app_commands.command(
        name="search-album",
        description="Search album of artist by query: title/artist",
    )
    @app_commands.describe(query="Album title or artist")
    async def _search_album(self, interaction: Interaction, query: str):
        if not await is_ready(interaction):
            return

        await interaction.response.send_message(ANSWERS.ON_SEARCH)
        playlists = get_service(interaction).search_albums_by_text(query, 3)

        if len(playlists) == 0:
            await interaction.channel.send(ANSWERS.ON_NOT_FOUND)
            return

        # await interaction.channel.send(ANSWERS.ON_FOUND)

        for playlist in playlists:
            view: ViewForPlaylist = ViewForPlaylist(playlist)

            view.on_show = show_playlist
            view.on_play = add_playlist

            embed = Embed(
                title=playlist.title,
                description=f"{playlist.description}\n**{playlist.count}** песен",
                color=Color.dark_purple(),
            )
            embed.set_thumbnail(url=playlist.photo)

            view.message = await interaction.channel.send(
                embed=embed,
                view=view,
            )

    @app_commands.command(
        name="list",
        description="Show list/queue of songs",
    )
    async def _list(self, interaction: Interaction):
        if not await is_ready(interaction):
            return

        queue: list[Song] = guilds[interaction.guild.id]["Queue"]
        repeat_mode: str = guilds[interaction.guild.id]["repeat_mode"]

        if len(queue) == 0:
            await interaction.response.send_message(ANSWERS.ON_LIST_EMPTY)
            return

        queue_list = ""
        for i, track in enumerate(queue, start=1):
            queue_list += f"**{i})** {track}\n"
        embed = Embed(
            title="Список песен:",
            url=None,
            description=queue_list,
            color=Color.blue(),
        )
        embed.set_footer(text=f"Повтор : {repeat_mode}")

        await interaction.response.send_message(embed=embed)

    @app_commands.command(
        name="skip",
        description="Skip current song",
    )
    async def _skip(self, interaction: Interaction):
        if not await is_ready(interaction):
            return

        client_voice: VoiceClient = interaction.guild.voice_client
        user_voice = VoiceClient = interaction.user.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:
                await interaction.response.send_message(ANSWERS.ON_SKIP)
                client_voice.stop()
            else:
                await interaction.response.send_message(ANSWERS.JUST_BUSY)
        else:
            await interaction.response.send_message(ANSWERS.NO_VOICE_BOT)

    @app_commands.command(
        name="repeat",
        description="Change repeat mode",
    )
    @app_commands.describe(mode="mode of repeating [OFF, ONE, ALL]")
    async def _repeat(
        self, interaction: Interaction, mode: Literal["OFF", "ONE", "ALL"]
    ):
        if not await is_ready(interaction):
            return

        client_voice: VoiceClient = interaction.guild.voice_client
        user_voice = VoiceClient = interaction.user.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:
                if mode in RepeatMode:
                    guilds[interaction.guild.id]["repeat_mode"] = mode
                    await interaction.response.send_message(
                        f"```Repeat mode: > {mode}```"
                    )
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
        if not await is_ready(interaction):
            return

        client_voice: VoiceClient = interaction.guild.voice_client
        user_voice = VoiceClient = interaction.user.voice

        if client_voice and client_voice.is_connected():
            if user_voice and client_voice.channel.id == user_voice.channel.id:
                guilds[interaction.guild.id]["Queue"] = []
                guilds[interaction.guild.id]["repeat_mode"] = "OFF"

                await interaction.response.send_message(ANSWERS.ON_QUIT)
                await client_voice.disconnect()
            else:
                await interaction.response.send_message(ANSWERS.JUST_BUSY)
        else:
            await interaction.response.send_message(ANSWERS.NO_VOICE_BOT)
