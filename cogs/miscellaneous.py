
#---------------------MISCELLANEOUS COMMANDS---------------------#

import re
import random
from discord.ext import commands
from discord.ext.commands import Context

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes

class Miscellaneous(commands.Cog, name="miscellaneous"):
    def __init__(self, bot):
        self.bot = bot

#---------------------------JANE------------------------------#
    @commands.hybrid_command(
        name="jane",
        description="OMG THE MENTALIST",
    )
    @checks.not_blacklisted()
    async def jane(self, context: Context):
        text_responses = [
            "https://tenor.com/view/the-mentalist-simon-baker-patrick-jane-gif-3538979",
            "https://tenor.com/view/patrick-jane-the-mentalist-smile-point-you-gif-16385894",
            "https://tenor.com/view/the-mentalist-patrick-jane-smile-happy-look-gif-16385853",
            "https://tenor.com/view/patrick-jane-the-mentalist-redjohn-behzatc-gif-12434872",
            "https://tenor.com/view/mentalist-patrick-jane-dramatic-gif-18947431",
            "https://tenor.com/view/simon-baker-patrick-jane-maybe-gif-20978632",
            "https://tenor.com/view/the-mentalist-patrick-jane-smiling-grin-gif-16385771",
            "https://tenor.com/view/tea-addicted-meantalist-patrick-jane-gif-5580036",
            "https://tenor.com/view/the-mentalist-patrick-jane-smile-happy-gif-16385800",
            "https://tenor.com/view/the-mentalist-patrick-jane-smile-little-small-gif-16385785",
            "https://tenor.com/view/icecream-patrick-jane-mentalist-funny-gif-5586338"
        ]
        response = random.choice(text_responses)
        await context.send(response)



#--------------------------KFC SPIN--------------------------------#
    @commands.hybrid_command(
        name="kfc",
        description="Chimken Spin!!",
    )
    @checks.not_blacklisted()
    async def kfc(self, context: Context):
        response= "https://media.discordapp.net/attachments/751366936557912066/1035409364552515644/kfcspin.gif"
        await context.send(response)





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



async def setup(bot):
    await bot.add_cog(Miscellaneous(bot))
