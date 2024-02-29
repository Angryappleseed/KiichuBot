
#---------------------TRUSTED USER COMMANDS---------------------#

import json

import discord
from typing import Optional
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, database
from helpers.colors import colors
from helpers.emotes import emotes


class Trusted(commands.Cog, name="trusted"):
    def __init__(self, bot):
        self.bot = bot
        with open('config.json') as config_file:
            self.config = json.load(config_file)



#--------------------------------DM COMMAND--------------------------------#
    @commands.hybrid_command(
        name="dm",
        description="Algebra will dm the user.",
    )
    @app_commands.describe(user="The user you want to DM", message="The message that Algebra should DM")
    @checks.is_trusted()
    async def dm(self, context: Context, user: discord.User, message: str, attachment: Optional[discord.Attachment] = None) -> None:
        try:
            if isinstance(user, str):
                user_id = user.strip("<@!>")
                user = await self.bot.fetch_user(user_id)

            media_url = None
            if attachment:
                media_url = attachment.url

            await user.send(message)
            
            embed = discord.Embed(title=f"Message sent to {user.name}#{user.discriminator} {emotes['comfy']}", color=colors["blue"])
            if media_url:
                embed.add_field(name="Attachment:", value=media_url)
            
            await context.send(embed=embed)

            if media_url:
                await user.send(media_url)

        except discord.Forbidden:
            embed = discord.Embed(title=f"I am unable to DM that user. {emotes['cry']}", color=colors["red"])
            await context.send(embed=embed)
        except discord.HTTPException:
            embed = discord.Embed(title=f"Failed to send message. {emotes['cry']}", color=colors["red"])
            await context.send(embed=embed)



#----------------------DM LISTENER-----------------------------#
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        if message.author == self.bot.user or message.author.bot:
            return

        # If message was sent to bot's DMs, send it to Algebra's Server
        if isinstance(message.channel, discord.DMChannel):
            dm_channel_id = int(self.config["dm_channel_id"])
            channel = self.bot.get_channel(dm_channel_id)
            if channel is not None:
                embed = discord.Embed(description=f"{message.author.name}: {message.content}", color=colors["blue"])
                media_urls = []
                if message.attachments:
                    for attachment in message.attachments:
                        media_urls.append(attachment.url)

                await channel.send(embed=embed)
                for url in media_urls:
                    await channel.send(url)



#--------------------------------ECHO COMMAND--------------------------------#
    @commands.hybrid_command(
        name="echo",
        description="Algebra will repeat after you",
    )
    @app_commands.describe(
        message="The message that should be repeated by Algebra"
        )
    @checks.is_trusted()
    async def echo(self, context: Context, *, message: str) -> None:
        await context.send(message)


#------------------------------SEND EMBED COMMAND--------------------------------#
    @commands.hybrid_command(
        name="embed",
        description="Algebra will repeat after you in an embed.",
    )
    @app_commands.describe(
        message="The message that should be repeated by Algebra"
        )
    @checks.is_trusted()
    async def embed(self, context: Context, *, message: str) -> None:
        embed = discord.Embed(description=message, color=colors["blue"])
        await context.send(embed=embed)



async def setup(bot):
    await bot.add_cog(Trusted(bot))
