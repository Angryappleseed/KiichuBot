
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




class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot):
        self.bot = bot

    async def log_purge(self, channel, moderator, messages):
        logging_cog = self.bot.get_cog('logging')
        if logging_cog:
            await logging_cog.log_purge(channel, moderator, messages)
        else:
            print("Logging cog not found - Cannot log purged messages.")



#-------------------------REACTION HANDLER-------------------------#
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        # ensure the reaction is in a valid voting message
        if reaction.message.id in self.bot.active_ban_votes and not user.bot:
            vote_data = self.bot.active_ban_votes[reaction.message.id]

            # check if the user hasn't already voted
            if user.id not in vote_data['votes']:
                vote_data['votes'].append(user.id)

                # if there are 2 votes (initiator + 1 more), ban
                if len(vote_data['votes']) >= 2:
                    context = await self.bot.get_context(reaction.message)
                    await self.ban_user(context, vote_data['user_to_ban'], vote_data['reason'])

                    # remove the vote tracking
                    del self.bot.active_ban_votes[reaction.message.id]


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
                    description=f"**User: ** {user.name}{user.mention}\n**Responsible Mod: **{context.author}",
                    color=colors["blue"],
                    timestamp=datetime.now()
                )
                avatar_url = member.avatar.url if member.avatar else None
                embed.set_author(name=member.display_name, icon_url=avatar_url)
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
                description=f"{user_to_ban} {user_to_ban.mention} was banned by **{context.author}**! {emotes['comfy']}",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            embed.add_field(name="Reason:", value=reason)
            avatar_url = member.avatar.url if member.avatar else None
            embed.set_author(name=member.display_name, icon_url=avatar_url)
            embed.set_footer(text=f"User ID: {member.id}")
            await context.send(embed=embed)

            # ban user
            await member.ban(reason=reason)

        except Exception as e:
            embed = discord.Embed(
                title="Error!",
                description=f"An error occurred while trying to ban the user. {emotes['think']} Make sure my role is above the role of the user you want to ban.",
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
        description="Unbans a user from the server.",
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
                description=f"{user.mention} **({user})** has been unbanned by **{context.author}**!",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            avatar_url = user.avatar.url if user.avatar else None
            embed.set_author(name=user.display_name, icon_url=avatar_url)
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
        description="Adds a warning to a member.",
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
            description=f"{user.mention} **({user})** was warned by **{context.author}**!\nTotal warns for this user: {total} {emotes['comfy']}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        avatar_url = member.avatar.url if member.avatar else None
        embed.set_author(name=member.display_name, icon_url=avatar_url)
        embed.set_footer(text=f"User ID: {member.id}")
        embed.add_field(name="Reason:", value=reason)
        await context.send(embed=embed)


#-----------------------REMOVE WARN-----------------------#
            
    @commands.hybrid_command(
        name="removewarn",
        description="Removes warning from a member.",
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
            description=f"I removed the warning **#{warn_id}** from **{member}**!\nTotal warns for this user: {total} {emotes['comfy']}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        avatar_url = member.avatar.url if member.avatar else None
        embed.set_author(name=member.display_name, icon_url=avatar_url)
        embed.set_footer(text=f"User ID: {member.id}")
        await context.send(embed=embed)


#-------------------------LIST WARNS-------------------------#
    @commands.hybrid_command(
        name="warns",
        description="Shows the warnings of a member.",
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
        avatar_url = user.avatar.url if user.avatar else None
        embed.set_author(name=user.display_name, icon_url=avatar_url)
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
        description="Unmutes a user by removing the jailed role."
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
                description=f"{user.mention} has been manually unmuted by {context.author.mention}.",
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
            # convert duration string to seconds
            time_units = {
                'm': 60,
                'min': 60,
                'h': 3600,
                'hr': 3600,
                'd': 86400,
                'day': 86400
            }
            if duration[-1] in time_units:
                try:
                    time_amount = int(duration[:-1])
                    return time_amount * time_units[duration[-1]]
                except ValueError:
                    return None
            return None





#-------------------------PURGE------------------------------#
    @commands.hybrid_command(
        name="purge",
        description="Delete a number of messages.",
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



async def setup(bot):
    await bot.add_cog(Moderation(bot))
