import asyncio
import json
import re
import os
import aiosqlite

from typing import List

from datetime import datetime, timezone

import discord
from discord import app_commands
from discord.ext import commands

from discord.ext import commands, tasks
from discord.ext.commands import Context

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes


from helpers.database import(
    add_automated_message,
    remove_automated_message,
    get_automated_messages,
    get_due_automated_messages,
    update_next_run
    )

DATABASE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'database.db')


# Load the role IDs from config.json
with open('config.json', 'r') as config_file:
    config = json.load(config_file)

FRESH_MEAT_ROLE_ID = int(config['fresh_meat_role_id'])
HEADPATTERS_ROLE_ID = int(config['headpatters_role_id'])
LIWE_ROLE_ID = int(config['liwe_role_id'])
PROTECTOR_ROLE_ID = int(config['protector_role_id'])
GOD_ROLE_ID = int(config['god_role_id'])
FAILED_VERIFY_ROLE_ID = int(config['failed_verify_role_id'])
MOD_ROLE_IDS = config['modRoles']
GAME_ROOM_2 = 999729521219616840
VCLOGS_CHANNEL_ID = int(config['vclogs_channel_id'])
# Backrooms chat and Jabol4Pan
EXCLUDED_VOICE_CHANNELS = [786890857499852830, 1222214029829738538]



def parse_time_interval(interval: str) -> int:
    match = re.match(r"(\d+)(s|min|hr|day)$", interval)
    if not match:
        raise ValueError("Invalid time interval format.")
    
    amount, unit = match.groups()
    amount = int(amount)
    
    if unit == "s":
        return amount
    elif unit == "min":
        return amount * 60
    elif unit == "hr":
        return amount * 3600
    elif unit == "day":
        return amount * 86400
    else:
        raise ValueError("Invalid time unit.")


def format_interval(seconds):
    units = [
        ('day', 86400),
        ('hr', 3600),
        ('min', 60),
        ('s', 1),
    ]
    parts = []
    for name, count in units:
        value = seconds // count
        if value:
            seconds -= value * count
            parts.append(f"{value} {name}")

    return ' '.join(parts)



class Tasks(commands.Cog, name="tasks"):
    def __init__(self, bot):
        self.bot = bot
        self.min_account_age_days = 7
        self.log_channel_id = 906624474403717141
        self.new_account_detection_enabled = True
        self.auto_mute_enabled = False



#---------Automated message loop--------------------#
    @commands.Cog.listener()
    async def on_ready(self):
        self.automated_message_task.start()

    @tasks.loop(seconds=60)
    async def automated_message_task(self):
        messages = await get_due_automated_messages()
        for msg_id, channel_id, message in messages:
            channel = self.bot.get_channel(int(channel_id))
            if channel:
                await channel.send(message)
                async with aiosqlite.connect(DATABASE_PATH) as db:
                    cursor = await db.execute(
                        "SELECT interval_seconds FROM automated_messages WHERE id = ?",
                        (msg_id,)
                    )
                    interval = await cursor.fetchone()
                if interval:
                    await update_next_run(msg_id, interval[0])

    @automated_message_task.before_loop
    async def before_automated_message_task(self):
        await self.bot.wait_until_ready()







