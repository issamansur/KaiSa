import io
import aiohttp

from discord import app_commands, Interaction, User, File
from discord.ext.commands import (
    command,
    has_permissions,
    Cog,
    Bot,
    Context,
)

from vkpymusic import TokenReceiverAsync, Service, Song

from .Voice import Voice

from .source.answers import *


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def is_dm(ctx: Interaction):
    return ctx.guild == None


# ---------------------------------------------
class Auth(Cog):
    ### constructor
    def __init__(self, bot):
        self.bot: Bot = bot

    ### !register
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
                content="Уже зарегистрированы!", ephemeral=True
            )
            return

        service: Service = Service.parse_config(rf"tokens\{guild_id}.ini")
        if service == None:
            await interaction.user.send(
                "Приветики, для авторизации используется ВК.\n"
                + "Токен не найден, необходима авторизация. Введите:\n"
                + f"```!auth {guild_id} <Логин/Телефон> <Пароль>```"
            )
        else:
            await interaction.user.send(
                f"```> Сервис для сервера {interaction.guild.name} активен!```"
            )
            await voice.set_service(guild_id, service)
        await interaction.response.send_message(
            content="Проверь сообщения в приватике!", ephemeral=True
        )

    ### 4 handlers and !auth
    # handler_1 (captcha image)
    async def on_captcha_handler(self, ctx, url: str) -> str:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as resp:
                img = await resp.read()
                with io.BytesIO(img) as file:
                    await ctx.channel.send(file=File(file, "captcha.png"))

        await ctx.send("Введите капчу:\n" + "```!captcha <капча>```")

        msg = await self.client.wait_for(
            "message",
            check=(
                lambda mes: mes.channel.id == ctx.channel.id
                and mes.content.split()[0] == "!captcha"
            ),
            timeout=60,
        )
        captcha_key: str = msg.content.split(" ")[-1]
        return captcha_key

    # handler_2 (2fa SMS OR VK code)
    async def on_2fa_handler(self, ctx) -> str:
        await ctx.send("Введите код из СМС:\n" + "```!code <код>```")

        msg = await self.client.wait_for(
            "message",
            check=(
                lambda mes: mes.channel.id == ctx.channel.id
                and mes.content.split()[0] == "!code"
            ),
            timeout=60,
        )
        code: str = msg.content.split(" ")[-1]
        return code

    # handler_3 (invalid login or password)
    async def on_invalid_client_handler(self, ctx):
        await ctx.send("Неверный логин или пароль, попробуйте ещё раз...")

    # handler_4 (unexpected error)
    async def on_critical_error_handler(self, ctx, obj):
        await ctx.send("Критическая ошибка!\n" + f"```{obj}```")

    # !auth
    @command()
    async def auth(self, ctx: Context, guild_id: int, login: str, password: str):
        if not await is_dm(ctx):
            await ctx.send("Только в лс!")
            return

        voice: Voice = self.client.get_cog("Voice")
        if await voice.is_registered(guild_id):
            await ctx.send("Уже зарегистрированы!")
            return

        tr: TokenReceiverAsync = TokenReceiverAsync(login, password)

        if await tr.auth(
            on_captcha=lambda url: self.on_captcha_handler(ctx, url),
            on_2fa=lambda: self.on_2fa_handler(ctx),
            on_invalid_client=lambda: self.on_invalid_client_handler(ctx),
            on_critical_error=lambda obj: self.on_critical_error_handler(ctx, obj),
        ):
            token = tr.get_token()
            await ctx.send("Успешно! Ваш токен:\n" + f"```{token}```")
            tr.save_to_config(rf"tokens\{guild_id}.ini")
            await ctx.send(
                f"Токен успешно сохранён для дальнейших сессий\n"
                + "Вернитесь на сервер и пропишите ещё раз:\n"
                + "```!register```"
            )
