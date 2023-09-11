from discord import Interaction, Message, ButtonStyle, Embed, Color
from discord.ui import View, Button, button
from discord.ext.commands import Context

from vkpymusic import Song, Playlist


def change(button: Button, result: int):
    if result == 1:
        button.emoji = "✅"
        button.label = "Success"
        button.style = ButtonStyle.success
        button.disabled = True

    if result == 0:
        button.emoji = "⌛"
        button.label = "Loading..."
        button.style = ButtonStyle.secondary
        button.disabled = True

    if result == -1:
        button.emoji = "🔄"
        button.label = "Try again"
        button.style = ButtonStyle.danger
        button.disabled = False


class ViewForSong(View):
    message: Message = None

    on_play = None
    on_save = None

    def __init__(self, song, *, timeout=15) -> None:
        super().__init__(timeout=timeout)
        self.song: Song = song

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)
        # await self.message.delete()

    @button(label="Play song", style=ButtonStyle.primary, emoji="🎵")
    async def play_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await self.message.edit(view=self)

        await interaction.response.defer()
        try:
            res: bool = await self.on_play(interaction, self.song)
            if res:
                change(button, 1)
            else:
                change(button, -1)
        except:
            change(button, -1)
        await interaction.followup.edit_message(self.message.id, view=self)

    @button(label="Download", style=ButtonStyle.primary, emoji="⬇")
    async def save_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await self.message.edit(view=self)

        await interaction.response.defer()
        try:
            res: bool = await self.on_save(interaction, self.song)
            if res:
                change(button, 1)
            else:
                change(button, -1)
        except:
            change(button, -1)

        await interaction.followup.edit_message(self.message.id, view=self)


class ViewForPlaylist(View):
    message: Message = None

    on_show = None
    on_play = None

    def __init__(self, playlist, *, timeout=30) -> None:
        super().__init__(timeout=timeout)
        self.playlist: Playlist = playlist

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @button(label="Show songs", style=ButtonStyle.primary, emoji="🔍")
    async def show_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await self.message.edit(view=self)

        await interaction.response.defer()
        try:
            res: Embed = await self.on_show(interaction, self.playlist)
            if res:
                change(button, 1)
            else:
                change(button, -1)
        except:
            change(button, -1)

        await interaction.followup.edit_message(self.message.id, view=self, embed=res)

    @button(label="Play album", style=ButtonStyle.primary, emoji="🎵")
    async def play_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await self.message.edit(view=self)

        await interaction.response.defer()
        try:
            res: bool = await self.on_play(interaction, self.playlist)
            if res:
                change(button, 1)
            else:
                change(button, -1)
        except:
            change(button, -1)

        await interaction.followup.edit_message(self.message.id, view=self)
