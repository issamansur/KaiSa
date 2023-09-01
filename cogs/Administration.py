from discord import utils, Status, Activity, ActivityType, Member
from discord.ext.commands import Cog, command, Context

from .Settings import *
from .source.actions import *
from .source.answers import *

import datetime

import aiohttp


class Administration(Cog):
    def __init__(self, bot):
        self.client = bot

    @Cog.listener()
    async def on_member_join(self, member):
        await member.send(f"Добро пожаловать в клуб стримера EDEXADE, {member}!")
        role = utils.get(member.guild.roles, id=DEFAULT_ROLE_ID)
        await member.add_roles(role, reason="Вход на сервер")
        print("Роль успешно выдана!")

    @Cog.listener()
    async def on_message(self, message):
        if message.author == self.client.user:
            return

        text = message.content
        words = text.split()
        author = message.author
        channel = message.channel

        if f"<@{ADMIN_USER_ID}>" in text:
            await message.channel.send(
                f"<@{message.author.id}>, Владелец заблокировал функцию упоминания."
            )
            await message.delete()
            return

        if str(words[0]).lower() in actions:
            try:
                member = await self.client.fetch_user(words[1][2:-1])
                await channel.send(
                    f"{author.display_name} {formatting(words[0])} {member.display_name} {' '.join(words[2:])}"
                )
            except Exception as e:
                await channel.send(f"Something went wrong: {e}")
            return

        await self.client.process_commands(message)

    # ------------------------------------------------------------

    async def timeout_user(self, user_id: int, guild_id: int, until):
        headers = {"Authorization": f"Bot {self.client.http.token}"}
        url = f"https://discord.com/api/v9/guilds/{guild_id}/members/{user_id}"
        timeout = (
            datetime.datetime.utcnow() + datetime.timedelta(minutes=until)
        ).isoformat()
        json = {"communication_disabled_until": timeout}
        self.client.session = aiohttp.self.clientSession()
        async with self.client.session.patch(
            url, json=json, headers=headers
        ) as session:
            status = session.status
            await self.client.session.close()
            if status in range(200, 299):
                return True
            return False

    @command(pass_context=False)
    async def mute(self, ctx: Context, member: Member, until: int):
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("Атятя")
            return
        handshake = await self.timeout_user(
            user_id=member.id, guild_id=ctx.guild.id, until=until
        )
        if handshake:
            return await ctx.send(
                f"Successfully timed out user {member} for {until} minutes."
            )
        await ctx.send("Something went wrong")

    @command(pass_context=False)
    async def version(self, ctx: Context):
        await ctx.send("1.0.1")

    @command(pass_context=False)
    async def mute_micro(self, ctx: Context, member: Member):
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("Атятя")
            return
        try:
            await member.edit(mute=True)
            await ctx.send(f"Successfully mute micro of user {member}.")
        except Exception as e:
            await ctx.send(f"Something went wrong: {e}")

    @command(pass_context=False)
    async def unmute_micro(self, ctx: Context, member: Member):
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("Атятя")
            return
        try:
            await member.edit(mute=False)
            await ctx.send(f"Successfully unmute micro of user {member}.")
        except Exception as e:
            await ctx.send(f"Something went wrong: {e}")

    @command(pass_context=False)
    async def ban(self, ctx: Context, member: Member, *, reason: str = ""):
        if ctx.author.id != ADMIN_USER_ID:
            await ctx.send("Атятя")
            return
        try:
            await ctx.guild.ban(user=member, reason=reason)
            await ctx.send(f"Successfully ban user {member}.")
        except Exception as e:
            await ctx.send(f"Something went wrong: {e}")

    @command(pass_context=True, brief="This check a status of the bot", aliases=["bot"])
    async def b(self, ctx):
        await ctx.send(ANSWERS.GREETING)
