import asyncio

from discord import FFmpegOpusAudio, Interaction, VoiceClient
from vkpymusic import Song

class Player:
    def __init__(self):
        self.queue = asyncio.Queue()

    async def play_next_song(self, interaction: Interaction, voice: VoiceClient):
        song = await self.queue.get()
        if song is None:
            return

        # play the song
        source = await FFmpegOpusAudio.from_probe(song.url)
        voice.play(source, after=lambda e: self.queue.task_done())

        # send a message to the channel
        await interaction.channel.send(f"Now playing: {song.title}")

        # start playing the next song
        await self.play_next_song(interaction, voice)

    def play(self, interaction: Interaction, voice: VoiceClient, song: Song):
        self.queue.put(song)

        if self.queue.empty():
            # start playing the song if the queue was empty
            asyncio.create_task(self.play_next_song(interaction, voice))