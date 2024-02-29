
# Algebra Bot v1.1.0
# DEV: Angryappleseed (angryappleseed on discord)
# Last Updated: Januray 5, 2024
# Invite Algebra to your own server:
# https://discordapp.com/oauth2/authorize?&client_id=1073891402108370974&scope=bot+applications.commands&permissions=1532229053686
# Join the Official Algebra Discord Server:
# https://discord.gg/uxj2KBVrep

import aiosqlite
import asyncio
import json
import logging
import os
import sys

import platform
import random

import discord
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Context

import helpers.exceptions as exceptions
from datetime import datetime
from helpers.colors import colors
from helpers.emotes import emotes


# ------------------INTENTS---------------------#

intents = discord.Intents.default()
intents.message_content = True
intents.members = True


# ----------------------------LOAD CONFIG.JSON--------------------------#

if not os.path.isfile(f"{os.path.realpath(os.path.dirname(__file__))}/config.json"):
    sys.exit("'config.json' was not found")
else:
    with open(f"{os.path.realpath(os.path.dirname(__file__))}/config.json") as file:
        config = json.load(file)



# -------------------GET SERVER PREFIXES---------------------------#
        
default_prefix = config["prefix"]
async def get_custom_prefix(bot, message):
    bot_mention = f'<@{bot.user.id}> '
    algebra_prefix = "Algebra "
    prefixes = [algebra_prefix, bot.default_prefix, bot_mention]

    if message.guild is not None:
        server_id = str(message.guild.id)
        custom_prefix = bot.custom_prefixes.get(server_id)
        if custom_prefix:
            prefixes = [custom_prefix]

    return tuple(prefixes)


#----------------------------ALGEBRA BOT-----------------------------#

