
#---------------------MISCELLANEOUS COMMANDS---------------------#

import re
import random
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes

class Miscellaneous(commands.Cog, name="miscellaneous"):
    def __init__(self, bot):
        self.bot = bot



#-----------------------YORU MOT LISTENER---------------------------#
    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        
        normalized_content = re.sub(r"[^\w]", "", message.content.lower())
        pattern = r"yorumot"

        if re.search(pattern, normalized_content, re.IGNORECASE):
            response_options = [
                "Yoru mot!",
                "Yoru mot?!",
                "YORU MOT!",
                f"yoru mot, my beloved {emotes['yorumot']}",
                "Your mere feeble mortal mind is incapable of grasping the true nature of Yoru mot.",
                "Yoru mot to you as well!",
                "y-yoru mot...",
                "Y-yoru mot~",
                "Yo'ru mot reference!",
                f"Yo'ru mot {emotes['yorumot']}",
                f"{emotes['yorumot']}",
                f"yoru mot {emotes['yorumot']}",
            ]
            response = random.choice(response_options)
            await message.channel.send(response)



#--------------------------------ECHO COMMAND--------------------------------#
    @commands.hybrid_command(
        name="echo",
        description="KiichuBot will send your message",
    )
    @app_commands.describe(
        message="The message that should be repeated by KiichuBot"
        )
    @checks.not_blacklisted()
    @checks.is_moderator()
    async def echo(self, context: Context, *, message: str) -> None:
        await context.send(message)




async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
