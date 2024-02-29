
#---------------------OWNER COMMANDS---------------------#
import json

from datetime import datetime
import discord
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks, database
from helpers.colors import colors
from helpers.emotes import emotes


class Owner(commands.Cog, name="owner"):
    def __init__(self, bot):
        self.bot = bot



#---------------------SYNC HYBRID COMMANDS-------------------#
    @commands.command(
        name="sync",
        description="Synchonizes the slash commands.",
    )
    @app_commands.describe(scope="The scope of the sync. Can be `global` or `guild`")
    @checks.is_owner()
    async def sync(self, context: Context, scope: str) -> None:
        if scope == "global":
            await context.bot.tree.sync()
            embed = discord.Embed(
                description=f"Slash commands have been globally synchronized. {emotes['comfy']}",
                color=colors["blue"],
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.copy_global_to(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been synced in this guild.",
                color=colors["blue"],
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=colors["red"]
        )
        await context.send(embed=embed)




#-----------------------UNSYNC HYBRID COMMANDS--------------------------#
    @commands.command(
        name="unsync",
        description="Unsynchonizes the slash commands.",
    )
    @app_commands.describe(
        scope="The scope of the sync. Can be `global`, `current_guild` or `guild`"
    )
    @checks.is_owner()
    async def unsync(self, context: Context, scope: str) -> None:
        if scope == "global":
            context.bot.tree.clear_commands(guild=None)
            await context.bot.tree.sync()
            embed = discord.Embed(
                description=f"Slash commands have been globally unsynchronized. {emotes['comfy']}",
                color=colors["blue"],
            )
            await context.send(embed=embed)
            return
        elif scope == "guild":
            context.bot.tree.clear_commands(guild=context.guild)
            await context.bot.tree.sync(guild=context.guild)
            embed = discord.Embed(
                description="Slash commands have been unsynchronized in this guild.",
                color=colors["blue"],
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description="The scope must be `global` or `guild`.", color=colors["red"]
        )
        await context.send(embed=embed)






#----------------------LOAD A COG--------------------------------#
    @commands.hybrid_command(
        name="load",
        description="Load a cog",
    )
    @app_commands.describe(cog="The name of the cog to load")
    @checks.is_owner()
    async def load(self, context: Context, cog: str) -> None:
        try:
            await self.bot.load_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"Could not load the `{cog}` cog. {emotes['think']}", color=colors["red"]
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully loaded the `{cog}` cog. {emotes['comfy']}", color=colors["blue"]
        )
        await context.send(embed=embed)




#-----------------------UNLOAD A COG-------------------------------#
    @commands.hybrid_command(
        name="unload",
        description="Unloads a cog.",
    )
    @app_commands.describe(cog="The name of the cog to unload")
    @checks.is_owner()
    async def unload(self, context: Context, cog: str) -> None:
        try:
            await self.bot.unload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"Could not unload the `{cog}` cog. {emotes['think']}", color=colors["red"]
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully unloaded the `{cog}` cog. {emotes['comfy']}", color=colors["blue"]
        )
        await context.send(embed=embed)




#-----------------------RELOAD A COG-------------------------------#
    @commands.hybrid_command(
        name="reload",
        description="Reloads a cog.",
    )
    @app_commands.describe(cog="The name of the cog to reload")
    @checks.is_owner()
    async def reload(self, context: Context, cog: str) -> None:
        try:
            await self.bot.reload_extension(f"cogs.{cog}")
        except Exception:
            embed = discord.Embed(
                description=f"Could not reload the `{cog}` cog. {emotes['think']}", color=colors["red"]
            )
            await context.send(embed=embed)
            return
        embed = discord.Embed(
            description=f"Successfully reloaded the `{cog}` cog. {emotes['comfy']}", color=colors["blue"]
        )
        await context.send(embed=embed)



#-----------------------SHUTDOWN THE BOT-------------------------------#
    @commands.hybrid_command(
        name="shutdown",
        description="Shuts Algebra down.",
    )
    @checks.is_owner()
    async def shutdown(self, context: Context) -> None:
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        bot_guild_id = int(config["bot_guild_id"])
        status_channel_id = int(config["status_channel_id"])
        # bot's guild
        self.bot.guild = self.bot.get_guild(bot_guild_id)
        # channel where you want status messages sent
        status_channel = self.bot.get_channel(status_channel_id)

        if status_channel:
            shutdown_embed = discord.Embed(
                title=f"Bye bye! {emotes['cry']}",
                description="Algebra is now offline.",
                color=colors["red"],
                timestamp=datetime.now()
            )
            shutdown_embed.set_author(name="Algebra", icon_url=self.bot.guild.icon.url)
            await status_channel.send(embed=shutdown_embed)
        else:
            self.bot.logger.warning("Status channel not found. Unable to send shutdown embed.")
        embed = discord.Embed(description=f"Shutting down... {emotes['cry']}", color=colors["blue"])
        await context.send(embed=embed)
        await self.bot.close()

    


