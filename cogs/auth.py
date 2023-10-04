from discord import app_commands, Interaction, File
from discord.ext.commands import (
    has_permissions,
    guild_only,
    dm_only,
    Cog,
    Bot,
)

from vkpymusic import TokenReceiverAsync, Service

from .voice import Voice

from utils import (
    on_captcha_handler,
    on_2fa_handler,
    on_invalid_client_handler,
    on_critical_error_handler,
)

FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def is_dm(interaction: Interaction):
    return interaction.guild is None


# ---------------------------------------------
async def setup(bot):
    await bot.add_cog(Auth(bot))


class Auth(Cog):
    ###############
    ### constructor
    def __init__(self, bot):
        self.bot: Bot = bot

    #############
    ### /register
    @guild_only()
    @has_permissions(administrator=True)
    @app_commands.command(
        name="register",
        description="Register service for audio",
    )
    async def _register(self, interaction: Interaction):
        if await is_dm(interaction):
            await interaction.response.send_message("Только в группе!")
            return

        guild_id: int = interaction.guild.id
        voice: Voice = self.bot.get_cog("Voice")

        if await voice.is_registered(guild_id):
            await interaction.response.send_message(
                content="Уже зарегистрированы!",
                ephemeral=True
            )
            return

        service: Service = Service.parse_config(rf"tokens/{guild_id}.ini")
        if service is None:
            com_str = f"```/auth guild_id:{guild_id} login: password:```"
            await interaction.user.send(
                "Приветики, для авторизации используется ВК.\n"
                + "Токен не найден, необходима авторизация. Введите:\n"
                + com_str
            )
        else:
            await interaction.user.send(
                f"```> Сервис для сервера {interaction.guild.name} активен!```"
            )
            await voice.set_service(guild_id, service)
        await interaction.response.send_message(
            content="Проверь сообщения в приватике!", ephemeral=True
        )

    ###############
    ### /unregister
    @guild_only()
    @has_permissions(administrator=True)
    @app_commands.command(
        name="unregister",
        description="Unregister service for audio",
    )
    async def _unregister(self, interaction: Interaction):
        if await is_dm(interaction):
            await interaction.response.send_message("Только в группе!")
            return

        guild_id: int = interaction.guild.id
        voice: Voice = self.bot.get_cog("Voice")

        if not await voice.is_registered(guild_id):
            await interaction.response.send_message(
                content="Вы не зарегистрированы!", ephemeral=True
            )
            return

        Service.del_config(rf"tokens/{guild_id}.ini")
        await voice.set_service(guild_id, None)
        await interaction.response.send_message(
            content="Сервис успешно отвязан!", ephemeral=True
        )
    

    #######
    # /auth
    @dm_only()
    @app_commands.command(
        name="auth",
        description="Auth in VK. Need for audio service",
    )
    @app_commands.describe(guild_id="ID of the registering guild")
    @app_commands.describe(login="VK username or number")
    @app_commands.describe(password="VK password")
    async def _auth(
        self, interaction: Interaction, guild_id: str, login: str, password: str
    ):
        # check on dm
        if not await is_dm(interaction):
            await interaction.response.send_message("Только в приватике!")
            return

        # check on registered
        voice: Voice = self.bot.get_cog("Voice")
        if await voice.is_registered(guild_id):
            await interaction.response.send_message("Уже зарегистрированы!")
            return

        try:
            guild_id = int(guild_id)
        except ValueError:
            await interaction.response.send_message("Ошибка параметра!")
            return
        # main auth
        await interaction.response.send_message("Авторизация...")

        token_receiver: TokenReceiverAsync = TokenReceiverAsync(login, password)

        if await token_receiver.auth(
            on_captcha=lambda url: on_captcha_handler(self.bot, interaction, url),
            on_2fa=lambda: on_2fa_handler(interaction),
            on_invalid_client=lambda: on_invalid_client_handler(interaction),
            on_critical_error=lambda obj: on_critical_error_handler(
                interaction, obj
            ),
        ):
            token = token_receiver.get_token()
            await interaction.channel.send(f"Успешно! Ваш токен:\n```{token}```")
            token_receiver.save_to_config(rf"tokens/{guild_id}.ini")
            await interaction.channel.send(
                "Токен успешно сохранён для дальнейших сессий\n"
                + "Вернитесь на сервер и пропишите ещё раз:\n"
                + "```/register```"
            )
