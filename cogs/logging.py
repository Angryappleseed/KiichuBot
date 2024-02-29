
#---------------------LOGGING COMMANDS and FEATURES---------------------#

import discord
import aiohttp

from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from datetime import datetime

from helpers.database import(
    add_modlog_channel, 
    get_modlog_channels, 
    remove_modlog_channel,
    get_msglog_webhooks,
    add_msglog_webhook,
    remove_msglog_webhook)

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes



#-----------Split messages up if cant fit in one embed--------------------------#
def chunk_messages(messages):
    chunks = []
    current_chunk = []
    current_length = 0

    for message in messages:
        message_length = len(message)
        if current_length + message_length > 1024 or len(current_chunk) >= 25:
            chunks.append(current_chunk)
            current_chunk = []
            current_length = 0
        current_chunk.append(message)
        current_length += message_length

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

def chunk_text(text, max_length=1024):
    return [text[i:i+max_length] for i in range(0, len(text), max_length)]


class Logging(commands.Cog, name="logging"):
    def __init__(self, bot):
        self.bot = bot
        self.log_channel = {}
        self.modlog_channel = {}


    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.loop.create_task(self.fetch_modlog_channels())
        self.bot.loop.create_task(self.fetch_msglog_webhooks())



#
#-------------------------------------MESSAGE EVENTS LOGGING------------------------------------------#
#


#-------------------FETCH MOD LOG CHANNELS-----------------#  
    async def fetch_msglog_webhooks(self):
        log_webhooks = await get_msglog_webhooks()
        for guild_id, webhook_url in log_webhooks:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                self.log_channel[guild.id] = webhook_url




#-------------------PURGE LOGGING (called in moderation.py)------------------------------#
    async def log_purge(self, channel, moderator, messages):
        if not messages:
            return

        webhook_url = self.log_channel.get(channel.guild.id)
        if not webhook_url:
            return


        message_chunks = chunk_messages(
            [f"{message.author}: {message.clean_content[:1024]}" for message in messages]
        )

        for i, chunk in enumerate(message_chunks):
            embed = discord.Embed(
                title=f"Purged Messages in #{channel.name} (Part {i+1}/{len(message_chunks)})",
                description=f"{len(messages)} messages were deleted by {moderator.mention}.",
                color=colors["red"],
                timestamp=datetime.now(),
            )

            messages_summary = "\n".join(chunk)
            if messages_summary:
                embed.add_field(name=f"Deleted Messages (Chunk {i+1})", value=messages_summary, inline=False)

            embed.set_footer(text=f"Moderator ID: {moderator.id}")

            async with aiohttp.ClientSession() as session:
                payload = {
                    "embeds": [embed.to_dict()],
                }
                await session.post(webhook_url, json=payload)



#--------------------MESSAGE DELETED LISTENER-------------------------#
    @commands.Cog.listener()
    async def on_message_delete(self, message):
        if message.guild and not message.author.bot:  # Ignore the bot's own messages
            webhook_url = self.log_channel.get(message.guild.id)
            if webhook_url:
                message_content_chunks = chunk_text(message.content)
                total_parts = len(message_content_chunks)
                for i, content_chunk in enumerate(message_content_chunks):
                    part_info = f" (Part {i+1}/{total_parts})" if total_parts > 1 else ""
                    embed = discord.Embed(
                        title=f"Message Deleted in #{message.channel.name}{part_info}",
                        description=content_chunk,
                        color=colors["red"],
                        timestamp=datetime.now(),
                    )
                    embed.set_author(name=str(message.author), icon_url=message.author.avatar.url)
                    embed.set_footer(text=f"User ID: {message.author.id}")

                    if message.attachments and i == 0:
                        attachment_info = "\n".join([f"{attachment.filename}\n{attachment.url}" for attachment in message.attachments])
                        embed.add_field(name="Attachments:", value=attachment_info, inline=False)

                    async with aiohttp.ClientSession() as session:
                        payload = {
                            "embeds": [embed.to_dict()],
                        }
                        await session.post(webhook_url, json=payload)




