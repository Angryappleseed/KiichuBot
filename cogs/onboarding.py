
#---------------------ONBOARDING---------------------#

import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

from helpers.database import( 
    get_welcome_message,
    get_goodbye_message,
    get_welcome_channel,
    add_auto_role,
    remove_auto_role,
    get_auto_roles,
    get_sticky_roles,
    set_sticky_roles
)


from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes

from datetime import datetime

import aiosqlite
import os


class Onboarding(commands.Cog, name="onboarding"):
    def __init__(self, bot):
        self.bot = bot


#--------------------- AUTO-ASSIGN ROLES + MESSAGES------------------------------#
    @commands.Cog.listener()
    async def on_member_join(self, member):
        await assign_auto_roles(member)
        guild_id = str(member.guild.id)
        member_id = str(member.id)
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT welcome_enabled, welcome_message, welcome_channel_id, sticky_roles_enabled FROM onboarding WHERE guild_id = ?",
                (guild_id,),
            )
            row = await cursor.fetchone()
            if row and row[0]:
                welcome_message = row[1]
                if welcome_message:
                    welcome_channel_id = row[2]
                    welcome_channel = member.guild.get_channel(int(welcome_channel_id))
                    if welcome_channel:
                        formatted_message = welcome_message.format(member=member)
                        await welcome_channel.send(formatted_message)
            
            if row and row[3]:
                sticky_roles = await get_sticky_roles(member_id, guild_id)
                if sticky_roles:
                    roles_to_assign = [member.guild.get_role(int(role_id)) for role_id in sticky_roles if member.guild.get_role(int(role_id))]
                    await member.add_roles(*roles_to_assign, reason="Sticky Roles")
        

    @commands.Cog.listener()
    async def on_member_remove(self, member):
        guild_id = str(member.guild.id)
        member_id = str(member.id)
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT goodbye_enabled, goodbye_message, welcome_channel_id, sticky_roles_enabled FROM onboarding WHERE guild_id = ?",
                (guild_id,),
            )
            row = await cursor.fetchone()
            if row:
                if row[3]:
                    role_ids = ",".join([str(role.id) for role in member.roles if not role.is_default()])
                    await set_sticky_roles(member_id, guild_id, role_ids)

                if row[0]:
                    goodbye_message = row[1]
                    if goodbye_message:
                        welcome_channel_id = row[2]
                        welcome_channel = member.guild.get_channel(int(welcome_channel_id))
                        if welcome_channel:
                            formatted_message = goodbye_message.format(member=member)
                            await welcome_channel.send(formatted_message)





#---------------------------ONBOARDING HELP-------------------------#
    @commands.hybrid_command(
        name="onboardinghelp",
        description="Displays tips for setting up Onboarding",
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def onboarding_help(self, ctx: commands.Context):
        embed = discord.Embed(
            title="Onboarding Help", color=colors["blue"]
            )
        embed.add_field(name="Welcome/Goodbye:", value=(
            "To set up the welcome/goodbye messages, first use the command `setwelcomechannel` followed by the channel you want the messages sent to.\n"
            "Next, you can use the command `setwelcome` or `setgoodbye` followed by your desired messages.\n"
            "You can include placeholders in the message to personalize it:\n"
            "- `{member}` will be replaced with the username of new members.\n"
            "- `{member.mention}` will ping the user instead.\n"
            "- `<#channel_id>` will mention a specified channel in the text.\n"
            "- `|n|` will create a newline, and create a paragraph break.\n"
            "**For example:**\n"
            "/setwelcome Welcome, `{member.mention}`! Head over to `<#1128964651909132317>` to get started!`\n"
            "You can also use the togglewelcome/togglegoodbye commands to disable/enable the messages."
        ),
        inline=False
    )
        embed.add_field(name="Autoroles:", value="""To set up auto-roles for new members, use the command `addautorole` followed by pinging the role you want to assign.
                        For example:
                        `/addautorole @Role` 
                        To remove an auto-role, use the command `removeautorole` instead. 
                        To list all auto-roles, use the command `listautoroles`.""", inline=False)
        await ctx.send(embed=embed)



#----------------------SET WELCOME--------------------------#
    @commands.hybrid_command(
        name="setwelcome",
        description="Sets server's welcome message."
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        welcome_message="The message you want the bot to say."
    )
    async def set_welcome_message(self, ctx: commands.Context, *, welcome_message: str):
        welcome_message = welcome_message.replace("|n|", "\n")
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT guild_id FROM onboarding WHERE guild_id = ?",
                (str(ctx.guild.id),),
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE onboarding SET welcome_message = ? WHERE guild_id = ?",
                    (welcome_message, str(ctx.guild.id)),
                )
            else:
                await db.execute(
                    "INSERT INTO onboarding (guild_id, welcome_message) VALUES (?, ?)",
                    (str(ctx.guild.id), welcome_message),
                )
            await db.commit()
        embed = discord.Embed(
            title="Welcome message set successfully!", color=colors["blue"]
        )
        await ctx.send(embed=embed)



