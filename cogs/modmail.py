
#---------------------MODMAIL-------------------------#

import json
import asyncio

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

from datetime import datetime

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes

class Modmail(commands.Cog, name="modmail"):
    def __init__(self, bot):
        self.bot = bot
        self.modmail_category_name = "▬▬▬▬ ModMail ▬▬▬▬"
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
            guild.me: discord.PermissionOverwrite(read_messages=True)
        }
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



#-------------------ON MESSAGE-------------------------#

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # ignore bot's messages and messages with prefix
        if message.author.bot:
            return

        # if bot is DMd
        if isinstance(message.channel, discord.DMChannel):
            # Check for existing modmail channel or user's intention to create one is handled later
            confirmation_embed = discord.Embed(
                title="Are you sure you want to send this message to Kiichan's Fox Den?",
                description=message.content,
                color=colors["gold"],
                timestamp=datetime.now()
            )
            confirmation_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel.")
            confirmation_message = await message.author.send(embed=confirmation_embed)
            # Add reactions for the user to confirm or cancel
            await confirmation_message.add_reaction("✅")
            await confirmation_message.add_reaction("❌")

            def check(reaction, user):
                return user == message.author and str(reaction.emoji) in ["✅", "❌"] and reaction.message.id == confirmation_message.id

            try:
                reaction, user = await self.bot.wait_for("reaction_add", timeout=60.0, check=check)
            except asyncio.TimeoutError:
                timedout_embed = discord.Embed(
                        title="Modmail Request Timed Out",
                        description="Your modmail request has been successfully cancelled.",
                        color=colors["red"]
                    )
                await confirmation_message.edit(content="", embed=timedout_embed)
                
            else:
                # if user reacts yes
                if str(reaction.emoji) == "✅":
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
                    
                    
                    # If user does not have modmail channel, create it
                    if not user_channel:
                        channel_topic = f"Modmail User ID: {message.author.id}"
                        user_channel = await guild.create_text_channel(user_channel_name, category=modmail_category, topic=channel_topic)
                        
                        # Fetch member object from guild to list roles
                        member = guild.get_member(message.author.id)
                        if member:
                            roles = [role.mention for role in member.roles if role != guild.default_role]  # Exclude @everyone role
                            
                            # Creating an embed with user information
                            embed = discord.Embed(title="New Modmail Ticket",
                                                color=colors["blue"],
                                                timestamp=datetime.now())
                            embed.add_field(name="User", value=f"{message.author.mention}\n{message.author.id}", inline=True)
                            embed.add_field(name="Roles", value=", ".join(roles) if roles else "No roles", inline=True)
                            embed.set_footer(text=f"User ID: {message.author.id}")
                            await user_channel.send(embed=embed)
                        

                    # Received DM embed
                    embed = discord.Embed(title="Message Received:",
                                        description=message.content,
                                        color=colors["green"],
                                        timestamp=datetime.now())
                    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    await user_channel.send(embed=embed)

                    # Send confirmation embed to the user in DM
                    confirmation_embed = discord.Embed(
                        title="Message Sent:",
                        description=f"{message.content}",
                        color=colors["green"],
                        timestamp=datetime.now()
                    )
                    confirmation_embed.set_footer(text=f"User ID: {message.author.id}")
                    await message.author.send(embed=confirmation_embed)

                # if user reacts no
                elif str(reaction.emoji) == "❌":
                    cancelled_embed = discord.Embed(
                        title="Modmail Request Cancelled",
                        description="Your modmail request has been successfully cancelled.",
                        color=colors["red"]
                    )
                    await confirmation_message.edit(content="", embed=cancelled_embed)

                    
        # if message is sent in modmail channel
        else:
            guild = message.guild
            modmail_category = discord.utils.get(guild.categories, name=self.modmail_category_name)
            if message.channel.category_id == modmail_category.id:
                # Call get_custom_prefix asynchronously
                current_prefixes = await self.bot.get_custom_prefix(message)
                
                # Since we can't use 'await' inside 'any', we loop through prefixes manually
                message_starts_with_prefix = False
                for prefix in current_prefixes:
                    if message.content.startswith(prefix):
                        message_starts_with_prefix = True
                        break

                if message_starts_with_prefix:
                    # If it does, simply return and do not process the message further
                    return
                
                # Extract the user ID from the channel's topic and continue as before
                user_id_str = message.channel.topic.split("Modmail User ID: ")[-1] if message.channel.topic else None
                try:
                    user_id = int(user_id_str)
                    user_id = int(user_id_str)
                    user = await self.bot.fetch_user(user_id)
                    # Send the DM to the user
                    embed = discord.Embed(
                        title="Message Received:",
                        description=message.content,
                        color=colors["red"],
                        timestamp=datetime.now()
                    )
                    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    await user.send(embed=embed)
                    await message.delete()

                    # Log that the message was sent
                    log_embed = discord.Embed(
                        title="Message Sent:",
                        description=f"{message.content}",
                        color=colors["red"],
                        timestamp=datetime.now()
                    )
                    log_embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                    log_embed.set_footer(text=f"User ID: {message.author.id}")
                    await message.channel.send(embed=log_embed)
                except (ValueError, TypeError):
                    # Handle cases where the topic does not contain a valid user ID or parsing issues
                    pass
                except discord.NotFound:
                    # Handle the case where the user cannot be found
                    pass


async def setup(bot):

    await bot.add_cog(Modmail(bot))