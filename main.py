from discord import (
    app_commands,
    Client,
    Intents,
    Interaction,
    Object,
    Message,
    Embed,
    Status,
    ActivityType,
    Activity,
    Game,
    Streaming,
)
from discord.ext import commands

from source import actions, formatting
from Settings import TOKEN, ADMIN_USER_ID

from cogs import Administration
from cogs import Voice
from cogs import Auth

from vkpymusic import Service


class SlashBot(commands.Bot):
    def __init__(self, *, command_prefix: str, intents: Intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def setup_hook(self):
        # set cogs
        await self.add_cog(Administration(client))
        await self.add_cog(Voice(client))
        await self.add_cog(Auth(client))

        # sync all
        await self.tree.sync(guild=None)
        # sync main
        """
        SYNC_GUILD = Object(id=DEFAULT_GUILD_ID)
        self.tree.copy_global_to(guild=SYNC_GUILD)
        await self.tree.sync(guild=SYNC_GUILD)
        """

        # on tree error
        self.tree.on_error = on_tree_error


client = SlashBot(command_prefix="/", intents=Intents.all())

# -------------------------------------------------------
activities = [
    Game(
        name="League of Legends",
    ),
    # ...
]


@client.event
async def on_ready():
    print(f"Has logged in as {client.user}")

    # set status
    await client.change_presence(
        status=Status.online,
        activity=activities[0],
    )

    # set services
    voice: Voice = client.get_cog("Voice")
    for guild in client.guilds:
        service: Service = Service.parse_config(rf"tokens/{guild.id}.ini")
        if service is not None:
            await voice.set_service(guild.id, service)
            print(f"\033[92mGuild {guild.name} connected!\033[0m")


@app_commands.checks.cooldown(1, 30)
@client.tree.command(name="ping", description="Checks bot")
async def _ping(interaction: Interaction):
    await interaction.response.send_message("Pong!")


@client.tree.command(name="help", description="Shows availible commands")
async def _ping(interaction: Interaction):
    embed = Embed
'''
* /ping: Проверить доступность бота. 
* /help: Получить справку о доступных командах. 
* /report: Отправить отчет о проблеме или баге. 

## Управление аккаунтом пользователя

* /register: Зарегистрировать аккаунт пользователя. 
* /unregister: Удалить аккаунт пользователя. 
* /auth \[id гильдии\] \[логин/телефон\] \[пароль\]: Аутентифицироваться. 

## Поиск и воспроизведение музыки

* /search \[название/автор песни\]: Найти и воспроизвести песню. 
* /search-album \[название плейлиста (исполнителя)\]: Найти альбом или исполнителя. ✅
* /search-playlist \[название плейлиста (пользователя)\]: Найти плейлист пользователя. ✅

## Управление воспроизведением музыки

* /list: Показать список воспроизведения. 
* /repeat \[OFF | ONE | ALL\]: Установить режим повтора. 
* /skip: Пропустить текущую композицию. 
* /quit: Завершить воспроизведение музыки. 
'''
#    await interaction.response.send_message("Pong!")


async def on_tree_error(interaction: Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        return await interaction.response.send_message(
            f"Command is currently on cooldown! Try again in **{error.retry_after:.2f}** seconds!"
        )

    elif isinstance(error, app_commands.CommandNotFound):
        print(error)

    else:
        raise error


@client.event
async def on_message(message: Message):
    if message.author == client.user:
        return

    text = message.content
    words = text.split()
    author = message.author
    channel = message.channel

    if f"<@{ADMIN_USER_ID}>" in text:
        await channel.send(f"<@{author.id}>, Владелец заблокировал функцию упоминания.")
        await message.delete()
        return

    if str(words[0]).lower() in actions:
        try:
            member = await client.fetch_user(words[1][2:-1])
            res = f"{author.display_name} {formatting(words[0])} {member.display_name} {' '.join(words[2:])}"
            await channel.send(content=res)
        except Exception as exception:
            await channel.send(f"Something went wrong: {exception}")
        return

    await client.process_commands(message)


# --------------------------------------------------------------------------


client.run(token=TOKEN)
