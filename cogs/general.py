
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
            title = "Algebra's Help Menu!",
            description = "It is HIGHLY recommened to enable developer mode when setting up this bot.",
            color=colors["blue"],   
        )
        embed.add_field(name=f"Current Prefix: `{current_prefix}` | Supports Slash Commands", value="This prefix can be changed with the `setprefix` command.", inline=False)
        embed.add_field(name="About me:", value="""I'm Algebra, A multipurpose Discord Bot, made by Angryappleseed (<@484856870725484560>). 
                        Please use the dropdown below for help with specific commands.
                        If you need more help, you can join the [AlgebraBot Server](https://discord.gg/uxj2KBVrep)""", inline=False)
        return embed




#--------------------------COMMANDS-------------------------------#
    


class General(commands.Cog, name="general"):
    def __init__(self, bot):
        self.bot = bot
        self.cog_descriptions = {
            'general': "Common commands for regular usage.",
            'fun': "Some fun mini-game commands",
            'music': "Handle music playing and vc activities",
            'social': "Social interaction commands like headpats of hugs.",
            'miscellaneous': "Just random commands.",
            'onboarding': "Commands for handling new members",
            'logging': "Commands for server logging and monitoring.",
            'moderation': "Commands to help moderate your server.",
            'trusted': "Special commands for Trusted users of the bot.",
            'owner': "Commands that are reserved for the bot owner(s)."
        }
#-------------------- HELP------------------------#

    @commands.hybrid_command(
        name="help", 
        description="Lists all the commands Algebra has loaded"
    )
    @checks.not_blacklisted()
    async def help(self, ctx):
        included_cogs = ["general", "fun", "music", "social", "miscellaneous", "onboarding", "logging", "moderation", "trusted", "owner"]
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

#--------------------ABOUT------------------------#

    @commands.hybrid_command(
        name="about",
        description="Get to know a little about Algebra",
    )
    @checks.not_blacklisted()
    async def about(self, context: Context) -> None:
        current_prefix = self.bot.custom_prefixes.get(str(context.guild.id), '!') 
        with open('config.json', 'r') as config_file:
            config = json.load(config_file)
        version = config.get('version', 'Unknown')
        embed = discord.Embed(
            title="Hi hi! I'm Algebra! Let's get to know each other! <:AlgebraWave:1129023384970346516>",
            color=colors["blue"],
        )
        embed.set_author(name="Algebra", icon_url=self.bot.guild.icon.url)
        embed.add_field(name="Owner/Dev:", value="Angryappleseed <@484856870725484560>", inline=True)
        embed.add_field(name="Profile Artist:", value="Marcine <@308615343163703299>", inline=True)
        embed.add_field(name="Current Version", value=version, inline=True)
        embed.add_field(name="Built on:", value=f"Python {platform.python_version()} with discord.py", inline=True)
        embed.add_field(name="Creation Date:", value="Feb 11, 2023", inline=True)

        embed.add_field(
            name="Prefix:",
            value=f"/ (Slash Commands) or `{current_prefix}` for normal commands",
            inline=False,
        )
        await context.send(embed=embed)
 


 #--------------------PING------------------------#

    @commands.hybrid_command(
        name="ping",
        description="Pings Algebra and gets her latency",
    )
    @checks.not_blacklisted()
    async def ping(self, context: Context) -> None:
        embed = discord.Embed(
            title=f"WHO PINGED ME?! {emotes['pout']}",
            description=f"My current latency is {round(self.bot.latency * 1000)}ms.",
            color=colors["blue"],
        )
        await context.send(embed=embed)


#--------------------INVITE------------------------#
    @commands.hybrid_command(
        name="invite",
        description="Get Algebra's link to add her to your server",
    )
    @checks.not_blacklisted()
    async def invite(self, context: Context) -> None:
        embed = discord.Embed(
            description=f"You can invite me to your server by clicking [here](https://discordapp.com/oauth2/authorize?&client_id={self.bot.config['application_id']}&scope=bot+applications.commands&permissions={self.bot.config['permissions']}). {emotes['peek']}",
            color=colors["blue"],
        )
        try:
            await context.author.send(embed=embed)
            await context.send(f"Check your DMs for the invite link {emotes['peek']}")
        except discord.Forbidden:
            await context.send(embed=embed)


#--------------------SERVER-----------------------#

    @commands.hybrid_command(
        name="server",
        description="Get an invite to Algebra's Official Server",
    )
    @checks.not_blacklisted()
    async def server(self, context: Context) -> None:
        embed = discord.Embed(
            description=f"Join Algebra's official server by clicking [here](https://discord.gg/uxj2KBVrep). <:AlgebraPeek:1129024648202440806>",
            color=colors["blue"],
        )
        try:
            await context.author.send(embed=embed)
            await context.send(f"Check your DMs for the invite link {emotes['peek']}")
        except discord.Forbidden:
            await context.send(embed=embed)



async def setup(bot):
    await bot.add_cog(General(bot))