class AlgebraBot(commands.Bot):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_channel = {} 
        self.update_stats = tasks.loop(hours=24)(self._update_stats)
        self.sync_guilds_db = tasks.loop(hours=6)(self._sync_guilds_db)
    
    #Logs all current guild IDs and Names to database
    async def _sync_guilds_db(self):
        current_guild_ids = {str(guild.id) for guild in self.guilds}
        async with aiosqlite.connect(f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db") as db:
            # Fetch guild ids from database
            async with db.execute("SELECT guild_id FROM bot_guilds") as cursor:
                db_guild_ids = {str(row[0]) for row in await cursor.fetchall()}

            # Remove guilds that are no longer in the bot
            guilds_to_remove = db_guild_ids - current_guild_ids
            for guild_id in guilds_to_remove:
                await db.execute("DELETE FROM bot_guilds WHERE guild_id = ?", (guild_id,))

            # Add or update current guilds
            for guild_id in current_guild_ids:
                guild = self.get_guild(int(guild_id))
                await db.execute("INSERT OR REPLACE INTO bot_guilds (guild_id, guild_name) VALUES (?, ?)", 
                                 (guild_id, guild.name))

            await db.commit()

    # Send guild and user numbers to db
    async def _update_stats(self):
        guild_count = len(self.guilds)
        user_count = sum(len(guild.members) for guild in self.guilds)
        async with aiosqlite.connect(f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db") as db:
            await db.execute("UPDATE bot_stats SET guild_count = ?", (guild_count,))
            await db.execute("UPDATE bot_stats SET user_count = ?", (user_count,))

            if db.total_changes == 0:
                await db.execute("INSERT INTO bot_stats(guild_count, user_count) VALUES (?, ?)", (guild_count, user_count))
            
            await db.commit()





bot = AlgebraBot(command_prefix=get_custom_prefix, 
                 intents=intents, 
                 help_command=None)



bot.default_prefix = default_prefix
bot.custom_prefixes = {}
bot.config = config


#--------------------TERMINAL LOGGING-----------------------------#

class LoggingFormatter(logging.Formatter):
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    gray = "\x1b[38m"
    reset = "\x1b[0m"
    bold = "\x1b[1m"

    COLORS = {
        logging.DEBUG: gray + bold,
        logging.INFO: blue + bold,
        logging.WARNING: yellow + bold,
        logging.ERROR: red,
        logging.CRITICAL: red + bold,
    }

    def format(self, record):
        log_color = self.COLORS[record.levelno]
        format = "(black){asctime}(reset) (levelcolor){levelname:<8}(reset) (green){name}(reset) {message}"
        format = format.replace("(black)", self.black + self.bold)
        format = format.replace("(reset)", self.reset)
        format = format.replace("(levelcolor)", log_color)
        format = format.replace("(green)", self.green + self.bold)
        formatter = logging.Formatter(format, "%Y-%m-%d %H:%M:%S", style="{")
        return formatter.format(record)


logger = logging.getLogger("Algebra")
logger.setLevel(logging.INFO)

console_handler = logging.StreamHandler()
console_handler.setFormatter(LoggingFormatter())

file_handler = logging.FileHandler(filename="discord.log", encoding="utf-8", mode="w")
file_handler_formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", "%Y-%m-%d %H:%M:%S", style="{"
)
file_handler.setFormatter(file_handler_formatter)

logger.addHandler(console_handler)
logger.addHandler(file_handler)
bot.logger = logger






#-------------------------------LOAD DATABASE--------------------------#

async def init_db():
    async with aiosqlite.connect(
        f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
    ) as db:
        with open(
            f"{os.path.realpath(os.path.dirname(__file__))}/database/schema.sql"
        ) as file:
            await db.executescript(file.read())
        await db.commit()





#---------------------------ON READY------------------------------#

@bot.event
async def on_ready():
    
    # Initialize the database
    await init_db()
    # Load server prefixes
    await load_prefixes()
    # send guild and user stats to database
    bot.update_stats.start()
    # Log current guilds
    bot.sync_guilds_db.start()
    
    statuses = ["with your feelings~", "roblox!!", "with angryappleseed", "League of Legends"]
    selected_status = random.choice(statuses)
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name=selected_status)
        )
    bot.logger.info(f"Hi hi! It's {bot.user.name}!")
    bot.logger.info(f"My current version is: {config['version']}!")
    bot.logger.info(f"My status is set to: 'Playing {selected_status}'")
    bot.logger.info(f"Curent discord.py API version: {discord.__version__}")
    bot.logger.info(f"Python version: {platform.python_version()}")
    bot.logger.info(f"Running on: {platform.system()} {platform.release()} ({os.name})")
    if config["sync_commands_globally"]:
        bot.logger.info("Syncing commands globally...")
        await bot.tree.sync()
    print(r"""
    ___    __           __              
   /   |  / /___ ____  / /_  _________ _
  / /| | / / __ `/ _ \/ __ \/ ___/ __ `/
 / ___ |/ / /_/ /  __/ /_/ / /  / /_/ / 
/_/  |_/_/\__, /\___/_.___/_/   \__,_/  
         /____/                        
    """)



    # STARTUP MESSAGES
    bot_guild_id = int(config["bot_guild_id"])
    bot.guild = bot.get_guild(bot_guild_id)
    status_channel_id = int(config["status_channel_id"])
    status_channel = bot.get_channel(status_channel_id)
    if status_channel:
        startup_embed = discord.Embed(title=f"Hey hey! I am up and ready to go! {emotes['wave']}", 
                                      description=f"Algebra is now online. {emotes['comfy']}", 
                                      color=colors["green"], 
                                      timestamp=datetime.now()
                                      )
        startup_embed.set_author(name="Algebra", icon_url=bot.guild.icon.url)
        await status_channel.send(embed=startup_embed)
    else:
        bot.logger.warning("Status channel not found. Unable to send startup and shutdown embeds.")
        







#
#-------------------------------EVENTS LISTENERS--------------------------------#
#