#---------Role update listener--------------------#

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        higher_roles = {HEADPATTERS_ROLE_ID, LIWE_ROLE_ID, PROTECTOR_ROLE_ID, GOD_ROLE_ID}

        # Detect if a user receives headpatters or higher roles and remove fresh meat role
        received_higher_role = any(role.id in higher_roles for role in after.roles) and not any(role.id in higher_roles for role in before.roles)
        if received_higher_role and FRESH_MEAT_ROLE_ID in [role.id for role in before.roles]:
            fresh_meat_role = discord.utils.get(after.guild.roles, id=FRESH_MEAT_ROLE_ID)
            if fresh_meat_role:
                await after.remove_roles(fresh_meat_role)

        # Detect if someone gets fresh meat while having headpatters or higher roles
        if FRESH_MEAT_ROLE_ID in [role.id for role in after.roles]:
            if any(role.id in higher_roles for role in after.roles):
                fresh_meat_role = discord.utils.get(after.guild.roles, id=FRESH_MEAT_ROLE_ID)
                if fresh_meat_role:
                    await after.remove_roles(fresh_meat_role)

        # Detect if someone failed verify
        if FAILED_VERIFY_ROLE_ID in [role.id for role in after.roles] and FAILED_VERIFY_ROLE_ID not in [role.id for role in before.roles]:
            if any(role.id in higher_roles for role in after.roles):
                log_channel = self.bot.get_channel(self.log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="Goofball clicked on the anti-bot button while in the server",
                        description=f"**User: **{after.name} {after.mention}\nUser clicked on the button that tells them NOT TO CLICK ON, but was not kicked due to being headpatters+ {emotes['pien']}",
                        color=colors["gold"],
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text=f"User ID: {after.id}")
                    await log_channel.send(embed=embed)

                failed_verify_role = discord.utils.get(after.guild.roles, id=FAILED_VERIFY_ROLE_ID)
                if failed_verify_role:
                    await after.remove_roles(failed_verify_role)
            else:
                log_channel = self.bot.get_channel(self.log_channel_id)
                if log_channel:
                    embed = discord.Embed(
                        title="Potential Bot Kicked",
                        description=f"**User: **{after.name} {after.mention}\nUser clicked on the button that tells them NOT TO CLICK ON, so they were automatically removed. {emotes['pien']}",
                        color=colors["red"],
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text=f"User ID: {after.id}")
                    await log_channel.send(embed=embed)

                failed_verify_role = discord.utils.get(after.guild.roles, id=FAILED_VERIFY_ROLE_ID)
                if failed_verify_role:
                    await after.remove_roles(failed_verify_role)

                # short delay before kicking the user
                await asyncio.sleep(2)

                await after.kick(reason="Clicked on Bot Deterrent button.")



#------------NEW ACCOUNT DETECTION------------------#


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        if not self.new_account_detection_enabled:
            return

        account_age_days = (datetime.now(timezone.utc) - member.created_at).days
        if account_age_days < self.min_account_age_days:
            try:
                await member.send(
                    f"Hello {member.name}, your account is suspected to be an alt in {member.guild.name}. {emotes['pien']}"
                    f"If you believe this to be an error, please feel free to add and DM `angryappleseed` about the issue."
                )
            except discord.Forbidden:
                pass 

            await member.kick(reason=f"Account is too new. Must be at least {self.min_account_age_days} days old.")

            # Log the kick action
            log_channel = self.bot.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="Suspected Alt Kicked",
                    description=f"**User: **{member.name}{member.mention}\nAccount is only {account_age_days} days old. (required age is {self.min_account_age_days} days) {emotes['pien']}",
                    color=colors["red"],
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"User ID: {member.id}")
                await log_channel.send(embed=embed)


 #------------AUTO MUTE IN GAME ROOM 2------------------#

    @commands.Cog.listener()
    async def on_voice_state_update(self, member, before, after):
        if not self.auto_mute_enabled:
            return

        # Mute the user when they join the designated voice channel
        if after.channel and after.channel.id == GAME_ROOM_2 and (before.channel is None or before.channel.id != GAME_ROOM_2):
            if not any(role.id in MOD_ROLE_IDS for role in member.roles):
                await member.edit(mute=True)
        
        # Unmute the user when they leave the designated voice channel
        if before.channel and before.channel.id == GAME_ROOM_2 and (after.channel is None or after.channel.id != GAME_ROOM_2):
            if not any(role.id in MOD_ROLE_IDS for role in member.roles):
                await member.edit(mute=False)


#---------------TOGGLE NEW-ACCOUNT AUTOREMOVER----------------#

    @commands.hybrid_command(
            name="togglealtdetection",
            description="Disables the auto-kick feature for new accounts."
            )
    @commands.guild_only()
    @checks.not_blacklisted()
    @checks.is_moderator()
    @commands.has_permissions(manage_guild=True)
    async def togglealtdetection(self, ctx: commands.Context):
        self.new_account_detection_enabled = not self.new_account_detection_enabled
        status = "enabled" if self.new_account_detection_enabled else "disabled"
        embed = discord.Embed(
            description=f"New account detection has been {status}. {emotes['comfy']}",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)


