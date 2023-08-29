import discord


class ViewWithButtons(discord.ui.View):
    message = None
    on_play = None

    def __init__(self, ctx, music, *, timeout=60, on_play) -> None:
        super().__init__(timeout=timeout)
        self.context = ctx
        self.music = music

    async def on_timeout(self) -> None:
        for item in self.children:
            item.disabled = True

        # self.clear_items()

        await self.message.edit(view=self)

    @staticmethod
    def change(button: discord.ui.Button, result: bool):
        if result:
            button.emoji = "✅"
            button.label = "Success"
            button.style = discord.ButtonStyle.success
            button.disabled = True
        else:
            button.emoji = "🔄"
            button.label = "Try again"
            button.style = discord.ButtonStyle.secondary

    @discord.ui.button(label="Play", style=discord.ButtonStyle.primary, emoji="🎵")
    async def play_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        result = await self.on_play(self.context, self.music)
        self.change(button, result)
        await interaction.followup.edit_message(self.message.id, view=self)

    @discord.ui.button(label="Save", style=discord.ButtonStyle.primary, emoji="⬇")
    async def save_button(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        result = True
        try:
            await self.context.channel.send(self.music.url)
        except:
            result = False
        self.change(button, result)
        await interaction.edit_original_response(view=self)
