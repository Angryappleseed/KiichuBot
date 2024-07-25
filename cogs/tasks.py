import asyncio
import json

from datetime import datetime, timezone

import discord
from discord.ext import commands

from discord.ext import commands, tasks
from discord.ext.commands import Context

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes


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


class Tasks(commands.Cog, name="tasks"):
    def __init__(self, bot):
        self.bot = bot
        self.min_account_age_days = 7
        self.log_channel_id = 906624474403717141


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
        if after.channel and after.channel.id == GAME_ROOM_2:
            if not any(role.id in MOD_ROLE_IDS for role in member.roles):
                await member.edit(mute=True)



#---------------TOGGLE NEW-ACCOUNT AUTOREMOVER----------------#

    @commands.hybrid_command(
            name="togglealtdetection",
            description="Disables the auto-kick feature for new accounts."
            )
    @commands.guild_only()
    @checks.not_blacklisted()
    @checks.is_moderator()
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
    async def toggleautomute(self, ctx: commands.Context):
        self.auto_mute_enabled = not self.auto_mute_enabled
        status = "enabled" if self.auto_mute_enabled else "disabled"
        embed = discord.Embed(
            description=f"Auto-mute feature has been {status}. {emotes['comfy']}",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Tasks(bot))