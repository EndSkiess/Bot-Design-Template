import discord
from discord.ext import commands
from discord import app_commands
import aiohttp
import random


class Memes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.subreddits = ['memes', 'dankmemes', 'wholesomememes', 'me_irl']

    @app_commands.command(name="meme", description="Get a random meme from Reddit")
    async def meme(self, interaction: discord.Interaction):
        """Fetch a random meme from Reddit"""
        await interaction.response.defer()
        
        subreddit = random.choice(self.subreddits)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://meme-api.com/gimme/{subreddit}') as response:
                    if response.status != 200:
                        await interaction.followup.send("❌ Failed to fetch meme. Try again later!")
                        return
                    
                    data = await response.json()
                    
                    if not data.get('url'):
                        await interaction.followup.send("❌ No meme found. Try again!")
                        return
                    
                    embed = discord.Embed(
                        title=data.get('title', 'Random Meme'),
                        color=discord.Color.random()
                    )
                    embed.set_image(url=data['url'])
                    embed.set_footer(text=f"👍 {data.get('ups', 0)} | r/{data.get('subreddit', subreddit)}")
                    
                    if data.get('postLink'):
                        embed.url = data['postLink']
                    
                    await interaction.followup.send(embed=embed)
                    
        except Exception as e:
            await interaction.followup.send(f"❌ An error occurred: {str(e)}")


async def setup(bot):
    await bot.add_cog(Memes(bot))
