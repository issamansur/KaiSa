from discord import Client, app_commands, Interaction, User, Embed, Color
from discord.ext.commands import Bot, Cog, cooldown
from components import embed

from Settings import ADMIN_USER_ID


async def setup(client):
    await client.add_cog(Administration(client))


class Administration(Cog):
    def __init__(self, client):
        self.client: Client = client
        

    @app_commands.checks.cooldown(1, 30)
    @app_commands.command(name="ping", description="Checks bot")
    async def _ping(self, interaction: Interaction):
        await interaction.response.send_message("Pong!")


    @app_commands.command(name="help", description="Shows availible commands")
    async def _help(self, interaction: Interaction):
        await interaction.response.send_message(embed=embed)


    @app_commands.command(name="report", description="Send report to bot's owner")
    @app_commands.describe(info="Additional info about problem")
    async def _report(self, interaction: Interaction, info: str):
        owner: User = await self.client.fetch_user(ADMIN_USER_ID)
        embed = Embed(
            title="Report about Kai'Sa",
            url=None,
            description=info,
            color=Color.red(),
        )
        embed.set_author(
            name=interaction.user.display_name,
            url=None,
            icon_url=interaction.user.avatar,
        )
        embed.add_field(name="User", value=interaction.user.mention, inline=True)
        if interaction.guild is not None:
            embed.add_field(name="Guild", value=interaction.guild.name, inline=True)
            embed.add_field(name="Guild Id", value=interaction.guild.id, inline=True)
        await owner.send(embed=embed)

        await interaction.response.send_message(
            "Жалоба успешно отправлена создателю бота!", ephemeral=True
        )