
#---------------------GENERAL COMMANDS---------------------#

import json
import discord
import platform

from discord import app_commands
from discord.ext import commands
from discord.ext import menus
from discord.ext.commands import Context
from discord.ext.commands.core import has_guild_permissions, has_permissions

from helpers import checks
from helpers.database import set_guild_prefix


from helpers.colors import colors
from helpers.emotes import emotes


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




#--------------------------COMMANDS-------------------------------#
    


class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.cog_descriptions = {
            'general': "Common commands for regular usage.",
            'logging': "Commands for server logging and monitoring.",
            'moderation': "Commands to help moderate your server.",
            'trusted': "Special commands for Trusted users of the bot.",
            'owner': "Commands that are reserved for the bot owner(s)."
        }
#-------------------- HELP------------------------#

    @commands.hybrid_command(
        name="help", 
        description="Lists all the commands KiichuBot has loaded"
    )
    @checks.not_blacklisted()
    async def help(self, ctx):
        included_cogs = ["general", "logging", "moderation", "trusted", "owner"]
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
        description="Algebra will repeat after you",
    )
    @app_commands.describe(
        message="The message that should be repeated by Algebra"
        )
    @checks.is_moderator()
    async def echo(self, context: Context, *, message: str) -> None:
        await context.send(message)





async def setup(bot):
    await bot.add_cog(General(bot))
