import discord
from discord.ext import commands

TOKEN = "your_token_here"

intents = discord.Intents.default()
intents.typing = False
intents.presences = False

bot = commands.Bot(command_prefix=".", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Cyberpunk edge runners"))

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if f"<@{bot.user.id}>" in message.content:
        await message.channel.send(f"{message.author.mention}, Mentions are blocked by the owner.")
        await message.delete()
        return

    await bot.process_commands(message)

@bot.command(name="reload", description="Reloads the bot")
async def reload_extension(ctx):
    extensions = ['cogs.administration', 'cogs.auth', 'cogs.voice']
    for extension in extensions:
        try:
            bot.reload_extension(extension)
        except commands.ExtensionNotLoaded:
            bot.load_extension(extension)
    await ctx.send("Reloaded!")

if __name__ == "__main__":
    for extension in ['cogs.administration', 'cogs.auth', 'cogs.voice']:
        bot.load_extension(extension)
    bot.run(TOKEN)
