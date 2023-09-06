import io
import aiohttp

from discord import File
from discord.ext.commands import (
    Bot,
    Context,
    Cog,
    Context,
    command,
    has_permissions,
)

from vkpymusic import TokenReceiverAsync, Service, Song

from .Voice import Voice

from .source.answers import *


FFMPEG_OPTIONS = {
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
    "options": "-vn",
}


async def is_dm(ctx: Context):
    return ctx.guild == None


# ---------------------------------------------
class Auth(Cog):
    ### constructor
    def __init__(self, bot):
        self.bot: Bot = bot

    ### !register
    @has_permissions(administrator=True)
    @command(
        pass_context=True,
        brief="Auth VK for audio service",
        aliases=["reg"],
    )
    async def register(self, ctx: Context):
        if await is_dm(ctx):
            await ctx.send("Только в группе!")
            return

        guild_id: int = ctx.message.guild.id
        voice: Voice = self.client.get_cog("Voice")

        if await voice.is_registered(ctx.guild.id):
            await ctx.send("Уже зарегистрированы!")
            return

        service: Service = Service.parse_config(rf"tokens\{guild_id}.ini")
        if service == None:
            await ctx.message.author.send(
                "Приветики, для авторизации используется ВК.\n"
                + "Токен не найден, необходима авторизация. Введите:\n"
                + f"```!auth {guild_id} <Логин/Телефон> <Пароль>```"
            )
        else:
            await ctx.send(f"```Сервис для сервера {ctx.guild.name} активен!```")
            voice: Voice = self.client.get_cog("Voice")
            await voice.set_service(guild_id, service)

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
