
#---------------------MODMAIL-------------------------#

import json
import asyncio
import io

import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

from datetime import datetime

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes
from helpers.database import(
    add_new_ticket,
    get_ticket_number
    )


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


        # check if Modmail category exists
        modmail_category = discord.utils.get(guild.categories, name=self.modmail_category_name)
        if not modmail_category:
            # create the Modmail category with overwrites
            modmail_category = await guild.create_category(self.modmail_category_name, overwrites=overwrites)
            await context.send(f"Created category {modmail_category.name}.")

        # check if the modmail-logs channel already exists
        modmail_logs_channel = discord.utils.get(guild.text_channels, name=self.modmail_logs_channel_name, category=modmail_category)
        if not modmail_logs_channel:
            # create the modmail-logs channel
            modmail_logs_channel = await guild.create_text_channel(self.modmail_logs_channel_name, category=modmail_category)
            await context.send(f"Created the channel {modmail_logs_channel.mention}.")

        embed = discord.Embed(
            description=f"Modmail system setup complete.",
            color=colors["blue"]
        )
        await context.send(embed=embed)



#--------------------------CLOSE TICKET------------------------------#

    @commands.hybrid_command(name="close", description="Closes the modmail ticket")
    @checks.is_moderator()
    async def close(self, ctx, *, reason="not specified."):
        # command can only be used in modmail channels
        modmail_category = discord.utils.get(ctx.guild.categories, name=self.modmail_category_name)
        modmail_logs_channel = discord.utils.get(ctx.guild.text_channels, name=self.modmail_logs_channel_name)
        if ctx.channel.category_id != modmail_category.id:
            embed = discord.Embed(description="This command can only be used in modmail channels.",
                                color=colors["red"],)
            await ctx.send(embed=embed)
            return
        
        # Retrieve the ticket number from the database
        ticket_number = await get_ticket_number(str(ctx.channel.id))
        if ticket_number is None:
            await ctx.send(embed=discord.Embed(description="Could not find the modmail ticket in the database.", color=colors["red"]))
            return

        
        # extract the user ID from the channel's topic
        user_id_str = ctx.channel.topic.split("Modmail User ID: ")[-1] if ctx.channel.topic else None
        try:
            user_id = int(user_id_str)
            user = await self.bot.fetch_user(user_id)
            
            # Inform the user that their modmail ticket has been closed
            dm_embed = discord.Embed(
                title=f"Modmail Ticket #{ticket_number} Closed",
                description=f"Your modmail ticket has been closed.\nReason: {reason}",
                color=colors["red"],
                timestamp=datetime.now()
            )
            dm_embed.set_author(name=ctx.author.name, icon_url=ctx.author.avatar.url)
            dm_embed.set_footer(text=f"User ID: {ctx.author.id}")
            await user.send(embed=dm_embed)
            
            # Delete the modmail channel
            await ctx.channel.delete(reason=f"Modmail closed. Reason: {reason}")

            if modmail_logs_channel:
                log_embed = discord.Embed(
                    title=f"Modmail Ticket #{ticket_number} Closed",
                    description=f"Ticket for {user.mention} | `{user.id}` was closed by {ctx.author.name}.\nReason: {reason}",
                    color=colors["red"],
                    timestamp=datetime.now()
                )
                log_embed.set_author(name=f"{ctx.author.name}", icon_url=ctx.author.avatar.url)
                log_embed.set_footer(text=f"User ID: {user_id}")
                await modmail_logs_channel.send(embed=log_embed)
            else:
                # Optionally handle the case where the logs channel wasn't found; this is up to your discretion.
                pass
            
        except (ValueError, TypeError):
            await ctx.send(embed=discord.Embed(description="Could not process the user ID from this channel's topic. The channel may not be a valid modmail ticket.",
                                           color=colors["red"]))
        except discord.NotFound:
            await ctx.send(embed=discord.Embed(description="The user associated with this modmail ticket could not be found.",
                                           color=colors["red"]))




