
#---------------------MODERATION COMMANDS---------------------#
import json
import asyncio

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from datetime import datetime


from helpers import checks, database
from helpers.colors import colors
from helpers.emotes import emotes


with open('config.json', 'r') as config_file:
    config = json.load(config_file)

NORI_ROLE_ID = int(config['nori_role_id'])
MOD_ROLE_IDS = config['modRoles']
JAILED_ROLE_ID = int(config['jailed_role_id'])
AUTOMOD_CHANNEL_ID = int(config['automod_channel_id'])
THREE_LEGS_ROLE_ID = 1573821396054843563
TWO_LEGS_ROLE_ID = 1573821395996250282
ONE_LEG_ROLE_ID = 1573821396101103705



class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot):
        self.bot = bot
        self.mute_timers = {}

    async def log_purge(self, channel, moderator, messages):
        logging_cog = self.bot.get_cog('logging')
        if logging_cog:
            await logging_cog.log_purge(channel, moderator, messages)
        else:
            print("Logging cog not found - Cannot log purged messages.")



#-------------------------REACTION HANDLER-------------------------#
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if hasattr(self.bot, 'active_ban_votes') and reaction.message.id in self.bot.active_ban_votes and not user.bot:
            vote_data = self.bot.active_ban_votes[reaction.message.id]

            # Check if the user hasn't already voted
            if user.id not in vote_data['votes']:
                vote_data['votes'].append(user.id)

                # If there are 2 votes (initiator + 1 more), proceed with banning the user
                if len(vote_data['votes']) >= 2:
                    context = await self.bot.get_context(reaction.message)
                    await self.ban_user(context, vote_data['user_to_ban'], vote_data['reason'])

                    # Remove the vote tracking once the ban is completed
                    del self.bot.active_ban_votes[reaction.message.id]

        # ignore other bot messages
        else:
            pass


