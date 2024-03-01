
#---------------------MODMAIL-------------------------#

import json

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

from helpers import checks

class Modmail(commands.Cog, name="modmail"):
    def __init__(self, bot):
        self.bot = bot
        self.modmail_category_name = "Modmail"
        self.modmail_logs_channel_name = "modmail-logs"


#----------------------SETUP-------------------------------#

    @commands.hybrid_command(name="setup", description="Sets up the modmail system.")
    @checks.is_owner()
    async def setup_modmail(self, context: Context) -> None:
        guild = context.guild

        # check if Modmail category exists
        modmail_category = discord.utils.get(guild.categories, name=self.modmail_category_name)
        if not modmail_category:
            # create the Modmail category
            overwrites = {
                # make it private to @everyone
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True)
            }
            modmail_category = await guild.create_category(self.modmail_category_name, overwrites=overwrites)
            await context.send(f"{modmail_category.name}.")

        # check if the modmail-logs channel already exists inside Modmail category
        modmail_logs_channel = discord.utils.get(guild.text_channels, name=self.modmail_logs_channel_name, category=modmail_category)
        if not modmail_logs_channel:
            # Create the modmail-logs channel
            modmail_logs_channel = await guild.create_text_channel(self.modmail_logs_channel_name, category=modmail_category)
            await context.send(f"Created the channel {modmail_logs_channel.mention}.")

        await context.send("Modmail system setup complete.")





    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # ignore bot's messages
        if message.author.bot:
            return

        # if bot is DMd
        if isinstance(message.channel, discord.DMChannel):
            with open('config.json', 'r') as config_file:
                config = json.load(config_file)
            bot_guild_id = int(config["bot_guild_id"])
            guild = self.bot.get_guild(bot_guild_id) 
            modmail_category = discord.utils.get(guild.categories, name=self.modmail_category_name)
            
            if not modmail_category:
                # Handle the case where the Modmail category doesn't exist
                return
            
            # Check for an existing channel for the user
            user_channel_name = f"{message.author.name}-{message.author.discriminator}"
            user_channel = discord.utils.get(guild.text_channels, name=user_channel_name, category=modmail_category)
            
            # If the channel does not exist, create it
            if not user_channel:
                user_channel = await guild.create_text_channel(user_channel_name, category=modmail_category)
                

            # Construct the embed to forward the DM
            embed = discord.Embed(title=f"Modmail from {message.author}", description=message.content, color=discord.Color.blue())
            await user_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Modmail(bot))