#---------------TOGGLE AUTO-MUTE FEATURE----------------#

    @commands.hybrid_command(
        name="toggleautomute",
        description="Toggles the auto-mute feature for the specified voice channel."
    )
    @commands.guild_only()
    @checks.not_blacklisted()
    @checks.is_moderator()
    @commands.has_permissions(manage_guild=True)
    async def toggleautomute(self, ctx: commands.Context):
        self.auto_mute_enabled = not self.auto_mute_enabled
        status = "enabled" if self.auto_mute_enabled else "disabled"
        embed = discord.Embed(
            description=f"Auto-mute feature has been {status}. {emotes['comfy']}",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)



#-------------------------ADD AUTO MESSAGE COMMAND--------------------------#

    @commands.hybrid_command(
        name="addautomessage",
        description="Schedules a new automated message."
    )
    @checks.is_moderator()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="The target channel for the messages.",
        interval="The time between repeats (s, min, hr).",
        message="The message you want to be sent."
    )
    async def add_automated_message(self, ctx: commands.Context, channel: discord.TextChannel, interval: str, *, message: str):
        interval_seconds = parse_time_interval(interval)
        await add_automated_message(str(channel.id), message, interval_seconds)
        embed = discord.Embed(
            description=f"Automated message scheduled in {channel.mention} every {interval}.",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)
        await channel.send(message)


#-------------------------REMOVE AUTO MESSAGE COMMAND--------------------------#

    @commands.hybrid_command(
        name="removeautomessage",
        description="Removes a specified automated message."
    )
    @checks.is_moderator()
    @commands.has_permissions(manage_guild=True)
    async def remove_automated_message(self, ctx: commands.Context, message_id: int):
        await remove_automated_message(message_id)
        embed = discord.Embed(
            description=f"Automated message with ID {message_id} has been removed.",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)


#-------------------------LIST AUTO MESSAGE COMMAND--------------------------#

    @commands.hybrid_command(
        name="listautomessages",
        description="Lists all scheduled automated messages."
    )
    @checks.is_moderator()
    @commands.has_permissions(manage_guild=True)
    async def list_automated_messages(self, ctx: commands.Context):
        messages = await get_automated_messages()
        embed = discord.Embed(title="Automated Messages", color=colors["blue"])
        for msg in messages:
            formatted_interval = format_interval(msg[3])
            embed.add_field(name=f"ID: {msg[0]}", value=f"Channel: <#{msg[1]}> - Interval: {formatted_interval}\nMessage: {msg[2]}", inline=False)
        await ctx.send(embed=embed)




#--------------------VOICE CHANNEL LOGGING----------------------#

    @commands.Cog.listener()
    async def on_voice_state_update(self, member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
        vclogs_channel = self.bot.get_channel(VCLOGS_CHANNEL_ID)

        # exclude backrooms and jabol4pan from logging
        if (before.channel and before.channel.id in EXCLUDED_VOICE_CHANNELS) or (after.channel and after.channel.id in EXCLUDED_VOICE_CHANNELS):
            return

        # User joins a voice channel
        if before.channel is None and after.channel is not None:
            embed = discord.Embed(
                title="User Joined Voice Channel",
                description=f"{member}{member.mention} joined **{after.channel.name}**",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"User ID: {member.id}")
            await vclogs_channel.send(embed=embed)

        # User leaves a voice channel
        elif before.channel is not None and after.channel is None:
            embed = discord.Embed(
                title="User Left Voice Channel",
                description=f"{member}{member.mention} left **{before.channel.name}**",
                color=colors["red"],
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"User ID: {member.id}")
            await vclogs_channel.send(embed=embed)

        # User switches voice channels
        elif before.channel is not None and after.channel is not None and before.channel.id != after.channel.id:
            embed = discord.Embed(
                title="User Switched Voice Channel",
                description=f"{member}{member.mention} switched from **{before.channel.name}** to **{after.channel.name}**",
                color=colors["gold"],
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"User ID: {member.id}")
            await vclogs_channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tasks(bot))