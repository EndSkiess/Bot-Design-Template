import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional

class HelpDropdown(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="General Overview", description="Introduction to Lilith", emoji="🥀", value="overview"),
            discord.SelectOption(label="Pets & RPG", description="Catch and train your companions", emoji="🐾", value="pets"),
            discord.SelectOption(label="Economy & Wealth", description="Earn and spend Lilith tokens", emoji="💰", value="economy"),
            discord.SelectOption(label="Games & Gambling", description="UNO, Casino, and more", emoji="🎰", value="games"),
            discord.SelectOption(label="Shop & Perks", description="Buy roles, colors, and boosts", emoji="🛒", value="shop"),
            discord.SelectOption(label="Community & Love", description="Marriage and Quotes", emoji="💖", value="community"),
            discord.SelectOption(label="Utility & Safety", description="Server info and moderation", emoji="🛠️", value="utility"),
        ]
        super().__init__(placeholder="Explore Lilith's Modules...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        category = self.values[0]
        embed = self.view.create_embed(category)
        await interaction.response.edit_message(embed=embed, view=self.view)

class HelpView(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=300)
        self.bot = bot
        self.add_item(HelpDropdown())

    def create_embed(self, category: str):
        color = 0x2b2d31 # Lilith's Signature Dark
        
        if category == "overview":
            embed = discord.Embed(
                title="🥀 Lilith Bot - Help Hub",
                description="Welcome to Lilith. I am a premium Discord companion focused on aesthetic immersion, RPG engagement, and server economy.\n\n"
                            "Select a module from the dropdown to view available commands.",
                color=color
            )
            embed.set_author(name="Lilith Development", icon_url=self.bot.user.display_avatar.url)
            embed.add_field(name="✨ Highlight Features", value="• **Pet RPG**: Catch, train, and battle.\n"
                                                              "• **Economy**: High-stakes gambling and work.\n"
                                                              "• **Shop**: Personalize your profile with roles and colors.\n"
                                                              "• **Aesthetic Quotes**: Turn any message into a masterpiece.", inline=False)
            embed.set_footer(text="Developed by Lilith Team | v2.0")

        elif category == "pets":
            embed = discord.Embed(title="🐾 Pets & RPG", color=0x3498DB)
            embed.add_field(name="Management", value="`/pet`, `/pets`, `/viewpets`, `/rename`, `/removepet`", inline=False)
            embed.add_field(name="Actions", value="`/catch`, `/feed`, `/playpet`, `/train`, `/refill`", inline=False)
            embed.add_field(name="Competition", value="`/petbattle`, `/petleaderboard`, `/spawn`", inline=False)

        elif category == "economy":
            embed = discord.Embed(title="💰 Economy & Wealth", color=0xF1C40F)
            embed.add_field(name="Earnings", value="`/daily`, `/work`, `/crime`, `/beg`", inline=False)
            embed.add_field(name="Banking", value="`/balance`, `/give`, `/leaderboard`", inline=False)
            embed.add_field(name="Admin", value="`/setbalance`", inline=False)

        elif category == "games":
            embed = discord.Embed(title="🎰 Games & Casino", color=0xE74C3C)
            embed.add_field(name="Card Games", value="`/uno`, `/play`, `/draw`, `/unohand`", inline=False)
            embed.add_field(name="Casino", value="`/blackjack`, `/slots`, `/roulette`, `/horserace`, `/coinflip`, `/dice`", inline=False)
            embed.add_field(name="Multiplayer", value="`/guess`, `/startgame`, `/trivia`, `/spinwheel`", inline=False)
            embed.add_field(name="Anime Specials", value="`/smashorpass`, `/whatanime`, `/animalfact` / `/meme`", inline=False)

        elif category == "shop":
            embed = discord.Embed(title="🛒 Shop & Perks", color=0x2ECC71)
            embed.add_field(name="Market", value="`/shop`, `/buy [id]`, `/sell [id]`", inline=False)
            embed.add_field(name="Inventory", value="`/inventory`, `/use [id]`", inline=False)

        elif category == "community":
            embed = discord.Embed(title="💖 Community & Love", color=0x9B59B6)
            embed.add_field(name="Marriage", value="`/propose`, `/marriage`, `/divorce`, `/couples`, `/tree`, `/jointbalance`, `/adopt`, `/disown`, `/runaway` ", inline=False)
            embed.add_field(name="Social", value="`/hug`, `/kiss`, `/slap`, `/punch`, `/lick`, `/cuddle`, `/pat`, `/poke`, `/bite`, `/wave`, `/laugh`, `/cry`, `/dance`, `/kill`, `/ship` ", inline=False)

        elif category == "utility":
            embed = discord.Embed(title="🛠️ Utility & Safety", color=0x95A5A6)
            embed.add_field(name="Information", value="`/userinfo`, `/serverinfo`, `/avatar`, `/snipe` ", inline=False)
            embed.add_field(name="Moderation", value="`/ban`, `/unban`, `/tempban`, `/kick`, `/mute`, `/unmute`, `/timeout`, `/removetimeout`, `/purge`, `/restrict`, `/unrestrict`, `/restrictions`, `/giverole` ", inline=False)
            embed.add_field(name="Events", value="`/giveawaycreate`, `/giveawayedit`, `/giveawayend`, `/giveawayreroll` ", inline=False)
            embed.add_field(name="Config", value="`/setup quote`, `/setup uno`, `/setwelcome`, `/setgoodbye`, `/redeem` ", inline=False)

        return embed

class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="help", description="View all available commands for Lilith")
    async def help_command(self, interaction: discord.Interaction):
        """Displays categorized help menu"""
        view = HelpView(self.bot)
        embed = view.create_embed("overview")
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Help(bot))