#-----------------------MANAGE BLACKLISTT-------------------------------#
    @commands.hybrid_group(
        name="blacklist",
        description="Get the list of all blacklisted users.",
    )
    @checks.is_owner()
    async def blacklist(self, context: Context) -> None:
        if context.invoked_subcommand is None:
            embed = discord.Embed(
                description="You need to specify a subcommand.\n\n**Subcommands:**\n`add` - Add a user to the blacklist.\n`remove` - Remove a user from the blacklist.",
                color=colors["red"],
            )
            await context.send(embed=embed)

    @blacklist.command(
        base="blacklist",
        name="show",
        description="Shows the list of all blacklisted users.",
    )
    @checks.is_owner()
    async def blacklist_show(self, context: Context) -> None:
        blacklisted_users = await database.get_blacklisted_users()
        if len(blacklisted_users) == 0:
            embed = discord.Embed(
                description="There are currently no blacklisted users.", color=colors["red"]
            )
            await context.send(embed=embed)
            return

        embed = discord.Embed(title="Blacklisted Users", color=colors["blue"])
        users = []
        for bluser in blacklisted_users:
            user = self.bot.get_user(int(bluser[0])) or await self.bot.fetch_user(
                int(bluser[0])
            )
            users.append(f"• {user.mention} ({user}) - Blacklisted <t:{bluser[1]}>")
        embed.description = "\n".join(users)
        await context.send(embed=embed)

    @blacklist.command(
        base="blacklist",
        name="add",
        description="Lets you add a user from not being able to use the bot.",
    )
    @app_commands.describe(user="The user that should be added to the blacklist")
    @checks.is_owner()
    async def blacklist_add(self, context: Context, user: discord.User) -> None:
        user_id = user.id
        if await database.is_blacklisted(user_id):
            embed = discord.Embed(
                description=f"**{user.name}** is already in the blacklist.",
                color=colors["red"],
            )
            await context.send(embed=embed)
            return
        total = await database.add_user_to_blacklist(user_id)
        embed = discord.Embed(
            description=f"**{user.name}** has been successfully added to the blacklist",
            color=colors["blue"],
        )
        embed.set_footer(
            text=f"There {'is' if total == 1 else 'are'} now {total} {'user' if total == 1 else 'users'} in the blacklist"
        )
        await context.send(embed=embed)

    @blacklist.command(
        base="blacklist",
        name="remove",
        description="Lets you remove a user from not being able to use the bot.",
    )
    @app_commands.describe(user="The user that should be removed from the blacklist.")
    @checks.is_owner()
    async def blacklist_remove(self, context: Context, user: discord.User) -> None:
        user_id = user.id
        if not await database.is_blacklisted(user_id):
            embed = discord.Embed(
                description=f"**{user.name}** is not in the blacklist.", color=colors["red"]
            )
            await context.send(embed=embed)
            return
        total = await database.remove_user_from_blacklist(user_id)
        embed = discord.Embed(
            description=f"**{user.name}** has been successfully removed from the blacklist",
            color=colors["blue"],
        )
        embed.set_footer(
            text=f"There {'is' if total == 1 else 'are'} now {total} {'user' if total == 1 else 'users'} in the blacklist"
        )
        await context.send(embed=embed)
    






#--------------------------SET STATUS---------------------------------#
    @commands.hybrid_command(name="setstatus", description="Changes Algebra's status.")
    @checks.is_owner()
    @app_commands.describe(
        presence="online, idle, or dnd",
        status="The status you want displayed"
        )
    async def set_status(self, context: Context, presence: str, *, status: str) -> None:
        valid_presences = {
            "online": discord.Status.online,
            "idle": discord.Status.idle,
            "dnd": discord.Status.dnd,
        }

        if presence.lower() not in valid_presences:
            embed = discord.Embed(
                description="Invalid presence type. Available options: 'online', 'idle', 'dnd'.",
                color=colors["red"],
            )
            await context.send(embed=embed)
            return

        await self.bot.change_presence(
            status=valid_presences[presence.lower()],
            activity=discord.Game(name=status)
        )

        embed = discord.Embed(
            description=f"My presence has been set!. Presence: {presence.capitalize()}, Status: {status} {emotes['comfy']}",
            color=colors["blue"],
        )
        await context.send(embed=embed)

    




async def setup(bot):
    await bot.add_cog(Owner(bot))