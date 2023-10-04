import io
import aiohttp

from discord import Interaction, File
from discord.ext.commands import Bot

# handler_1 (captcha image)
async def on_captcha_handler(bot: Bot, interaction: Interaction, url: str) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            img = await resp.read()
            with io.BytesIO(img) as file:
                await interaction.channel.send(file=File(file, "captcha.png"))

    await interaction.channel.send("Введите капчу:\n```!captcha [капча]```")

    msg = await bot.wait_for(
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
async def on_2fa_handler(bot: Bot, interaction: Interaction) -> str:
    await interaction.channel.send("Введите код из СМС:\n```!code [код]```")

    msg = await bot.wait_for(
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
async def on_invalid_client_handler(interaction: Interaction):
    await interaction.channel.send(
        "Неверный логин или пароль, попробуйте ещё раз..."
    )

# handler_4 (unexpected error)
async def on_critical_error_handler(interaction: Interaction, obj: any):
    await interaction.channel.send(f"Критическая ошибка!\n```{obj}```")
    pleasure: str = "Пожалуйста, скопируйте текст ошибки и отправьте:\n"
    pleasure += "```/report [текст ошибки]```"
    await interaction.channel.send(pleasure)