#--------------------MESSAGE EDITED LISTENER-------------------------#
    @commands.Cog.listener()
    async def on_message_edit(self, before, after):
            if before.guild and not before.author.bot:  # Ignore bot's own messages
                webhook_url = self.log_channel.get(after.guild.id)
                if webhook_url is None:
                    return 

                content_changed = before.content != after.content
                attachments_removed = len(before.attachments) > len(after.attachments)

                if content_changed or attachments_removed:
                    message_link = f"https://discord.com/channels/{after.guild.id}/{after.channel.id}/{after.id}"
                    before_content_chunks = chunk_text(before.content)
                    after_content_chunks = chunk_text(after.content)

                    # Loop through the maximum number of chunks between before and after
                    for i in range(max(len(before_content_chunks), len(after_content_chunks))):
                        description_lines = [f"### [Message Edited in #{before.channel.name}]({message_link})\n"]

                        if i < len(before_content_chunks):
                            description_lines.append(f"**Before: **{before_content_chunks[i]}\n")
                        if i < len(after_content_chunks):
                            description_lines.append(f"**After: **{after_content_chunks[i]}\n\n")

                        description_lines.append(f"**Message ID: **{after.id}\n")

                        embed = discord.Embed(
                            description="".join(description_lines),
                            color=colors["gold"],
                            timestamp=datetime.now()
                        )
                        embed.set_author(name=str(after.author), icon_url=after.author.avatar.url)
                        embed.set_footer(text=f"User ID: {after.author.id}")

                        if i == 0:
                            if attachments_removed:
                                removed_attachments = [attachment for attachment in before.attachments if attachment not in after.attachments]
                                if removed_attachments:
                                    removed_attachment_info = "\n".join(f"{attachment.filename}\n{attachment.url}" for attachment in removed_attachments)
                                    embed.add_field(name="Removed Attachments:", value=removed_attachment_info, inline=False)
                            elif before.attachments:
                                attachment_info = "\n".join([f"{attachment.filename}\n{attachment.url}" for attachment in before.attachments])
                                if attachment_info:
                                    embed.add_field(name="Attachments:", value=attachment_info, inline=False)

                        # Send the embed for the current chunk
                        async with aiohttp.ClientSession() as session:
                            payload = {
                                "embeds": [embed.to_dict()],
                            }
                            await session.post(webhook_url, json=payload)



#-------------------SET MESSAGE LOGS CHANNEL----------------------------------#
    @commands.hybrid_command(name="setmsglogs", description="Sets the message logging channel.")
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="The channel you want msg logs to go to."
    )
    async def set_msglog_channel(self, context: Context, channel: discord.TextChannel):
        if not channel.permissions_for(context.guild.me).manage_webhooks:
            return await context.send("I do not have permission to manage webhooks in the specified channel.")

        existing_webhook_url = self.log_channel.get(context.guild.id)
        if existing_webhook_url:
            webhook_id = existing_webhook_url.split("/")[-2]
            try:
                existing_webhook = await self.bot.fetch_webhook(webhook_id)
                await existing_webhook.delete(reason="Replacing message logging webhook")
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                await context.send(f"Failed to delete the existing webhook: {e}")
                return

        try:
            with open('images/KiichuBotPFP.png', 'rb') as avatar_file:
                avatar_bytes = avatar_file.read()

            webhook = await channel.create_webhook(name="KiichuBot Logging", avatar=avatar_bytes)
            self.log_channel[context.guild.id] = webhook.url
            await add_msglog_webhook(context.guild.id, webhook.url)
            embed = discord.Embed(
                description=f"Logging channel set to {channel.mention}! {emotes['comfy']}",
                color=colors["blue"],
                timestamp=datetime.now(),
            )
            await context.send(embed=embed)
        except discord.HTTPException as e:
            await context.send(f"Failed to create a webhook: {e}")




#-------------------RESET MESSAGE LOGS CHANNEL----------------------------------#
    @commands.hybrid_command(name="removemsglogs", description="Disables the message logging channel.")
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def remove_msglog_channel_command(self, context: Context):
        log_webhooks = await get_msglog_webhooks()
        webhook_url = next((webhook for guild_id, webhook in log_webhooks if int(guild_id) == context.guild.id), None)
        if webhook_url:
            webhook_id = webhook_url.split("/")[-2]

            try:
                webhook = await self.bot.fetch_webhook(webhook_id)
                await webhook.delete(reason="Message logging disabled by user")
            except discord.NotFound:
                pass
            except discord.HTTPException as e:
                return await context.send(f"Failed to delete the webhook: {e}")

        await remove_msglog_webhook(context.guild.id)
        if context.guild.id in self.log_channel:
            del self.log_channel[context.guild.id]
        embed = discord.Embed(
            description=f"Message logging has been disabled! {emotes['comfy']}",
            color=colors["blue"],
            timestamp=datetime.now(),
        )
        await context.send(embed=embed)






#
#---------------------------MOD EVENT LOGGING--------------------------------#
#

    async def fetch_modlog_channels(self):
        modlog_channels = await get_modlog_channels()
        for guild_id, channel_id in modlog_channels:
            guild = self.bot.get_guild(int(guild_id))
            if guild:
                channel = guild.get_channel(int(channel_id))
                if channel:
                    self.modlog_channel[guild.id] = channel

#------------------------BAN LISTENER--------------------#
    @commands.Cog.listener()
    async def on_member_ban(self, guild, user):
        modlog_channel = self.modlog_channel.get(guild.id)
        if modlog_channel:
            ban_entry = await guild.fetch_ban(user)
            reason = ban_entry.reason if ban_entry.reason else "No reason provided"
            responsible_moderator = "Unknown"
            
            try:
                async for audit_log in guild.audit_logs(action=discord.AuditLogAction.ban, limit=1):
                    if audit_log.target == user:
                        responsible_moderator = audit_log.user
                        break
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

            embed = discord.Embed(
                title="Member Banned",
                description=f"**User**: {user.mention} ({user})\n**Banned by**: {responsible_moderator}",
                color=colors["red"],
                timestamp=datetime.now(),
            )
            embed.add_field(name="Reason:", value=reason)
            embed.set_footer(text=f"User ID: {user.id}")
            embed.set_author(name=user.display_name, icon_url=user.avatar.url)
        await modlog_channel.send(embed=embed)

