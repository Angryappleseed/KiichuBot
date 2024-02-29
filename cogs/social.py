#---------------------SOCIAL COMMANDS---------------------#

import discord
import json
import requests
from discord.ext import commands
from discord.ext.commands import Context, MemberConverter
from discord import app_commands

from helpers import checks
from helpers.database import increment_interaction_count, get_interaction_count
from helpers.colors import colors
from helpers.emotes import emotes


# Logic to fix some past tense actions
def past_tense_action(action):
    irregulars = {
        'slap': 'slapped',
        'pat': 'patted',
        'hug': 'hugged',
        'poke': 'poked',
        'nom': 'nommed',
        'handhold': 'handheld',
        'stare': 'stared',
    }
    if action in irregulars:
        return irregulars[action]
    return action + 'ed'



class Social(commands.Cog, name="social"):
    def __init__(self, bot):
        self.bot = bot
        # Defined in config.json
        self.api_key = bot.config.get("tenor_api_key")
        self.client_key = bot.config.get("tenor_client_key")

    async def interaction(self, context: Context, member: discord.Member, action: str, gif_search_term: str):
        bot_is_target = member == self.bot.user
        if not member:
            await context.send(f"You need to specify a user to {action}.")
            return

        await increment_interaction_count(context.author.id, member.id, action)
        count = await get_interaction_count(member.id, action)

        if bot_is_target:
            bot_responses = {
                'slap': f"Ow... That hurt! Why would you slap me? {emotes['cry']}",
                'pat': f"Headpats? I uh... guess I did a good job, thanks! {emotes['ayaya']}",
                'hug': f"Oh! Okay... I guess a hug doesn't hurt.. {emotes['comfy']}",
                'punch': f"Eh?? I don't know what I did, but I won't do it again... {emotes['cry']}",
                'kiss': f"W-what are you doing!?! {emotes['pout']}",
                'poke': f"*Boops you back* {emotes['peek']}",
                'lick': f"... Disgusting.",
                'kabedon': f"Eh!?! W-w-what are you doing!?!",
                'nom': f"W-what? {emotes['think']}",
                'handhold': f"E-ehhh? Premarital Handholding??",
                'stare': f"*Glares back into the Depths of your soul* {emotes['yorumot']}",
                'tickle': f"S-stop! I'm ticklish! {emotes['ayaya']}",
            }
            action_response = bot_responses.get(action, f"{context.author.display_name} tried to {action} me...")
            counterfooter = f"I have been {past_tense_action(action)} a total of {count} times."
        elif context.author == member:
            action_response = f"{context.author.display_name}... Why would you want to {action} yourself?"
            counterfooter = f"... you need help."
        else:
            past_tense = past_tense_action(action)
            action_response = f"{context.author.display_name} {past_tense} {member.display_name}!"
            counterfooter = f"{member.display_name} has been {past_tense} a total of {count} times."

        gif_url = await self.get_random_gif(gif_search_term)

        if gif_url:
            embed = discord.Embed(
                description=action_response,
                color=colors["blue"],
            )
            #embed.set_author(name=action_response, icon_url=context.author.avatar.url)
            embed.set_image(url=gif_url)
            embed.set_footer(text=counterfooter)
            await context.send(embed=embed)
        else:
            await context.send(f"Sorry, no {gif_search_term} GIFs found. {emotes['cry']}")



    async def get_random_gif(self, search_term):
        lmt = 1
        url = f"https://tenor.googleapis.com/v2/search?q={search_term}&key={self.api_key}&client_key={self.client_key}&limit={lmt}&random=true"

        response = requests.get(url)

        if response.status_code == 200:
            gif_data = json.loads(response.content)
            results = gif_data.get("results", [])
            if results:
                media_formats = results[0].get("media_formats", {})
                if "gif" in media_formats:
                    gif_url = media_formats["gif"]["url"]
                    return gif_url

        return None



#----------------------SLAP-----------------------#
    @commands.hybrid_command(
        name="slap",
        description="Give someone a lil slap",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to slap",
    )
    async def slap(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "slap", "anime slap")


#----------------------PAT-----------------------#
    @commands.hybrid_command(
        name="pat",
        description="Comfort someone with some headpats",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to pat",
    )
    async def pat(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "pat", "anime pat")


#----------------------HUG-----------------------#
    @commands.hybrid_command(
        name="hug",
        description="hug someone to show your appreciation",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to hug",
    )
    async def hug(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "hug", "anime hug")


#----------------------PUNCH-----------------------#
    @commands.hybrid_command(
        name="punch",
        description="Punch someone you despise :D",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to punch",
    )
    async def punch(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "punch", "anime punch")


#----------------------KISS-----------------------#
    @commands.hybrid_command(
        name="kiss",
        description="Gib someone a kiss",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to kiss",
    )
    async def kiss(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "kiss", "anime kiss")


#----------------------POKE-----------------------#
    @commands.hybrid_command(
        name="poke",
        description="Boop someone",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to poke",
    )
    async def poke(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "poke", "anime poke")


#----------------------LICK-----------------------#
    @commands.hybrid_command(
        name="lick",
        description="... Lick someone?",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to lick",
    )
    async def lick(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "lick", "anime lick")


#--------------------KABEDON-----------------------#
    @commands.hybrid_command(
        name="kabedon",
        description="K-Kabedon someone?!",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to kabedon",
    )
    async def kabedon(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "kabedon", "anime kabedon")


#--------------------NOM-----------------------#
    @commands.hybrid_command(
        name="nom",
        description="Nom nom",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to nom",
    )
    async def nom(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "nom", "anime bite")


#--------------------HANDHOLD-----------------------#
    @commands.hybrid_command(
        name="handhold",
        description="P-premarital handholding?! Scandalous!",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to handhold",
    )
    async def handhold(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "handhold", "anime handhold")


#--------------------STARE-----------------------#
    @commands.hybrid_command(
        name="stare",
        description="Stare someone in the eyes.",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to stare at",
    )
    async def stare(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "stare", "anime stare")


#--------------------TICKLE-----------------------#
    @commands.hybrid_command(
        name="tickle",
        description="Give someone some tickles",
    )
    @checks.not_blacklisted()
    @app_commands.describe(
        member="The person you wish to tickle",
    )
    async def tickle(self, context: Context, member: discord.Member = None):
        await self.interaction(context, member, "tickle", "anime tickle")



async def setup(bot):
    await bot.add_cog(Social(bot))