#--------------------KICK---------------------#
    @commands.hybrid_command(
        name="kick",
        description="Kick a user out of the server.",
    )
    @checks.not_blacklisted()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @checks.is_moderator()
    @app_commands.describe(
        user="The user that should be kicked.",
        reason="The reason why the user should be kicked.",
    )
    async def kick(
        self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        if member.guild_permissions.administrator:
            embed = discord.Embed(
                description="User has administrator permissions.", color=colors["red"]
            )
            await context.send(embed=embed)
        else:
            try:
                embed = discord.Embed(
                    title="Kicked Member!",
                    description=f"**User: **{user.name}{user.mention}\n**Responsible Mod: **{context.author}",
                    color=colors["blue"],
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"User ID: {member.id}")
                embed.add_field(name="Reason:", value=reason)
                await context.send(embed=embed)

                await member.kick(reason=reason)

            except:
                embed = discord.Embed(
                    description="An error occurred while trying to kick the user. Make sure my role is above the role of the user you want to kick.",
                    color=colors["red"],
                    timestamp=datetime.now()
                )
                await context.send(embed=embed)





#---------------------------BAN-----------------------------#
    @commands.hybrid_command(
        name="ban",
        description="Bans a user from the server."
    )
    @checks.not_blacklisted()
    @commands.bot_has_permissions(ban_members=True)
    @checks.is_moderator()
    @commands.guild_only()
    async def ban(self, context: commands.Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(user.id)
        
        if member.guild_permissions.administrator:
            embed = discord.Embed(
                description="User has administrator permissions.", color=colors["red"]
            )
            await context.send(embed=embed)

        else:
            # if nori, start ban vote
            nori_role = context.guild.get_role(NORI_ROLE_ID)
            if nori_role in context.author.roles:
                await self.start_ban_vote(context, user, reason)
            # if other mod, ban regularly
            else:
                await self.ban_user(context, user, reason)

    #-------------------------BAN USER-------------------------#
    async def ban_user(self, context, user_to_ban, reason):
        try:
            member = context.guild.get_member(user_to_ban.id) or await context.guild.fetch_member(user_to_ban.id)
            embed = discord.Embed(
                title="Banned Member!",
                description=f"**Offender: **{user_to_ban}{user_to_ban.mention}\n**Responsible Moderator: **{context.author} {emotes['comfy']}",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            embed.add_field(name="Reason:", value=reason)
            embed.set_footer(text=f"User ID: {member.id}")
            await context.send(embed=embed)

            # ban user
            await member.ban(reason=reason)

        except Exception as e:
            embed = discord.Embed(
                title="Error!",
                description=f"An error occurred while trying to ban the user. {emotes['think']}",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)

    #-------------------------VOTE INITIALIZATION-------------------------#
    async def start_ban_vote(self, context, user_to_ban, reason):
        # create embed for voting
        embed = discord.Embed(
            title="Ban Vote",
            description=f"A vote to ban {user_to_ban.mention} has started. At least 1 more vote is needed to confirm the ban. React with {emotes['this']} to vote.",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        embed.add_field(name="Reason:", value=reason)
        vote_message = await context.send(embed=embed)

        # bot adds reaction for mods to react
        await vote_message.add_reaction(emotes['this']) 

        # track votes
        self.bot.active_ban_votes[vote_message.id] = {
            'initiator': context.author.id,
            'user_to_ban': user_to_ban,
            'reason': reason,
            'votes': [context.author.id],
            'message': vote_message
        }

        # start a 24-hour ttimer
        await self.handle_vote_timeout(vote_message.id)

    #-------------------------VOTE TIMEOUT HANDLER-------------------------#
    async def handle_vote_timeout(self, message_id):
        await asyncio.sleep(86400)

        # If 24 hours and no votes
        if message_id in self.bot.active_ban_votes:
            vote_data = self.bot.active_ban_votes[message_id]
            message = vote_data['message']

            embed = discord.Embed(
                title="Ban Vote Expired",
                description=f"The vote to ban {vote_data['user_to_ban'].mention} has expired due to insufficient votes. {emotes['ded']}",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await message.channel.send(embed=embed)

            # remove the vote from active votes
            del self.bot.active_ban_votes[message_id]



#--------------------UNBAN---------------------#
    @commands.hybrid_command(
        name="unban",
        description="Unbans user from server.",
    )
    @checks.not_blacklisted()
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @checks.is_moderator()
    @app_commands.describe(
        user_id="The ID of the user that should be unbanned.",
        reason="The reason why the user should be unbanned.",
    )
    async def unban(
        self, context: Context, user_id: str, *, reason: str = "Not specified") -> None:
        try:
            user_id_int = int(user_id)
        except ValueError:
            embed = discord.Embed(
                description="Invalid user ID format. Please provide a valid user ID.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        try:
            user = None
            async for ban_entry in context.guild.bans():
                if ban_entry.user.id == user_id_int:
                    user = ban_entry.user
                    break

            if user is None:
                embed = discord.Embed(
                    description="User not found in the ban list.",
                    color=colors["red"],
                    timestamp=datetime.now()
                )
                await context.send(embed=embed)
                return
            await context.guild.unban(user, reason=reason)

            embed = discord.Embed(
                title="Unbanned User!",
                description=f"**User: **{user}{user.mention}\n**Responsible Moderator: ** {context.author}",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"User ID: {user.id}")
            embed.add_field(name="Reason:", value=reason)
            await context.send(embed=embed)

            try:
                await user.send(
                    f"You have been unbanned from **{context.guild.name}** by **{context.author}**!\nReason: {reason}"
                )
            except:
                pass

        except Exception as e:
            embed = discord.Embed(
                title="Error!",
                description=f"An error occurred while trying to unban the user. {str(e)}",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)





#--------------------WARN---------------------------------#
    @commands.hybrid_command(
        name="warn",
        description="Adds warn to a user.",
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The user that should be warned.",
        reason="The reason why the user should be warned.",
    )
    async def addwarn(
        self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        total = await database.add_warn(
            user.id, context.guild.id, context.author.id, reason
        )
        embed = discord.Embed(
            title="Warned Member!",
            description=f"**Offender: **{user}{user.mention}\n**Responsible Moderator: **{context.author}!\nTotal warns for this user: {total} {emotes['comfy']}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"User ID: {member.id}")
        embed.add_field(name="Reason:", value=reason)

        dm_sent = True
        try:
            await member.send(
                f"You were warned in **{context.guild.name}**!\nReason: {reason}"
            )
        except (discord.Forbidden, discord.HTTPException):
            dm_sent = False

        if not dm_sent:
            embed.add_field(
                name="DM Status",
                value="Could not DM this user (DMs closed or bot blocked perhaps)",
                inline=False
            )

        await context.send(embed=embed)


#-----------------------REMOVE WARN-----------------------#
            
    @commands.hybrid_command(
        name="removewarn",
        description="Removes warn from user.",
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    @commands.has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The user that should get their warning removed.",
        warn_id="The ID of the warning that should be removed.",
    )
    async def removewarn(
        self, context: Context, user: discord.User, warn_id: int) -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        total = await database.remove_warn(warn_id, user.id, context.guild.id)
        embed = discord.Embed(
            title="Removed Warn!",
            description=f"Removed warning **#{warn_id}** from **{member}**!\nTotal warns for this user: {total} {emotes['comfy']}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"User ID: {member.id}")
        await context.send(embed=embed)


#-------------------------LIST WARNS-------------------------#
    @commands.hybrid_command(
        name="warns",
        description="Shows the warnings of a user.",
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    
    @app_commands.describe(user="The user you want to get the warnings of.")
    async def listwarns(self, context: Context, user: discord.User):
        warnings_list = await database.get_warnings(user.id, context.guild.id)
        embed = discord.Embed(title=f"Warnings of {user}",
                              color=colors["blue"],
                              timestamp=datetime.now()
                              )
        description = ""
        if len(warnings_list) == 0:
            description = f"This user has no warnings. {emotes['think']}"
        else:
            for warning in warnings_list:
                description += f"• Warn ID #{warning[5]} - Warned by <@{warning[2]}>: **{warning[3]}** (<t:{warning[4]}>)\n"
        embed.description = description
        embed.set_footer(text=f"User ID: {user.id}")
        await context.send(embed=embed)



#-------------------------MUTE COMMAND-------------------------#
    @commands.hybrid_command(
        name="mute",
        description="Mutes a user with jailed role."
    )
    @checks.not_blacklisted()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.is_moderator()
    @app_commands.describe(
        user="The user to be muted.",
        duration="Duration of the mute ('10min' for 10 minutes, '1hr' for 1 hour)."
    )
    async def mute(self, context: Context, user: discord.Member, duration: str) -> None:
        # Parse duration into seconds
        mute_duration_seconds = self.parse_duration(duration)
        if mute_duration_seconds is None:
            embed = discord.Embed(
                description="Invalid duration format. Please use formats like `10min`, `6hr`, or `2day`.",
                color=colors["red"]
            )
            await context.send(embed=embed)
            return
        
        # Add the jailed role to the user
        jailed_role = context.guild.get_role(JAILED_ROLE_ID)
        if jailed_role in user.roles:
            embed = discord.Embed(
                description=f"{user.mention} is already muted.",
                color=colors["red"]
            )
            await context.send(embed=embed)
            return

        await user.add_roles(jailed_role)

        # send confirmation message in the current channel
        embed = discord.Embed(
            description=f"**Offender:** {user.mention}\n**Duration:** {duration}\n**Responsible Moderator:** {context.author.mention}",
            color=colors["gold"],
            timestamp=datetime.now()
        )
        await context.send(embed=embed)

        # Log mute in the automod channel
        automod_channel = self.bot.get_channel(AUTOMOD_CHANNEL_ID)
        if automod_channel:
            log_embed = discord.Embed(
                title="User Muted",
                description=f"**Offender:** {user.mention}\n**Duration:** {duration}\n**Responsible Moderator:** {context.author.mention}",
                color=colors["gold"],
                timestamp=datetime.now()
            )
            log_embed.set_footer(text=f"User ID: {user.id}")
            await automod_channel.send(embed=log_embed)

        # schedule the automatic unmute
        self.mute_timers[user.id] = self.bot.loop.create_task(self.unmute_after(context, user, mute_duration_seconds))

    #-------------------UNMUTE AFTER TIMER--------------------#
    async def unmute_after(self, context: Context, user: discord.Member, duration: int):
        await asyncio.sleep(duration)

        # check if the user is still muted (i.e., has the jailed role)
        jailed_role = context.guild.get_role(JAILED_ROLE_ID)
        if jailed_role in user.roles:
            await user.remove_roles(jailed_role)

            # Log automatic unmute in the automod channel
            automod_channel = self.bot.get_channel(AUTOMOD_CHANNEL_ID)
            if automod_channel:
                embed = discord.Embed(
                    title="User Automatically Unmuted",
                    description=f"{user.mention} has been automatically unmuted.",
                    color=colors["blue"],
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"User ID: {user.id}")
                await automod_channel.send(embed=embed)



    #-------------------------UNMUTE COMMAND-------------------------#
    @commands.hybrid_command(
        name="unmute",
        description="Removes the jailed role."
    )
    @checks.not_blacklisted()
    @commands.bot_has_permissions(manage_roles=True)
    @checks.is_moderator()
    @app_commands.describe(
        user="The user to be unmuted."
    )
    async def unmute(self, context: Context, user: discord.Member) -> None:
        # Remove the jailed role from the user
        jailed_role = context.guild.get_role(JAILED_ROLE_ID)
        if jailed_role not in user.roles:
            embed = discord.Embed(
                description=f"{user.mention} is not muted.",
                color=colors["red"]
            )
            await context.send(embed=embed)
            return

        await user.remove_roles(jailed_role)

        # Send confirmation message
        embed = discord.Embed(
            description=f"{user.mention} has been unmuted by {context.author.mention}.",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        await context.send(embed=embed)

        # Log unmute in the automod channel
        automod_channel = self.bot.get_channel(AUTOMOD_CHANNEL_ID)
        if automod_channel:
            log_embed = discord.Embed(
                title="User Unmuted",
                description=f"**Offender:** {user.mention}\n**Responsible Moderator: **{context.author.mention}.",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            log_embed.set_footer(text=f"User ID: {user.id}")
            await automod_channel.send(embed=log_embed)

        # Cancel any existing mute timer
        if user.id in self.mute_timers:
            self.mute_timers[user.id].cancel()
            del self.mute_timers[user.id]


    def parse_duration(self, duration: str):
        # Define time units and full word alternatives
        time_units = {
            'm': 60,
            'min': 60,
            'h': 3600,
            'hr': 3600,
            'd': 86400,
            'day': 86400
        }

        # Check if the duration ends with a known unit or word
        for unit, seconds in time_units.items():
            if duration.endswith(unit):
                try:
                    time_amount = int(duration.rstrip(unit))
                    return time_amount * seconds
                except ValueError:
                    return None
        return None





#-------------------------PURGE------------------------------#
    @commands.hybrid_command(
        name="purge",
        description="Delete a bunch of messages.",
    )
    @checks.not_blacklisted()
    @commands.has_guild_permissions(manage_messages = True)
    @commands.bot_has_permissions(manage_messages = True)
    @checks.is_moderator()
    @app_commands.describe(amount="The amount of messages that should be deleted.")
    async def purge(self, context: Context, amount: int) -> None:
        await context.send("Deleting messages...")
        to_be_deleted = [message async for message in context.channel.history(limit=amount + 2)]
        to_be_deleted = to_be_deleted[::-1]
        await self.log_purge(context.channel, context.author, to_be_deleted[:-1]) 
        await context.channel.purge(limit=amount + 2)
        
        embed = discord.Embed(
            title="Messages Purged!",
            description=f"**{context.author}** cleared **{amount}** messages! {emotes['comfy']}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        await context.channel.send(embed=embed, delete_after=3)


#-------------------------VELZ PURGE (user-targeted)-------------------------#

    class VelzPurgeConfirmView(discord.ui.View):
        def __init__(self, author_id: int, target: discord.Member, amount: int, timeout: float = 60):
            super().__init__(timeout=timeout)
            self.author_id = author_id
            self.target = target
            self.amount = amount
            self.value = None  # True = proceed, False = cancel

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user.id != self.author_id:
                await interaction.response.send_message(
                    "Only the moderator who ran this command can decide their fate.",
                    ephemeral=True
                )
                return False
            return True

        @discord.ui.button(label="Proceed, I agree.", style=discord.ButtonStyle.danger)
        async def proceed(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = True
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()

        @discord.ui.button(label="CANCEL! I fucked UP!", style=discord.ButtonStyle.secondary)
        async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
            self.value = False
            for child in self.children:
                child.disabled = True
            await interaction.response.edit_message(view=self)
            self.stop()

        async def on_timeout(self):
            for child in self.children:
                child.disabled = True

    @commands.hybrid_command(
        name="velzpurge",
        description="Delete a set number of a specific user's messages across the server."
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    @commands.has_guild_permissions(manage_messages=True)
    @commands.bot_has_permissions(manage_messages=True)
    @app_commands.describe(
        user="The user whose messages should be deleted.",
        amount="How many of that user's messages to delete (newest first)."
    )
    async def velzpurge(self, context: Context, user: discord.Member, amount: int) -> None:
        if amount < 1:
            embed = discord.Embed(
                description="Amount must be at least 1.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        if amount > 100:
            embed = discord.Embed(
                description="Are you SURE you didnt put the UserID in the wrong spot?",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        confirm_embed = discord.Embed(
            title="Velz Purge Confirmation",
            description=(
                f"You are attempting to delete the last **{amount}** of **{user}** {user.mention}'s messages "
                f"**across the entire server**.\n\n"
                f"**Are YOU SURE THIS IS CORRECT?**\n"
                f"Do you accept all responsibility for attempting to use this command and any "
                f"potential ramifications for any improper usage?"
            ),
            color=colors["gold"],
            timestamp=datetime.now()
        )
        confirm_embed.set_footer(text=f"Target User ID: {user.id}")

        view = self.VelzPurgeConfirmView(context.author.id, user, amount)
        prompt = await context.send(embed=confirm_embed, view=view)

        await view.wait()

        if view.value is None:
            await prompt.edit(
                embed=discord.Embed(
                    description="Velz purge cancelled — confirmation timed out.",
                    color=colors["red"],
                    timestamp=datetime.now()
                ),
                view=None
            )
            return

        if view.value is False:
            await prompt.edit(
                embed=discord.Embed(
                    description="Velz purge Aborted. No messages were deleted.",
                    color=colors["red"],
                    timestamp=datetime.now()
                ),
                view=None
            )
            return

        await prompt.edit(
            embed=discord.Embed(
                description=(
                    f"Scanning channels/threads for up to **{amount}** messages from {user.mention}...\n"
                    f"This can take a bit. Teka short... Get it? kasi like wait lang sounds like wait long"
                ),
                color=colors["blue"],
                timestamp=datetime.now()
            ),
            view=None
        )

        me = context.guild.me
        found = []

        per_channel_scan = 150
        archived_thread_limit = 25

        async def scan_history(channel):
            perms = channel.permissions_for(me)
            if not (perms.view_channel and perms.read_message_history and perms.manage_messages):
                return
            try:
                async for message in channel.history(limit=per_channel_scan):
                    if message.author.id == user.id:
                        found.append(message)
            except (discord.Forbidden, discord.HTTPException):
                return

        # 1) Text channels + their threads
        for channel in context.guild.text_channels:
            await scan_history(channel)
            await asyncio.sleep(0.15)

            for thread in channel.threads:
                await scan_history(thread)
                await asyncio.sleep(0.1)

            try:
                async for thread in channel.archived_threads(limit=archived_thread_limit):
                    await scan_history(thread)
                    await asyncio.sleep(0.1)
            except (discord.Forbidden, discord.HTTPException):
                pass

            if len(found) >= amount * 5:
                break

        # 2) Forum channels (posts are threads)
        for forum in getattr(context.guild, "forums", []):
            await asyncio.sleep(0.15)

            for thread in forum.threads:
                await scan_history(thread)
                await asyncio.sleep(0.1)

            try:
                async for thread in forum.archived_threads(limit=archived_thread_limit):
                    await scan_history(thread)
                    await asyncio.sleep(0.1)
            except (discord.Forbidden, discord.HTTPException):
                pass

            if len(found) >= amount * 5:
                break

        # 3) Any other active guild threads we might have missed
        for thread in context.guild.threads:
            if any(m.channel.id == thread.id for m in found):
                continue
            await scan_history(thread)
            await asyncio.sleep(0.1)

        if not found:
            await prompt.edit(
                embed=discord.Embed(
                    description=f"No recent messages from {user.mention} were found.",
                    color=colors["red"],
                    timestamp=datetime.now()
                )
            )
            return

        # Newest first, then take only the requested amount
        found.sort(key=lambda m: m.created_at, reverse=True)
        to_delete = found[:amount]

        # Group by channel for delete_messages / logging
        by_channel = {}
        for message in to_delete:
            by_channel.setdefault(message.channel, []).append(message)

        deleted_count = 0
        channels_touched = 0

        for channel, messages in by_channel.items():
            channels_touched += 1
            try:
                await self.log_purge(channel, context.author, messages)
            except Exception:
                pass

            bulk = [
                m for m in messages
                if (datetime.now(m.created_at.tzinfo) - m.created_at).days < 14
            ]
            old = [m for m in messages if m not in bulk]

            # bulk delete needs 2+ messages
            if len(bulk) == 1:
                old.append(bulk.pop())

            if bulk:
                try:
                    await channel.delete_messages(bulk)
                    deleted_count += len(bulk)
                except discord.HTTPException:
                    old.extend(bulk)

            for message in old:
                try:
                    await message.delete()
                    deleted_count += 1
                except (discord.Forbidden, discord.HTTPException):
                    continue

        done_embed = discord.Embed(
            title="Velz Purge Complete",
            description=(
                f"**{context.author}** deleted **{deleted_count}** message(s) "
                f"from **{user}** {user.mention} "
                f"across **{channels_touched}** channel(s)/thread(s)."
            ),
            color=colors["blue"],
            timestamp=datetime.now()
        )
        done_embed.set_footer(text=f"Target User ID: {user.id}")
        await prompt.edit(embed=done_embed)






#-------------------------CRUSH FEMUR-------------------------#

    @commands.hybrid_command(
        name="crushfemur",
        description="MODS CRUSH THEIR FEMURS!!"
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    @commands.bot_has_permissions(manage_roles=True)
    @app_commands.describe(
        user="The femur crushee",
        amount="How many legs to remove. Default is 1."
    )
    async def crushfemur(
        self, context: Context, user: discord.Member, amount: int = 1
    ) -> None:
        if amount not in (1, 2):
            embed = discord.Embed(
                description="Amount must be `1` or `2`.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        three_legs = context.guild.get_role(THREE_LEGS_ROLE_ID)
        two_legs = context.guild.get_role(TWO_LEGS_ROLE_ID)
        one_leg = context.guild.get_role(ONE_LEG_ROLE_ID)

        if not all((three_legs, two_legs, one_leg)):
            embed = discord.Embed(
                description="One or more leg roles could not be found. Check the role IDs.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        # determine current legs (users MIGHT have more than 1 leg role)
        if three_legs in user.roles:
            current = 3
        elif two_legs in user.roles:
            current = 2
        elif one_leg in user.roles:
            current = 1
        else:
            embed = discord.Embed(
                description=f"{user.mention} does not have any leg roles.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        # if on last leg
        if current == 1:
            embed = discord.Embed(
                description=(
                    f"{user.mention} is already on their last leg. "
                    f"There are no more femurs left to crush."
                ),
                color=colors["red"],
                timestamp=datetime.now()
            )
            embed.set_footer(text=f"User ID: {user.id}")
            await context.send(embed=embed)
            return

        # cant remove legs to lower than 1
        remove = min(amount, current - 1)
        new_legs = current - remove

        roles_to_remove = []
        if three_legs in user.roles:
            roles_to_remove.append(three_legs)
        if two_legs in user.roles:
            roles_to_remove.append(two_legs)
        if one_leg in user.roles:
            roles_to_remove.append(one_leg)

        role_to_add = {
            3: three_legs,
            2: two_legs,
            1: one_leg,
        }[new_legs]

        try:
            if roles_to_remove:
                await user.remove_roles(*roles_to_remove, reason=f"crushfemur by {context.author}")
            await user.add_roles(role_to_add, reason=f"crushfemur by {context.author}")
        except discord.Forbidden:
            embed = discord.Embed(
                description=(
                    "I couldn't update that user's roles... I hate you grass"
                ),
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return
        except discord.HTTPException as e:
            embed = discord.Embed(
                description=f"Failed to update roles: {e}",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)
            return

        legs_word = "leg" if new_legs == 1 else "legs"
        removed_word = "femur" if remove == 1 else "femurs"

        embed = discord.Embed(
            title="Femur Crushed!",
            description=(
                f"**Crushee:** {user} {user.mention}\n"
                f"**Responsible Moderator:** {context.author}\n"
                f"**Removed:** {remove} {removed_word}\n"
                f"**Legs remaining:** {new_legs} {legs_word}"
            ),
            color=colors["blue"],
            timestamp=datetime.now()
        )
        embed.set_footer(text=f"User ID: {user.id}")
        await context.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