#----------------------SET GOODBYE--------------------------#
    @commands.hybrid_command(
        name="setgoodbye", 
        description="Sets server's goodbye message."
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        goodbye_message="The message you want the bot to say."
    )
    async def set_goodbye_message(self, ctx: commands.Context, *, goodbye_message: str):
        goodbye_message = goodbye_message.replace("|n|", "\n")
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT guild_id FROM onboarding WHERE guild_id = ?",
                (str(ctx.guild.id),),
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE onboarding SET goodbye_message = ? WHERE guild_id = ?",
                    (goodbye_message, str(ctx.guild.id)),
                )
            else:
                await db.execute(
                    "INSERT INTO onboarding (guild_id, goodbye_message) VALUES (?, ?)",
                    (str(ctx.guild.id), goodbye_message),
                )
            await db.commit()
        embed = discord.Embed(
            title="Goodbye message set successfully!", color=colors["blue"]
        )
        await ctx.send(embed=embed)

    


#----------------------SET WELCOME CHANNEL--------------------------#
    @commands.hybrid_command(
        name="setwelcomechannel",
        description="Sets server's welcome channel."
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        channel="The channel where you want welcome/goodbye messages."
    )
    async def set_welcome_channel(self, ctx: commands.Context, channel: discord.TextChannel):
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT guild_id FROM onboarding WHERE guild_id = ?",
                (str(ctx.guild.id),),
            )
            row = await cursor.fetchone()
            if row:
                await db.execute(
                    "UPDATE onboarding SET welcome_channel_id = ? WHERE guild_id = ?",
                    (str(channel.id), str(ctx.guild.id)),
                )
            else:
                await db.execute(
                    "INSERT INTO onboarding (guild_id, welcome_channel_id) VALUES (?, ?)",
                    (str(ctx.guild.id), str(channel.id)),
                )
            await db.commit()
        embed = discord.Embed(
            title=f"Welcome channel set to {channel.mention}!", color=colors["blue"]
        )
        await ctx.send(embed=embed)

    
#----------------------TOGGLE WELCOME MESSAGE--------------------------#
    @commands.hybrid_command(
        name="togglewelcome",
        description="Toggles welcome messages on or off."
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def toggle_welcome_message(self, ctx: commands.Context):
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT welcome_enabled FROM onboarding WHERE guild_id = ?",
                (str(ctx.guild.id),),
            )
            row = await cursor.fetchone()
            new_status = not row[0] if row else True
            await db.execute(
                "UPDATE onboarding SET welcome_enabled = ? WHERE guild_id = ?",
                (new_status, str(ctx.guild.id)),
            )
            await db.commit()
        status = "enabled" if new_status else "disabled"
        embed = discord.Embed(
            title=f"Welcome message has been {status}.", color=colors["blue"]
        )
        await ctx.send(embed=embed)

