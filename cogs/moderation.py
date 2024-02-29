
#---------------------MODERATION COMMANDS---------------------#

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from datetime import datetime


from helpers import checks, database
from helpers.colors import colors
from helpers.emotes import emotes




class Moderation(commands.Cog, name="moderation"):
    def __init__(self, bot):
        self.bot = bot

    async def log_purge(self, channel, moderator, messages):
        logging_cog = self.bot.get_cog('logging')
        if logging_cog:
            await logging_cog.log_purge(channel, moderator, messages)
        else:
            print("Logging cog not found - Cannot log purged messages.")



#--------------------KICK---------------------#
    @commands.hybrid_command(
        name="kick",
        description="Kick a user out of the server.",
    )
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_permissions(kick_members=True)
    @checks.not_blacklisted()
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
                    description=f"{user.mention} **({user})** was kicked by **{context.author}**!",
                    color=colors["blue"],
                    timestamp=datetime.now()
                )
                avatar_url = member.avatar.url if member.avatar else None
                embed.set_author(name=member.display_name, icon_url=avatar_url)
                embed.set_footer(text=f"User ID: {member.id}")
                embed.add_field(name="Reason:", value=reason)
                await context.send(embed=embed)
                try:
                    await member.send(
                        f"You were kicked by **{context.author}** from **{context.guild.name}**!\nReason: {reason}"
                    )
                except:
                    pass
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
        description="Bans a user from the server.",
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @checks.not_blacklisted()
    @app_commands.describe(
        user="The user that should be banned.",
        reason="The reason why the user should be banned.",
    )
    async def ban(
        self, context: Context, user: discord.User, *, reason: str = "Not specified") -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        try:
            if member.guild_permissions.administrator:
                embed = discord.Embed(
                    description="User has administrator permissions.", color=colors["red"]
                )
                await context.send(embed=embed)
            else:
                embed = discord.Embed(
                    title="Banned Member!",
                    description=f"{user.mention} **({user})** was banned by **{context.author}**!",
                    color=colors["blue"],
                    timestamp=datetime.now()
                )
                embed.add_field(name="Reason:", value=reason)
                avatar_url = member.avatar.url if member.avatar else None
                embed.set_author(name=member.display_name, icon_url=avatar_url)
                embed.set_footer(text=f"User ID: {member.id}")
                await context.send(embed=embed)
                try:
                    await member.send(
                        f"You were banned by **{context.author}** from **{context.guild.name}**!\nReason: {reason}"
                    )
                except:
                    pass
                await member.ban(reason=reason)
        except:
            embed = discord.Embed(
                title="Error!",
                description=f"An error occurred while trying to ban the user. {emotes['think']} Make sure my role is above the role of the user you want to ban.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)


#-------------------------------BAN WITH ID------------------------------------#
    @commands.hybrid_command(
        name="idban",
        description="Bans a user using their userID.",
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
    @checks.not_blacklisted()
    @app_commands.describe(
        user_id="The user ID that should be banned.",
        reason="The reason why the user should be banned.",
    )
    async def idban(
        self, context: Context, user_id: str, *, reason: str = "Not specified") -> None:
        try:
            await self.bot.http.ban(user_id, context.guild.id, reason=reason)
            user = self.bot.get_user(int(user_id)) or await self.bot.fetch_user(
                int(user_id)
            )
            embed = discord.Embed(
                title="Banned User!",
                description=f"{user.mention} **({user})** was banned by **{context.author}**!",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            avatar_url = user.avatar.url if user.avatar else None
            embed.set_author(name=user.display_name, icon_url=avatar_url)
            embed.set_footer(text=f"User ID: {user.id}")
            embed.add_field(name="Reason:", value=reason)
            await context.send(embed=embed)
        except Exception as e:
            embed = discord.Embed(
                description=f"An error occurred while trying to ban the user. {emotes['think']} Make sure userID actually exists.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            await context.send(embed=embed)




#--------------------UNBAN---------------------#
    @commands.hybrid_command(
        name="unban",
        description="Unbans a user from the server.",
    )
    @commands.has_permissions(ban_members=True)
    @commands.bot_has_permissions(ban_members=True)
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
            description=f"{user.mention} **({user})** was warned by **{context.author}**!\nTotal warns for this user: {total}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        avatar_url = member.avatar.url if member.avatar else None
        embed.set_author(name=member.display_name, icon_url=avatar_url)
        embed.set_footer(text=f"User ID: {member.id}")
        embed.add_field(name="Reason:", value=reason)
        await context.send(embed=embed)
        try:
            await member.send(
                f"You were warned by **{context.author}** in **{context.guild.name}**!\nReason: {reason}"
            )
        except:
            await context.send(
                f"{member.mention}, you were warned by **{context.author}**!\nReason: {reason}"
            )


#-----------------------REMOVE WARN-----------------------#
            
    @commands.hybrid_command(
        name="removewarn",
        description="Removes warning from a member.",
    )
    @checks.not_blacklisted()
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
            description=f"I removed the warning **#{warn_id}** from **{member}**!\nTotal warns for this user: {total}",
            color=colors["blue"],
            timestamp=datetime.now()
        )
        avatar_url = member.avatar.url if member.avatar else None
        embed.set_author(name=member.display_name, icon_url=avatar_url)
        embed.set_footer(text=f"User ID: {member.id}")
        await context.send(embed=embed)


#-------------------------LIST WARNS-------------------------#
    @commands.hybrid_command(
        name="listwarns",
        description="Shows the warnings of a member.",
    )
    @commands.has_guild_permissions(manage_messages = True)
    @checks.not_blacklisted()
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
                description += f"• Warned by <@{warning[2]}>: **{warning[3]}** (<t:{warning[4]}>) - Warn ID #{warning[5]}\n"
        embed.description = description
        avatar_url = user.avatar.url if user.avatar else None
        embed.set_author(name=user.display_name, icon_url=avatar_url)
        embed.set_footer(text=f"User ID: {user.id}")
        await context.send(embed=embed)




#-------------------------PURGE------------------------------#
    @commands.hybrid_command(
        name="purge",
        description="Delete a number of messages.",
    )
    @commands.has_guild_permissions(manage_messages = True)
    @commands.bot_has_permissions(manage_messages = True)
    @checks.not_blacklisted()
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


#--------------------NICKNAME--------------------#
    @commands.hybrid_command(
        name="nick",
        description="Change the nickname of a member",
    )
    @commands.has_permissions(manage_nicknames = True)
    @commands.bot_has_permissions(manage_nicknames = True)
    @checks.not_blacklisted()
    @app_commands.describe(
        user="The user that should have a new nickname.",
        nickname="The new nickname that should be set.",
    )
    async def nick(
        self, context: Context, user: discord.User, *, nickname: str = None) -> None:
        member = context.guild.get_member(user.id) or await context.guild.fetch_member(
            user.id
        )
        try:
            await member.edit(nick=nickname)
            embed = discord.Embed(
                title="Nickname Changed!",
                description=f"**{user}'s** new nickname is **{nickname}**! {emotes['comfy']}",
                color=colors["blue"],
                timestamp=datetime.now()
            )
            avatar_url = member.avatar.url if member.avatar else None
            embed.set_author(name=member.display_name, icon_url=avatar_url)
            embed.set_footer(text=f"User ID: {member.id}")
            await context.send(embed=embed)
        except:
            embed = discord.Embed(
                description=f"An error occurred while trying to change the nickname of the user. {emotes['think']} Make sure my role is above the role of the user you want to change the nickname.",
                color=colors["red"],
            )
            await context.send(embed=embed)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