#------------------------ON GUILD JOIN-------------------------#
@bot.event
async def on_guild_join(guild: discord.Guild) -> None:
    welcome_channel = guild.system_channel
    if welcome_channel is not None:
        default_prefix = bot.default_prefix
        welcome_message = f"""I'm Algebra, a multipurpose bot here to assist you.
        Feel free to use my commands to enhance your server experience. 
        My default prefix is set to `{default_prefix}`, but you can change this with the `{default_prefix}setprefix` command.
        You can use `{default_prefix}help` to get started. Have fun! {emotes['comfy']}"""
        embed = discord.Embed(title=f"Hi hi! It's Algebra {emotes['wave']}", 
                              description=welcome_message, 
                              color=colors["blue"]
                              )
        await welcome_channel.send(embed=embed)
    async with aiosqlite.connect(f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db") as db:
        await db.execute("INSERT INTO bot_guilds (guild_id, guild_name) VALUES (?, ?)", (guild.id, guild.name))
        await db.commit()


#------------------------ON GUILD LEAVE-------------------------#
@bot.event
async def on_guild_remove(guild):
    async with aiosqlite.connect(f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db") as db:
        await db.execute("DELETE FROM bot_guilds WHERE guild_id = ?", (guild.id,))
        await db.commit()


#------------------------ON DISCONNECT-------------------------#
@bot.event
async def on_disconnect():
    pass


#---------------------ON COMMAND COMPLETION--------------------#
@bot.event
async def on_command_completion(context: Context) -> None:
    full_command_name = context.command.qualified_name
    split = full_command_name.split(" ")
    executed_command = str(split[0])
    if context.guild is not None:
        bot.logger.info(
            f"Executed {executed_command} command in {context.guild.name} (ID: {context.guild.id}) by {context.author} (ID: {context.author.id})"
        )
    else:
        bot.logger.info(
            f"Executed {executed_command} command by {context.author} (ID: {context.author.id}) in DMs"
        )





# ---------------------------------ERROR HANDLING----------------------------------------#

@bot.event
async def on_command_error(context: Context, error) -> None:

    #-------------------COMMAND ON COOLDOWN------------------------#
    if isinstance(error, commands.CommandOnCooldown):
        minutes, seconds = divmod(error.retry_after, 60)
        hours, minutes = divmod(minutes, 60)
        hours = hours % 24
        embed = discord.Embed(
            description=f"**Please slow down** - You can use this command again in {f'{round(hours)} hours' if round(hours) > 0 else ''} {f'{round(minutes)} minutes' if round(minutes) > 0 else ''} {f'{round(seconds)} seconds' if round(seconds) > 0 else ''}. {emotes['ded']}",
            color=colors["red"],
        )
        await context.send(embed=embed)


    #-------------------USER IS BLACKLISTED------------------------#
    elif isinstance(error, exceptions.UserBlacklisted):
        embed = discord.Embed(
            description=f"You are blacklisted from using the bot! {emotes['ded']}", color=colors["red"]
        )
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"Blacklisted user {context.author} (ID: {context.author.id}) tried to execute a command in the guild {context.guild.name} (ID: {context.guild.id})."
            )
        else:
            bot.logger.warning(
                f"Blacklisted user {context.author} (ID: {context.author.id}) tried to execute a command in the bot's DMs."
            )

    #-------------------USER IS NOT AN OWNER------------------------#
    elif isinstance(error, exceptions.UserNotOwner):
        embed = discord.Embed(
            description=f"You are not the owner of Algebra! {emotes['ded']}", color=colors["red"]
        )
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the guild {context.guild.name} (ID: {context.guild.id})."
            )
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute an owner only command in the bot's DMs."
            )


    #-------------------USER IS NOT TRUSTED------------------------#
    elif isinstance(error, exceptions.UserNotTrusted):
        embed = discord.Embed(
            description=f"You are not a Trusted User of Algebra! {emotes['ded']}", color=colors["red"]
        )
        await context.send(embed=embed)
        if context.guild:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute a trusted-user only command in the guild {context.guild.name} (ID: {context.guild.id})."
            )
        else:
            bot.logger.warning(
                f"{context.author} (ID: {context.author.id}) tried to execute a trusted-user only command in the bot's DMs."
            )


    #--------------------USER LACKS PERMISSIONS------------------#
    elif isinstance(error, commands.MissingPermissions):
        embed = discord.Embed(
            description="You are missing the permission(s) `" + ", ".join(error.missing_permissions) + f"` to execute this command! {emotes['ded']}",
            color=colors["red"],
        )
        await context.send(embed=embed)

    #---------------------BOT LACKS PERMISSIONS------------------#
    elif isinstance(error, commands.BotMissingPermissions):
        embed = discord.Embed(
            description="I am missing the permission(s) `" + ", ".join(error.missing_permissions) + f"` to fully perform this command! {emotes['ded']}",
            color=colors["red"],
        )
        await context.send(embed=embed)

    #-------------------MISSING ARGUMENT------------------#
    elif isinstance(error, commands.MissingRequiredArgument):
        embed = discord.Embed(
            title=f"Error! {emotes['ded']}",
            description=str(error).capitalize(),
            color=colors["red"],
        )
        await context.send(embed=embed)
    else:
        raise error




#
#-------------------------------------------------------------------------------------------
#

#-----------------------------LOAD COGS-------------------------------------#
async def load_cogs() -> None:
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"cogs.{extension}")
                bot.logger.info(f"Loaded extension: '{extension}'")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                bot.logger.error(f"Failed to load extension: {extension}\n{exception}")



#-----------------------------LOAD PREFIXES--------------------------------#
async def load_prefixes() -> None:
    async with aiosqlite.connect(
        f"{os.path.realpath(os.path.dirname(__file__))}/database/database.db"
    ) as db:
        async with db.execute("SELECT * FROM prefixes") as cursor:
            rows = await cursor.fetchall()
            for row in rows:
                bot.custom_prefixes[row[0]] = row[1]



# RUN THE BOT
asyncio.run(init_db())
asyncio.run(load_cogs())
bot.run(config["token"])
