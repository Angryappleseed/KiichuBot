import asyncio
import json
import re
import os
import aiosqlite
import random

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


#welcome message imports
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps
import io
import textwrap


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

# Welcome settings
WELCOME_CHANNEL_ID = 751367236966547457
TEMPLATE_PATH = './images/Kiichan_Welcome.png'
FONT_PATH = './fonts/Poppins-Regular.ttf'

HIGHER_ROLES = {HEADPATTERS_ROLE_ID, LIWE_ROLE_ID, PROTECTOR_ROLE_ID, GOD_ROLE_ID}

APPEAL_SERVER_INVITE = "https://discord.gg/p5DnRR9z6w"

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


#----------------- Whitelist Pagination------------------#

class WhitelistPaginator(discord.ui.View):
    def __init__(self, rows: list, author: discord.Member, items_per_page: int = 10):
        super().__init__(timeout=180)  # 3 minute timeout
        self.rows = rows
        self.author = author
        self.items_per_page = items_per_page
        self.current_page = 0
        self.total_pages = (len(rows) + items_per_page - 1) // items_per_page

        # Disable buttons initially if needed
        self.update_buttons()

    def get_embed(self, page: int) -> discord.Embed:
        start = page * self.items_per_page
        end = start + self.items_per_page
        page_rows = self.rows[start:end]

        embed = discord.Embed(
            title=f"Whitelisted Alts ({len(self.rows)} total)",
            color=colors["blue"]
        )

        for row in page_rows:
            user_id, mod_id, reason, timestamp = row
            embed.add_field(
                name=f"User ID: `{user_id}`",
                value=f"**Whitelisted by:** <@{mod_id}>\n"
                      f"**Reason:** {reason or 'None'}\n"
                      f"**Date:** {timestamp}",
                inline=False
            )

        embed.set_footer(text=f"Page {page + 1}/{self.total_pages} • Use buttons to navigate")
        return embed

    def update_buttons(self):
        self.first_button.disabled = self.current_page == 0
        self.prev_button.disabled = self.current_page == 0
        self.next_button.disabled = self.current_page >= self.total_pages - 1
        self.last_button.disabled = self.current_page >= self.total_pages - 1

    @discord.ui.button(label="Start", style=discord.ButtonStyle.gray)
    async def first_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Don't touch my SHIT!", ephemeral=True)
        
        self.current_page = 0
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(self.current_page), view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.gray)
    async def prev_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Don't touch my SHIT!", ephemeral=True)
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(self.current_page), view=self)

    @discord.ui.button(label="Next", style=discord.ButtonStyle.gray)
    async def next_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Don't touch my SHIT!", ephemeral=True)
        
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_buttons()
            await interaction.response.edit_message(embed=self.get_embed(self.current_page), view=self)

    @discord.ui.button(label="End", style=discord.ButtonStyle.gray)
    async def last_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Don't touch my SHIT!", ephemeral=True)
        
        self.current_page = self.total_pages - 1
        self.update_buttons()
        await interaction.response.edit_message(embed=self.get_embed(self.current_page), view=self)







#----------------- TASKS --------------------------#



class Tasks(commands.Cog, name="tasks"):
    def __init__(self, bot):
        self.bot = bot
        self.min_account_age_days = 7
        self.log_channel_id = 906624474403717141
        self.new_account_detection_enabled = True
        self.auto_mute_enabled = False
        self.auto_image_message_enabled = False
        self.auto_image_message_task = None
        self.auto_image_message_interval = 3600  # Default interval: 1 hr
        self.image_message_channel_id = None 

        self.images_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "images")
        # Hardcoded list of image-message combos
        self.image_message_combos = [
            {"image": os.path.join(self.images_dir, "KiiAdvancedgg.png"), "message": "Go get yourself some  banger flavors at https://advanced.gg! Don't forget to use code KIICHAN for a discount!"},
            {"image": os.path.join(self.images_dir, "KiiTwitch.png"), "message": "Go check out Kiichan's stream! Henry is giving away 50 KiiCoins:tm:!"},
        ]
        self.TICKET_TOOL_BOT_ID = 557628352828014614

        self.goodbye_messages = [
            "***{name}** has been consumed. <:Kiichomp:789878586907557928>",
            "**{name}** has taken their leave... They will be missed. <:KiiCrying:1334189979395424348>",
            "The void has consumed **{name}**. <:KiiNotLikeThis:812243537058856960>",
            "Good luck on your ventures **{name}**! Surely they didn't find a new oshi to replace Kiichan. <:Kiien:1192124110881439844>",
            "**{name}** has left the fox den. <a:KiiNodders:1015000796355641424>",
            "**{name}** will be remembered... <a:KiiNodders:1015000796355641424>",
        ]

