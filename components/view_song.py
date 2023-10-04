from discord import Interaction, Message, ButtonStyle
from discord.ui import View, Button, button
from vkpymusic import Song

from utils import change

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
