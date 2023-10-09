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

from vkpymusic import Service

from source import actions, formatting
from components import embed
from Settings import TOKEN, ADMIN_USER_ID

from cogs import Administration
from cogs import Voice
from cogs import Auth


initial_extensions = ['cogs.administration', 'cogs.auth', 'cogs.voice']

async def load_extensions():
    for extension in initial_extensions:
        await client.load_extension(extension)

class SlashBot(commands.Bot):
    def __init__(self, intents: Intents):
        super().__init__(command_prefix=".", intents=intents)
        # self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # set cogs
        '''
        await self.add_cog(Administration(client))
        await self.add_cog(Voice(client))
        await self.add_cog(Auth(client))
        '''
        await load_extensions()

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


client = SlashBot(intents=Intents.default())

# -------------------------------------------------------
activities = [
    Game(
        name="League of Legends",
    ),
    Activity(
        type=ActivityType.watching,
        name="Cyberpunk edge runners",
    ),
    # ...
]


@client.event
async def on_ready():
    print(f"Has logged in as {client.user}")

    # set status
    await client.change_presence(
        status=Status.online,
        activity=activities[1],
    )

    # set services
    voice: Voice = client.get_cog("Voice")
    for guild in client.guilds:
        service: Service = Service.parse_config(rf"tokens/{guild.id}.ini")
        if service is not None:
            await voice.set_service(guild.id, service)
            print(f"\033[92mGuild {guild.name} connected!\033[0m")


async def on_tree_error(interaction: Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.CommandOnCooldown):
        await interaction.channel.send(
            f"Command is currently on cooldown! Try again in **{error.retry_after:.2f}** seconds!"
        )

    elif isinstance(error, app_commands.CommandNotFound):
        await interaction.channel.send(error)

    else:
        await interaction.channel.send(error)
    
    if not interaction.response.is_done():
        await interaction.response.send_message(content="Something went wrong!", ephemeral=True)


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
    
    if len(words) != 0 and words[0].lower() in actions:
        try:
            member = await client.fetch_user(words[1][2:-1])
            res = f"{author.display_name} {formatting(words[0])} {member.display_name} {' '.join(words[2:])}"
            await channel.send(content=res)

        except Exception as exception:
            await channel.send(f"Something went wrong: {exception}")
    
    await client.process_commands(message)

@client.tree.command(name="reload", description="Reloads bot")
async def _reload(interaction: Interaction):
    for extension in initial_extensions:
        await client.reload_extension(extension)
    await interaction.response.send_message("Reloaded!")

# --------------------------------------------------------------------------


client.run(token=TOKEN)