#-------------------ON MESSAGE-------------------------#

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        # ignore bot's messages
        if message.author.bot:
            return

        # WHEN BOT IS DM'd
        if isinstance(message.channel, discord.DMChannel):
            attachment_urls = [attachment.url for attachment in message.attachments]
            message_content_with_attachments = f"{message.content}\n" + "\n".join(attachment_urls)
            # confirm if user wishes to send message
            confirmation_embed = discord.Embed(
                title="Are you sure you want to send this message to Kiichan's Fox Den?",
                description=message_content_with_attachments,
                color=colors["gold"],
                timestamp=datetime.now()
            )
            confirmation_embed.set_footer(text="React with ✅ to confirm or ❌ to cancel.")
            confirmation_message = await message.author.send(embed=confirmation_embed)
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
                        
                        member = guild.get_member(message.author.id)
                        ticket_number = await add_new_ticket(str(user_channel.id), str(message.author.id))

                        if member:
                            roles = [role.mention for role in member.roles if role != guild.default_role] 
                            
                            # create an embed with user's information
                            embed = discord.Embed(title=f"Modmail Ticket #{ticket_number} Opened",
                                                color=colors["blue"],
                                                timestamp=datetime.now())
                            embed.add_field(name="User", value=f"{message.author.mention}\n{message.author.id}", inline=True)
                            embed.add_field(name="Roles", value=", ".join(roles) if roles else "No roles", inline=True)
                            embed.set_footer(text=f"User ID: {message.author.id}")
                            await user_channel.send(embed=embed)
                        
                        modmail_logs_channel = discord.utils.get(guild.text_channels, name=self.modmail_logs_channel_name)
                        # log it in modmail-logs
                        if modmail_logs_channel:
                            log_embed = discord.Embed(title=f"Modmail Ticket #{ticket_number} Opened",
                                                    color=colors["green"],
                                                    timestamp=datetime.now())
                            log_embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                            log_embed.set_footer(text=f"User ID: {message.author.id}")
                            await modmail_logs_channel.send(embed=log_embed)
                        

                    # Send user's message to channel
                    embed = discord.Embed(title="Message Received:",
                                        description=message_content_with_attachments,
                                        color=colors["green"],
                                        timestamp=datetime.now())
                    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    await user_channel.send(embed=embed)

                    # Send confirmation embed to the user in DM
                    confirmation_embed = discord.Embed(
                        title="Message Sent:",
                        description=f"{message_content_with_attachments}",
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
            attachment_urls = [attachment.url for attachment in message.attachments]
            message_content_with_attachments = f"{message.content}\n" + "\n".join(attachment_urls)
            if message.channel.category_id == modmail_category.id:

                current_prefixes = await self.bot.get_custom_prefix(message)
                message_starts_with_prefix = False
                for prefix in current_prefixes:
                    if message.content.startswith(prefix):
                        message_starts_with_prefix = True
                        break
                # ignore messages starting with prefix     
                if message_starts_with_prefix:
                    return
                
                # extract the user ID from the channel's topic
                user_id_str = message.channel.topic.split("Modmail User ID: ")[-1] if message.channel.topic else None
                try:
                    user_id = int(user_id_str)
                    user_id = int(user_id_str)
                    user = await self.bot.fetch_user(user_id)
                    # Send the DM to the user
                    embed = discord.Embed(
                        title="Message Received:",
                        description=message_content_with_attachments,
                        color=colors["red"],
                        timestamp=datetime.now()
                    )
                    embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                    embed.set_footer(text=f"User ID: {message.author.id}")
                    try:
                        await user.send(embed=embed)
                        await message.delete()

                        # Log that the message was sent
                        log_embed = discord.Embed(
                            title="Message Sent:",
                            description=f"{message_content_with_attachments}",
                            color=colors["red"],
                            timestamp=datetime.now()
                        )
                        log_embed.set_author(name=message.author.name, icon_url=message.author.avatar.url)
                        log_embed.set_footer(text=f"User ID: {message.author.id}")
                        await message.channel.send(embed=log_embed)


                    except discord.errors.Forbidden:
                        forbidden_embed = discord.Embed(
                            title="Failed to Deliver Message",
                            description="The message could not be delivered because the user has DMs disabled, has blocked the bot, or is not in the server anymore.",
                            color=colors["red"]
                        )
                        await message.channel.send(embed=forbidden_embed)

                    



                except (ValueError, TypeError):
                    # if topic does not contain a valid user ID or parsing issues
                    pass
                except discord.NotFound:
                    not_found_embed = discord.Embed(
                        title="Unable to Deliver Message",
                        description="It seems like target is not a member of the server anymore.",
                        color=colors["red"]
                    )
                    await message.author.send(embed=not_found_embed)

async def setup(bot):

    await bot.add_cog(Modmail(bot))