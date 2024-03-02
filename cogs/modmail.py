
#---------------------MODMAIL-------------------------#

import json

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

from helpers import checks

from helpers.colors import colors
from helpers.emotes import emotes

class Modmail(commands.Cog, name="modmail"):
    def __init__(self, bot):
        self.bot = bot
        self.modmail_category_name = "Modmail"
        self.modmail_logs_channel_name = "modmail-logs"


#----------------------SETUP-------------------------------#

    @commands.hybrid_command(name="setupmodmail", description="Sets up the modmail system.")
    @checks.is_owner()
    async def setup_modmail(self, context: Context) -> None:
        guild = context.guild

        # Load mod roles from config.json
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        mod_role_ids = config["modRoles"]


        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            guild.me: discord.PermissionOverwrite(read_messages=True)  # Bot can access
        }
        # Add mod roles to overwrites with read permission
        for role_id in mod_role_ids:
            role = guild.get_role(role_id)
            if role:
                overwrites[role] = discord.PermissionOverwrite(read_messages=True)


        # Check if Modmail category exists
        modmail_category = discord.utils.get(guild.categories, name=self.modmail_category_name)
        if not modmail_category:
            # Create the Modmail category with overwrites
            modmail_category = await guild.create_category(self.modmail_category_name, overwrites=overwrites)
            await context.send(f"Created category {modmail_category.name}.")

        # Check if the modmail-logs channel already exists inside Modmail category
        modmail_logs_channel = discord.utils.get(guild.text_channels, name=self.modmail_logs_channel_name, category=modmail_category)
        if not modmail_logs_channel:
            # Create the modmail-logs channel
            modmail_logs_channel = await guild.create_text_channel(self.modmail_logs_channel_name, category=modmail_category)
            await context.send(f"Created the channel {modmail_logs_channel.mention}.")

        embed = discord.Embed(
            description=f"Modmail system setup complete.",
            color=colors["blue"]
        )
        await context.send(embed=embed)





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
            
            # check if user has modmail channel
            user_channel_name = f"{message.author.name}-{message.author.discriminator}"
            user_channel = discord.utils.get(guild.text_channels, name=user_channel_name, category=modmail_category)
            
            # if user does not have modmail channel, create it
            if not user_channel:
                user_channel = await guild.create_text_channel(user_channel_name, category=modmail_category)
                

            # Received DM embed
            embed = discord.Embed(title=f"Modmail from {message.author}", description=message.content, color=colors["blue"])
            await user_channel.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Modmail(bot))