
#---------------------GENERAL COMMANDS---------------------#

import aiosqlite
import asyncio
import os
import re
import json
from datetime import datetime, timedelta, timezone

import discord

from discord import app_commands
from discord.ext import commands
from discord.ext import menus, tasks
from discord.ext.commands import Context
from discord.ext.commands.core import has_guild_permissions, has_permissions

from typing import Optional

from helpers import checks
from helpers.database import(
    set_guild_prefix,
    add_automated_message,
    remove_automated_message,
    get_automated_messages,
    get_due_automated_messages,
    update_next_run
    )


from helpers.colors import colors
from helpers.emotes import emotes


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



#--------------------HELP PAGINATION----------------#
class HelpMenu(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=1)

    async def format_page(self, menu, item):
        embed = discord.Embed(title=item[0], description='```' + '\n'.join(item[1]) + '```', color=colors["blue"])
        return embed

class HelpMenuSelect(discord.ui.Select):
    def __init__(self, cogs):
        options = [discord.SelectOption(label='Home', description='Show the homescreen')]
        options += [discord.SelectOption(label=cog, description=f"Lists {cog} commands") for cog in cogs]
        super().__init__(placeholder='Select a cog', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if interaction.user.id != self.view.ctx.author.id:
            return await interaction.response.send_message("Only the author of the original command can interact with this menu.", ephemeral=True)

        cog_name = self.values[0]
        if cog_name == 'Home':
            embed = self.view.get_homescreen_embed()
        else:
            cog = self.view.bot.get_cog(cog_name)
            if cog:
                commands = cog.get_commands()
                data = []
                for command in commands:
                    description = command.description.partition("\n")[0]
                    parameters = []
                    for param in command.clean_params.values():
                        parameters.append(f"<{param.name}>")
                    parameter_info = " ".join(parameters)
                    data.append(f"{command.name} {parameter_info} - {description}")

                cog_description = self.view.bot.get_cog('general').cog_descriptions.get(cog_name, "No description available.")

                embed = discord.Embed(title=f"{cog_name.capitalize()} Commands", description=f"**{cog_description}**\n" + '```' + '\n'.join(data) + '```', color=colors["blue"])
        
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, ctx, cogs):
        super().__init__()
        self.ctx = ctx
        self.bot = ctx.bot
        self.add_item(HelpMenuSelect(cogs))

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Only the author of the original command can interact with this menu.", ephemeral=True)
            return False
        return True

    def get_homescreen_embed(self):
        current_prefix = self.bot.custom_prefixes.get(str(self.ctx.guild.id), '!')
        embed = discord.Embed(
            title = "KiichuBot's Help Menu!",
            description = "It is HIGHLY recommened to enable developer mode when setting up this bot.",
            color=colors["blue"],   
        )
        embed.add_field(name=f"Current Prefix: `{current_prefix}` | Supports Slash Commands", value="This prefix can be changed with the `setprefix` command.", inline=False)
        embed.add_field(name="About me:", value="""I'm KiichuBot, A multipurpose Discord Bot, made by Angryappleseed (<@484856870725484560>). 
                        Please use the dropdown below for help with specific commands.)""", inline=False)
        return embed




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


#--------------------------COMMANDS-------------------------------#
    


class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.cog_descriptions = {
            'general': "Common commands for regular usage.",
            'owner': "Commands that are reserved for the bot owner(s)."
        }
        self.min_account_age_days = 7
        self.log_channel_id = 906624474403717141

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
        # Detect if a user receives headpatters or higher roles and remove fresh meat role
        higher_roles = {HEADPATTERS_ROLE_ID, LIWE_ROLE_ID, PROTECTOR_ROLE_ID, GOD_ROLE_ID}
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
                        description=f"**User: **{after.name} {after.mention}\nUser clicked on the button that tells them NOT TO CLICK ON, but was not kicked due to being headpatters+",
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
                        description=f"**User: **{after.name} {after.mention}\nUser clicked on the button that tells them NOT TO CLICK ON, so they were automatically removed.",
                        color=colors["red"],
                        timestamp=datetime.now()
                    )
                    embed.set_footer(text=f"User ID: {after.id}")
                    await log_channel.send(embed=embed)

                failed_verify_role = discord.utils.get(after.guild.roles, id=FAILED_VERIFY_ROLE_ID)
                if failed_verify_role:
                    await after.remove_roles(failed_verify_role)

                # Adding a short delay before kicking the user
                await asyncio.sleep(2)

                await after.kick(reason="Clicked on Bot Deterrent button.")



