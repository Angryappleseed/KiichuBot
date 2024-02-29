
#---------------------FUN COMMANDS---------------------#

import aiohttp
import discord
from discord.ext import commands
from discord.ext.commands import Context
from discord import app_commands

import random

from helpers import checks
from helpers.colors import colors
from helpers.emotes import emotes


#----------------RPS PAGINATION UI-----------------------------#
class Choice(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.value = None

    @discord.ui.button(label="Heads", style=discord.ButtonStyle.blurple)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ):
        self.value = "heads"
        self.stop()

    @discord.ui.button(label="Tails", style=discord.ButtonStyle.blurple)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction):
        self.value = "tails"
        self.stop()

class RockPaperScissors(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(
                label="Scissors", description="You choose scissors.", emoji="✂"
            ),
            discord.SelectOption(
                label="Rock", description="You choose rock.", emoji="🪨"
            ),
            discord.SelectOption(
                label="paper", description="You choose paper.", emoji="🧻"
            ),
        ]
        super().__init__(
            placeholder="Choose...",
            min_values=1,
            max_values=1,
            options=options,
        )

    async def callback(self, interaction: discord.Interaction):
        choices = {
            "rock": 0,
            "paper": 1,
            "scissors": 2,
        }
        user_choice = self.values[0].lower()
        user_choice_index = choices[user_choice]

        bot_choice = random.choice(list(choices.keys()))
        bot_choice_index = choices[bot_choice]

        result_embed = discord.Embed(color=0x9C84EF)
        result_embed.set_author(
            name=interaction.user.name, icon_url=interaction.user.avatar.url
        )

        if user_choice_index == bot_choice_index:
            result_embed.description = f"**It's a draw..**\nI chose {bot_choice}, and you chose {user_choice}."
            result_embed.colour = colors["gold"]
        elif user_choice_index == 0 and bot_choice_index == 2:
            result_embed.description = f"**You won!**\nI chose {bot_choice}, and you chose {user_choice}."
            result_embed.colour = colors["blue"]
        elif user_choice_index == 1 and bot_choice_index == 0:
            result_embed.description = f"**You won!**\nI chose {bot_choice}, and you chose {user_choice}."
            result_embed.colour = colors["blue"]
        elif user_choice_index == 2 and bot_choice_index == 1:
            result_embed.description = f"**You won!**\nI chose {bot_choice}, and you chose {user_choice}."
            result_embed.colour = colors["blue"]
        else:
            result_embed.description = (
                f"**You lost!**\nI chose {bot_choice}, and you chose {user_choice}."
            )
            result_embed.colour = colors["red"]
        await interaction.response.edit_message(
            embed=result_embed, content=None, view=None
        )


class RockPaperScissorsView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(RockPaperScissors())







#
#---------------------------------COMMANDS-------------------------------------#
#
        
class Fun(commands.Cog, name="fun"):
    def __init__(self, bot):
        self.bot = bot

#--------------------------RANDOM FACT------------------------#

    @commands.hybrid_command(name="randomfact", description="Algebra will give a random fact.")
    @checks.not_blacklisted()
    async def randomfact(self, context: Context) -> None:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                "https://uselessfacts.jsph.pl/random.json?language=en"
            ) as request:
                if request.status == 200:
                    data = await request.json()
                    embed = discord.Embed(description=data["text"], color=colors["blue"])
                else:
                    embed = discord.Embed(
                        title="Error!",
                        description="There is something wrong with the API, please try again later",
                        color=colors["red"],
                    )
                await context.send(embed=embed)




#------------------------COINFLIP----------------------------#

    @commands.hybrid_command(
        name="coinflip", description="Gamble and flip a coin :D"
    )
    @checks.not_blacklisted()
    async def coinflip(self, context: Context) -> None:
        buttons = Choice()
        embed = discord.Embed(description="What is your bet?", color=colors["blue"])
        message = await context.send(embed=embed, view=buttons)
        await buttons.wait()
        result = random.choice(["heads", "tails"])
        if buttons.value == result:
            embed = discord.Embed(
                description=f"Let's go! You guessed `{buttons.value}` and it landed on `{result}`.",
                color=colors["blue"],
            )
        else:
            embed = discord.Embed(
                description=f"L\nYou guessed `{buttons.value}` and it landed on `{result}`.",
                color=colors["red"],
            )
        await message.edit(embed=embed, view=None, content=None)




#------------------ROCK PAPER SCISSORS---------------------#

    @commands.hybrid_command(
        name="rps", description="Play rock paper scissors vs Algebra."
    )
    @checks.not_blacklisted()
    async def rock_paper_scissors(self, context: Context) -> None:
        view = RockPaperScissorsView()
        await context.send("Select your weapon of choice", view=view)





#----------------------8 BALL-------------------------#
    @commands.hybrid_command(
        name="8ball",
        description="Ask Algebra a question!",
    )
    @checks.not_blacklisted()
    @app_commands.describe(question="The question you want to ask.")
    async def eight_ball(self, context: Context, *, question: str) -> None:
        answers = [
            "It is certain.",
            "It is appears so.",
            "Somehow it's a yes?.",
            "Without a doubt.",
            "Yes - definitely.",
            "I have decided I feel like saying yes",
            "Most likely.",
            "Yes.",
            "Ugh... you are like totes a scorpio.."
            "The council has spoken: Yes.",
            "mayhaps...",
            "...maybe?",
            "Don't count on it.",
            "My reply is no.",
            "The council has spoken: No.",
            "Very doubtful.",
            "... Is that a joke?",
            "Of course not.",
            "Stop dreaming kid.",
            "No, you're not that guy.",
            "No.",
            "nya~",
            "Y-yes! Of course! hahahaha... totally..",
            "no u",
            "Ask again later.",
            "Mere mortals should not have access to such knowledge of the universe.",
            "Cell service is bad here.. please ask again.",
            "Did someone say sumthin?",
            "Erm.. I am contractually obligated to say no",
            "Erm.. I am contractually obligated to say yes",
            "*muffled scream in the background* Uh... gotta check on something, brb."
        ]
        embed = discord.Embed(
            title=f"{random.choice(answers)}",
            color=colors["blue"],
        )
        embed.set_footer(text=f"The question was: {question}")
        await context.send(embed=embed)




async def setup(bot):
    await bot.add_cog(Fun(bot))
