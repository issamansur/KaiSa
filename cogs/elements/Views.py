from discord import Interaction, ButtonStyle
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
        button.emoji = "⏳"
        button.label = "Loading..."
        button.style = ButtonStyle.secondary
        button.disabled = True

    if result == -1:
        button.emoji = "🔄"
        button.label = "Try again"
        button.style = ButtonStyle.danger
        button.disabled = False


class ViewForSong(View):
    message = None

    on_play = None
    on_save = None

    def __init__(self, interaction, music, *, timeout=15) -> None:
        super().__init__(timeout=timeout)
        self.interaction: Interaction = interaction
        self.music: Song = music

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @button(label="Play song", style=ButtonStyle.primary, emoji="🎵")
    async def play_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await self.message.edit(view=self)

        await interaction.response.defer()
        try:
            await self.on_play(self.interaction, self.music)
            change(button, 1)
        except:
            change(button, -1)
        await interaction.followup.edit_message(self.message.id, view=self)

    @button(label="Download", style=ButtonStyle.primary, emoji="⬇")
    async def save_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await interaction.response.edit_message(view=self)

        await interaction.response.defer()

        try:
            await self.on_save(self.music)
            change(button, 1)
        except:
            change(button, -1)

        await interaction.followup.edit_message(self.message.id, view=self)


class ViewForPlaylist(View):
    message = None

    on_play = None
    on_show = None

    def __init__(self, ctx, playlist, *, timeout=30) -> None:
        super().__init__(timeout=timeout)
        self.context = ctx
        self.playlist = playlist

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True
        await self.message.edit(view=self)

    @button(label="Play album", style=ButtonStyle.primary, emoji="🎵")
    async def play_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await interaction.response.edit_message(view=self)

        await interaction.response.defer()

        try:
            await self.on_play(self.playlist)
            change(button, 1)
        except:
            change(button, -1)

        await interaction.followup.edit_message(self.message.id, view=self)

    @button(label="Show songs", style=ButtonStyle.primary, emoji="🔍")
    async def show_button(self, interaction: Interaction, button: Button):
        change(button, 0)
        await interaction.response.edit_message(view=self)

        await interaction.response.defer()

        try:
            await self.on_show(self.playlist)
            change(button, 1)
        except:
            change(button, -1)

        await interaction.followup.edit_message(self.message.id, view=self)