#----------------------TOGGLE GOODBYE MESSAGE--------------------------#
    @commands.hybrid_command(
        name="togglegoodbye",
        description="Toggles goodbye messages on or off."
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def toggle_goodbye_message(self, ctx: commands.Context):
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT goodbye_enabled FROM onboarding WHERE guild_id = ?",
                (str(ctx.guild.id),),
            )
            row = await cursor.fetchone()
            new_status = not row[0] if row else True
            await db.execute(
                "UPDATE onboarding SET goodbye_enabled = ? WHERE guild_id = ?",
                (new_status, str(ctx.guild.id)),
            )
            await db.commit()
        status = "enabled" if new_status else "disabled"
        embed = discord.Embed(
            title=f"Goodbye message has been {status}.", color=colors["blue"]
        )
        await ctx.send(embed=embed)


#----------------------ADD AUTOROLES--------------------------#
    @commands.hybrid_command(
        name="addautorole",
        description="Adds an auto-role for new members.",
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        role="The role you want added to new members"
    )
    async def set_auto_role(self, ctx: commands.Context, role: discord.Role):
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)

        await add_auto_role(guild_id, role_id)
        embed = discord.Embed(
                title="Auto-assigned role added!",
                description=f"{role.mention}", color=colors["blue"]
            )
        await ctx.send(embed=embed)




#---------------------REMOVE AUTOROLES--------------------------#
    @commands.hybrid_command(
        name="removeautorole",
        description="Removes an auto-role for new members.",
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    @app_commands.describe(
        role="The role you want removed from autorrole."
    )
    async def remove_auto_role(self, ctx: commands.Context, role: discord.Role):
        guild_id = str(ctx.guild.id)
        role_id = str(role.id)

        await remove_auto_role(guild_id, role_id)
        embed = discord.Embed(
        title="Auto-assigned role removed!",
        description=f"{role.mention}", color=colors["blue"]
        )
        await ctx.send(embed=embed)



#---------------------LIST AUTOROLES----------------------#
    @commands.hybrid_command(
        name="listautoroles",
        description="Lists all current auto-roles.",
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def list_auto_roles(self, ctx: commands.Context):
        guild_id = str(ctx.guild.id)

        auto_roles = await get_auto_roles(guild_id)
        if auto_roles:
            roles = [ctx.guild.get_role(int(role_id)) for role_id in auto_roles]
            roles_mention = [role.mention for role in roles if role is not None]
            if roles_mention:
                embed = discord.Embed(
                title="Current list of auto-roles:",
                description=f"\n".join(roles_mention), color=colors["blue"]
                )
                await ctx.send(embed=embed)
            else:
                embed = discord.Embed(
                title=f"No auto-roles set.", color=colors["blue"]
                )
                await ctx.send(embed=embed)
        else:
            embed = discord.Embed(
            title=f"No auto-roles set.", color=colors["blue"]
            )
            await ctx.send(embed=embed)



#----------------------TOGGLE STICKY ROLES-----------------------#
    @commands.hybrid_command(
        name="stickyroles",
        description="Toggles sticky roles feature for the server."
    )
    @checks.not_blacklisted()
    @commands.has_permissions(manage_guild=True)
    async def sticky_roles(self, ctx: commands.Context):
        async with aiosqlite.connect("database/database.db") as db:
            cursor = await db.execute(
                "SELECT sticky_roles_enabled FROM onboarding WHERE guild_id = ?",
                (str(ctx.guild.id),),
            )
            row = await cursor.fetchone()
            if row:
                new_status = not row[0]
                await db.execute(
                    "UPDATE onboarding SET sticky_roles_enabled = ? WHERE guild_id = ?",
                    (new_status, str(ctx.guild.id)),
                )
                status_text = "enabled" if new_status else "disabled"
            else:
                await db.execute(
                    "INSERT INTO onboarding (guild_id, sticky_roles_enabled) VALUES (?, ?)",
                    (str(ctx.guild.id), True),
                )
                status_text = "enabled"
            await db.commit()

        embed = discord.Embed(
            title="Sticky Roles",
            description=f"Sticky roles have been {status_text}!",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)





async def assign_auto_roles(member: discord.Member):
    guild_id = str(member.guild.id)
    auto_roles = await get_auto_roles(guild_id)
    
    for role_id in auto_roles:
        role = member.guild.get_role(int(role_id))
        if role:
            await member.add_roles(role)


async def setup(bot):
    await bot.add_cog(Onboarding(bot))