#------------NEW ACCOUNT VERIFICATION------------------#
    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        account_age_days = (datetime.now(timezone.utc) - member.created_at).days
        if account_age_days < self.min_account_age_days:
            try:
                await member.send(
                    f"Hello {member.name}, your account is suspected to be an alt in {member.guild.name}. "
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
                    description=f"**User: **{member.name}{member.mention}\nAccount is only {account_age_days} days old. (required age is {self.min_account_age_days} days)",
                    color=colors["red"],
                    timestamp=datetime.now()
                )
                embed.set_footer(text=f"User ID: {member.id}")
                await log_channel.send(embed=embed)




#-------------------- HELP------------------------#

    @commands.hybrid_command(
        name="help", 
        description="Lists all the commands KiichuBot has loaded"
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    async def help(self, ctx):
        included_cogs = ["general", "owner"]
        view = HelpView(ctx, included_cogs)
        embed = view.get_homescreen_embed()
        await ctx.send(embed=embed, view=view)



#---------------------SET PREFIX--------------------#

    @commands.hybrid_command(
        name="setprefix", 
        description="Sets a custom prefix in your server."
    )
    @commands.guild_only()
    @commands.has_permissions(manage_guild=True)
    @checks.not_blacklisted()
    @app_commands.describe(
        prefix="The prefix you wish to set"
    )
    async def setprefix(self, ctx: commands.Context, prefix: str):
        server_id = str(ctx.guild.id)
        await set_guild_prefix(server_id, prefix)
        self.bot.custom_prefixes[server_id] = prefix
        embed = discord.Embed(
            description=f"My prefix has been set to `{prefix}`",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)


#-----------------CHECK CURRENT PREFIX------------------#

    @commands.hybrid_command(
        name="currentprefix",
        description="Checks the current prefix in your server."
    )
    @commands.guild_only()
    @checks.not_blacklisted()
    @checks.is_moderator()
    async def currentprefix(self, ctx: commands.Context):
        server_id = str(ctx.guild.id)
        current_prefix = self.bot.custom_prefixes.get(server_id, self.bot.default_prefix)
        embed = discord.Embed(
            description=f"The current prefix for this server is `{current_prefix}`",
            color=colors["blue"]
        )
        await ctx.send(embed=embed)



#--------------------------------ECHO COMMAND--------------------------------#
        
    @commands.hybrid_command(
        name="echo",
        description="KiichuBot will repeat after you.",
    )
    @checks.not_blacklisted()
    @checks.is_moderator()
    @app_commands.describe(
        channel="The target channel of the message.",
        message="The message you want sent.",
    )
    async def echo(self, context: commands.Context, channel: Optional[discord.TextChannel], *, message: str) -> None:
        if channel:
            await channel.send(message)
            embed = discord.Embed(
                description=f"Message sent to {channel.mention}.",
                color=colors["blue"]
            )
            await context.send(embed=embed)

        else:
            await context.send(message)


#-------------------------ADD AUTO MESSAGE COMMAND--------------------------#

    @commands.hybrid_command(
        name="addautomessage",
        description="Schedules a new automated message."
    )
    @checks.is_moderator()
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
    async def list_automated_messages(self, ctx: commands.Context):
        messages = await get_automated_messages()
        embed = discord.Embed(title="Automated Messages", color=colors["blue"])
        for msg in messages:
            formatted_interval = format_interval(msg[3])
            embed.add_field(name=f"ID: {msg[0]}", value=f"Channel: <#{msg[1]}> - Interval: {formatted_interval}\nMessage: {msg[2]}", inline=False)
        await ctx.send(embed=embed)




#-------------------------REMOVE HEADPATTERS ROLE--------------------------#

    # @commands.hybrid_command(
    #     name="removeheadpatters",
    #     description="Removes Headpatters from Legs I Won't Eat."
    # )
    # @checks.is_moderator()
    # async def remove_headpatters(self, ctx: commands.Context):
    #     guild = ctx.guild
    #     legs_i_wont_eat_role = guild.get_role(781190734954758154)
    #     headpatters_role = guild.get_role(752590175711920198)

    #     if not legs_i_wont_eat_role or not headpatters_role:
    #         embed = discord.Embed(
    #             description="Could not find the specified roles in the server.",
    #             color=colors["red"]
    #         )
    #         await ctx.send(embed=embed)
    #         return

    #     removed_count = 0
    #     for member in guild.members:
    #         if legs_i_wont_eat_role in member.roles and headpatters_role in member.roles:
    #             await member.remove_roles(headpatters_role)
    #             removed_count += 1

    #     embed = discord.Embed(
    #         description=f"Successfully removed the Headpatters role from {removed_count} users who had the Legs I Won't Eat role.",
    #         color=colors["blue"]
    #     )
    #     await ctx.send(embed=embed)



async def setup(bot):
    await bot.add_cog(General(bot))
