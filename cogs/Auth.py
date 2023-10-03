import io
import aiohttp

from discord import app_commands, Interaction, File
from discord.ext.commands import (
    has_permissions,
    guild_only,
    dm_only,
    Cog,
    Bot,
)

from vkpymusic import TokenReceiverAsync, Service

from cogs import Voice


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

    ########################
    ### 4 handlers and /auth
    # handler_1 (captcha image)
    async def _on_captcha_handler(self, interaction: Interaction, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                img = await resp.read()
                with io.BytesIO(img) as file:
                    await interaction.channel.send(file=File(file, "captcha.png"))

        await interaction.channel.send("Введите капчу:\n```!captcha [капча]```")

        msg = await self.bot.wait_for(
            "message",
            check=(
                lambda mes: mes.channel.id == interaction.channel.id
                and mes.content.split()[0] == "!captcha"
            ),
            timeout=60,
        )
        captcha_key: str = msg.content.split(" ")[-1]
        return captcha_key

    # handler_2 (2fa SMS OR VK code)
    async def _on_2fa_handler(self, interaction: Interaction) -> str:
        await interaction.channel.send("Введите код из СМС:\n```!code [код]```")

        msg = await self.bot.wait_for(
            "message",
            check=(
                lambda mes: mes.channel.id == interaction.channel.id
                and mes.content.split()[0] == "!code"
            ),
            timeout=120,
        )
        code: str = msg.content.split(" ")[-1]
        return code

    # handler_3 (invalid login or password)
    async def _on_invalid_client_handler(self, interaction: Interaction):
        await interaction.channel.send(
            "Неверный логин или пароль, попробуйте ещё раз..."
        )

    # handler_4 (unexpected error)
    async def _on_critical_error_handler(self, interaction: Interaction, obj: any):
        await interaction.channel.send(f"Критическая ошибка!\n```{obj}```")
        pleasure: str = "Пожалуйста, скопируйте текст ошибки и отправьте:\n"
        pleasure += "```/report [текст ошибки]```"
        await interaction.channel.send(pleasure)

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
            on_captcha=lambda url: self._on_captcha_handler(interaction, url),
            on_2fa=lambda: self._on_2fa_handler(interaction),
            on_invalid_client=lambda: self._on_invalid_client_handler(interaction),
            on_critical_error=lambda obj: self._on_critical_error_handler(
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