#------------------------UNBAN LISTENER--------------------#
    @commands.Cog.listener()
    async def on_member_unban(self, guild, user):
        modlog_channel = self.modlog_channel.get(guild.id)
        if modlog_channel:
            responsible_moderator = "Unknown"
            try:
                async for audit_log in guild.audit_logs(action=discord.AuditLogAction.unban, limit=1):
                    if audit_log.target == user:
                        responsible_moderator = audit_log.user
                        break 
            except discord.Forbidden:
                pass
            except discord.HTTPException:
                pass

            embed = discord.Embed(
                title="Member Unbanned",
                description=f"**User**: {user.mention} ({user})\n**Unbanned by**: {responsible_moderator}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"User ID: {user.id}")
            embed.set_author(name=user.display_name, icon_url=user.avatar.url if user.avatar else user.default_avatar.url)

            await modlog_channel.send(embed=embed)




#------------------------KICK LISTENER (Not working properly)-----------------------#
    # async def is_kick(self, guild, member):
    #     try:
    #         async for log in guild.audit_logs(limit=1, action=discord.AuditLogAction.kick):
    #             if log.target == member:
    #                 return (True, log.user)
    #     except discord.Forbidden:
    #         pass
    #     except discord.HTTPException:
    #         pass
    #     return (False, None)

    
    # @commands.Cog.listener()
    # async def on_member_remove(self, member):
    #     modlog_channel = self.modlog_channel.get(member.guild.id)
    #     if modlog_channel:
    #         was_kicked, moderator = await self.is_kick(member.guild, member)
    #         if was_kicked:
    #             embed = discord.Embed(
    #                 title="Member Kicked",
    #                 description=f"**User**: {member.mention} ({member})\n**Kicked by**: {moderator}",
    #                 color=colors["red"],
    #                 timestamp=datetime.now(),
    #             )
    #         else:
    #             embed = discord.Embed(
    #                 title="Member Left",
    #                 description=f"**User**: {member.mention} ({member})",
    #                 color=colors["red"],
    #                 timestamp=datetime.now(),
    #             )

    #         embed.set_footer(text=f"User ID: {member.id}")
    #         embed.set_author(name=member.display_name, icon_url=member.avatar.url)
    #         await modlog_channel.send(embed=embed)


#------------------------TIME OUT LISTENER-----------------------#
    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        modlog_channel = self.modlog_channel.get(after.guild.id)
        if modlog_channel:
            if before.timed_out_until is None and after.timed_out_until is not None:
                embed = discord.Embed(
                    title="Member Timed Out",
                    description=f"**User**: {after.mention} ({after})",
                    color=colors["gold"],
                    timestamp=datetime.now(),
                )
                embed.set_footer(text=f"User ID: {after.id}")
                embed.set_author(name=after.display_name, icon_url=after.avatar.url)
                await modlog_channel.send(embed=embed)


#------------------------UNTIME OUT LISTENER (doesnt work)-----------------------#
        # elif before.timed_out_until is not None and after.timed_out_until is None:
        #     embed = discord.Embed(
        #         title="Member Untimed Out",
        #         description=f"**User**: {after.mention} ({after})",
        #         color=colors["green"],
        #         timestamp=datetime.now(),
        #     )
        #     embed.set_footer(text=f"User ID: {after.id}")
        #     embed.set_author(name=after.display_name, icon_url=after.avatar.url)
        #     await modlog_channel.send(embed=embed)




#-------------------------SET MOD LOGS CHANNEL----------------------------#
    @commands.hybrid_command(name="setmodlogs", description="Sets the mod event logging channel.")
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="The channel you want mod logs to go to."
    )
    async def set_modlog_channel(self, context: Context, channel: discord.TextChannel):
        self.modlog_channel[context.guild.id] = channel
        await add_modlog_channel(context.guild.id, channel.id)
        embed = discord.Embed(
            description=f"Mod event logging channel set to {channel.mention}!",
            color=colors["blue"],
            timestamp=datetime.now(),
        )
        await context.send(embed=embed)



#-------------------RESET MOD LOGS CHANNEL----------------------------------#
    @commands.hybrid_command(name="removemodlogs", description="Disables the mod event logging channel.")
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def remove_modlog_channel_command(self, context: Context):
        await remove_modlog_channel(context.guild.id)
        if context.guild.id in self.modlog_channel:
            del self.modlog_channel[context.guild.id]
        embed = discord.Embed(
            description="Mod event logging has been disabled!",
            color=colors["red"],
            timestamp=datetime.now(),
        )
        await context.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Logging(bot))