#----------- whitelist helpers----------#

    async def is_whitelisted(self, user_id: str) -> bool:
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute(
                "SELECT 1 FROM whitelisted_alts WHERE user_id = ?", (user_id,)
            )
            return await cursor.fetchone() is not None

    async def add_to_whitelist(self, user_id: str, mod_id: str, reason: str = None):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                """
                INSERT OR REPLACE INTO whitelisted_alts 
                (user_id, whitelisted_by, reason) 
                VALUES (?, ?, ?)
                """,
                (user_id, mod_id, reason)
            )
            await db.commit()\
    
    async def remove_from_whitelist(self, user_id: str):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            await db.execute(
                "DELETE FROM whitelisted_alts WHERE user_id = ?",
                (user_id,)
            )
            await db.commit()



#-------------- Welcome message Logic------------------------#
    async def send_fancy_welcome(self, member: discord.Member):
        """Send fancy welcome image when Fresh Meat role is given."""
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(str(member.avatar.replace(size=256).url)) as resp:
                    avatar_bytes = await resp.read()

            with Image.open(TEMPLATE_PATH) as template:
                with Image.open(io.BytesIO(avatar_bytes)) as avatar:
                    avatar = avatar.resize((350, 350))
                    mask = Image.new('L', avatar.size, 0)
                    draw = ImageDraw.Draw(mask)
                    draw.ellipse((0, 0) + avatar.size, fill=255)
                    avatar = ImageOps.fit(avatar, mask.size, centering=(0.5, 0.5))
                    avatar.putalpha(mask)

                    border_size = 10
                    total_size = (avatar.size[0] + border_size * 2, avatar.size[1] + border_size * 2)
                    bordered_avatar = Image.new('RGBA', total_size, (255, 255, 255, 0))
                    bordered_avatar.paste(avatar, (border_size, border_size), avatar)

                    template_width, template_height = template.size
                    avatar_width, avatar_height = bordered_avatar.size
                    avatar_position = ((template_width - avatar_width) // 2, (template_height - avatar_height) // 2 - 57)

                    template.paste(bordered_avatar, avatar_position, bordered_avatar)

                    draw = ImageDraw.Draw(template)
                    try:
                        font = ImageFont.truetype(FONT_PATH, 48)
                    except IOError:
                        font = ImageFont.load_default()

                    username = member.name[:20] + '...' if len(member.name) > 20 else member.name
                    left, top, right, bottom = font.getbbox(username)
                    text_width = right - left
                    text_position = ((template_width - text_width) // 2, avatar_position[1] + avatar_height + 10)
                    draw.text(text_position, username, fill=(0, 0, 0), font=font)

                output_buffer = io.BytesIO()
                template.save(output_buffer, 'PNG')
                output_buffer.seek(0)
                file = discord.File(fp=output_buffer, filename="welcome_image.png")

            msg = f"Hi konkon! Welcome to Kiichan's Fox Den {member.mention}!\nPlease read the <#912401777356312576> and enjoy your stay!\n"

            await channel.send(msg, file=file)

        except Exception as e:
            print(f"Welcome image failed for {member}: {e}")
            await channel.send(f"Welcome {member.mention}! Please enjoy your sta")







#---------------EVENT LISTENERS--------------------#





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



#---------Rename Tickettool channels-----------#
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):

        # Check if the message is from TicketTool and in a ticket channel
        if message.author.id == self.TICKET_TOOL_BOT_ID and "ticket-" in message.channel.name:

            # Check if there's a mention in the message
            if message.mentions:
                ticket_creator = message.mentions[0]  # Get the mentioned user
                new_channel_name = f"{ticket_creator.name.lower()}"

                # Rename the channel
                try:
                    await message.channel.edit(name=new_channel_name)
                    print(f"Renamed channel to {new_channel_name}")
                except Exception as e:
                    print(f"Failed to rename channel: {e}")




#---------Role update listener--------------------#

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        higher_roles = {HEADPATTERS_ROLE_ID, LIWE_ROLE_ID, PROTECTOR_ROLE_ID, GOD_ROLE_ID}

        # Trigger fancy welcome when Fresh Meat role is assigned (new users via onboarding or Carl-bot reassign)
        if (FRESH_MEAT_ROLE_ID not in [r.id for r in before.roles] and 
            FRESH_MEAT_ROLE_ID in [r.id for r in after.roles]):
            await self.send_fancy_welcome(after)

        # detect if a user receives headpatters or higher roles and remove fresh meat role
        received_higher_role = any(role.id in higher_roles for role in after.roles) and not any(role.id in higher_roles for role in before.roles)
        if received_higher_role and FRESH_MEAT_ROLE_ID in [role.id for role in before.roles]:
            fresh_meat_role = discord.utils.get(after.guild.roles, id=FRESH_MEAT_ROLE_ID)
            if fresh_meat_role:
                await after.remove_roles(fresh_meat_role)

        # detect if someone gets fresh meat while having headpatters or higher roles
        if FRESH_MEAT_ROLE_ID in [role.id for role in after.roles]:
            if any(role.id in higher_roles for role in after.roles):
                fresh_meat_role = discord.utils.get(after.guild.roles, id=FRESH_MEAT_ROLE_ID)
                if fresh_meat_role:
                    await after.remove_roles(fresh_meat_role)

        # detect if someone failed verify
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

                # short delay before kicking the user to make sure nothing breaks
                await asyncio.sleep(2)

                await after.kick(reason="Clicked on Bot Deterrent button.")



#------------NEW ACCOUNT DETECTION------------------#


    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        # Alt Detection only
        if self.new_account_detection_enabled:
            account_age_days = (datetime.now(timezone.utc) - member.created_at).days
            if account_age_days < self.min_account_age_days:
                if await self.is_whitelisted(str(member.id)):
                    log_channel = self.bot.get_channel(self.log_channel_id)
                    if log_channel:
                        embed = discord.Embed(
                            title="Whitelisted Alt Joined",
                            description=f"**User:** {member} {member.mention}\nAccount age: {account_age_days} days",
                            color=colors["blue"],
                            timestamp=datetime.now()
                        )
                        embed.set_footer(text=f"User ID: {member.id}")
                        await log_channel.send(embed=embed)
                    return

                # Kick flow
                try:
                    await member.send(
                        f"Heyo {member.name}!\n"
                        f"Your account is suspected to be a bot or alt account and was automatically removed from Kiichan's server.\n\n"
                        f"To join, please join our appeal server and post your appeal there: {APPEAL_SERVER_INVITE}\n"
                        f"A moderator will review it and whitelist you if approved. <a:KiiNodders:1015000796355641424> "
                    )
                except discord.Forbidden:
                    pass
                await member.kick(reason=f"Account too new ({account_age_days} days).")
                return


#-------------ON MEMBER LEAVE - GOODBYE MESSAGE----------------#

    @commands.Cog.listener()
    async def on_member_remove(self, member: discord.Member):
        channel = self.bot.get_channel(WELCOME_CHANNEL_ID)
        if not channel:
            return

        template = random.choice(self.goodbye_messages)

        goodbye_message = template.format(
            mention=member.mention,
            name=member.name
        )
        
        await channel.send(goodbye_message)


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



#------------------- NEW ACCOUNT AUTO-REMOVE COMMANDS--------------$


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


#---------------------ADD USER TO WHITELIST---------------------#


    @commands.hybrid_command(name="whitelist",
                             description="Whitelist a user for alt detection"
                             )
    @checks.not_blacklisted()
    @commands.guild_only()
    @checks.is_moderator()
    @app_commands.describe(user="User to whitelist (ID, mention, or name)", reason="Optional reason")
    async def whitelist_user(self, ctx: commands.Context, user: discord.User, reason: str = None):
        await self.add_to_whitelist(str(user.id), str(ctx.author.id), reason)
        
        embed = discord.Embed(
            title="User Whitelisted",
            description=f"{user.mention} (`{user.id}`) has been added to the alt whitelist.",
            color=colors["blue"]
        )
        if reason:
            embed.add_field(name="Reason", value=reason, inline=False)
        await ctx.send(embed=embed)


#------------------UNWHITELIST USER---------------------------#


    @commands.hybrid_command(name="unwhitelist",
                             description="Remove a user from the alt whitelist"
                             )
    @checks.not_blacklisted()
    @commands.guild_only()
    @checks.is_moderator()
    @app_commands.describe(user="User to remove from whitelist (ID, mention, or name)")
    async def unwhitelist_user(self, ctx: commands.Context, user: discord.User):
        await self.remove_from_whitelist(str(user.id))
        
        embed = discord.Embed(
            title="User Removed from Whitelist",
            description=f"{user.mention} (`{user.id}`) has been removed from the alt whitelist.",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)


#-----------------------LIST WHITELIST------------------#


    @commands.hybrid_command(name="listwhitelist",
                             description="List all whitelisted users"
                             )
    @commands.guild_only()
    @checks.not_blacklisted()
    @checks.is_moderator()
    async def list_whitelist(self, ctx: commands.Context):
        async with aiosqlite.connect(DATABASE_PATH) as db:
            cursor = await db.execute("""
                SELECT user_id, whitelisted_by, reason, whitelisted_at 
                FROM whitelisted_alts 
                ORDER BY whitelisted_at DESC
            """)
            rows = await cursor.fetchall()

        if not rows:
            return await ctx.send("No users are currently whitelisted.")

        view = WhitelistPaginator(rows, ctx.author)
        embed = view.get_embed(0)
        await ctx.send(embed=embed, view=view)




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



#-------------------------TOGGLE AUTO IMAGE MESSAGE-------------------------#
    # @commands.hybrid_command(
    #     name="toggleads",
    #     description="Toggles the automated ads."
    # )
    # @checks.is_moderator()
    # @commands.has_permissions(manage_guild=True)
    # @app_commands.describe(
    #     channel="The channel where the messages will be sent.",
    #     interval="Time interval for sending the image-message combo (e.g., '10min', '1hr')."
    # )
    # async def toggle_image_cycle(self, ctx: commands.Context, channel: discord.TextChannel, interval: str):
    #     # Parse the interval
    #     try:
    #         interval_seconds = parse_time_interval(interval)
    #     except ValueError:
    #         embed = discord.Embed(
    #             description="Invalid interval format. Use formats like `10min`, `1hr`, or `2day`.",
    #             color=colors["red"]
    #         )
    #         await ctx.send(embed=embed)
    #         return

    #     # Toggle the feature
    #     self.auto_image_message_enabled = not self.auto_image_message_enabled
    #     if self.auto_image_message_enabled:
    #         self.auto_image_message_interval = interval_seconds
    #         self.image_message_channel_id = channel.id

    #         # Start the background task
    #         if not self.auto_image_message_task:
    #             self.auto_image_message_task = self.bot.loop.create_task(self.image_message_cycle())
            
    #         embed = discord.Embed(
    #             description=f"Auto image-message feature enabled in {channel.mention}. Interval: {interval}.",
    #             color=colors["blue"]
    #         )
    #     else:
    #         if self.auto_image_message_task:
    #             self.auto_image_message_task.cancel()
    #             self.auto_image_message_task = None
    #             self.image_message_channel_id = None
            
    #         embed = discord.Embed(
    #             description="Auto image-message feature disabled.",
    #             color=colors["red"]
    #         )

    #     await ctx.send(embed=embed)

    # #-------------------------IMAGE MESSAGE CYCLE-------------------------#
    # async def image_message_cycle(self):
    #     while self.auto_image_message_enabled:
    #         # Get the target channel
    #         if not self.image_message_channel_id:
    #             break
    #         channel = self.bot.get_channel(self.image_message_channel_id)
    #         if not channel:
    #             break

    #         # Choose a random image-message combo
    #         combo = random.choice(self.image_message_combos)
    #         try:
    #             # Send the message with the image
    #             file = discord.File(combo["image"], filename=combo["image"].split("/")[-1])
    #             await channel.send(content=combo["message"], file=file)
    #         except Exception as e:
    #             print(f"Failed to send automated image-message: {e}")

    #         # Wait for the next interval
    #         await asyncio.sleep(self.auto_image_message_interval)



async def setup(bot):
    await bot.add_cog(Tasks(bot))