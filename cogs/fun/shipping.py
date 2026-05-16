import discord
from discord.ext import commands
from discord import app_commands
import random


class Shipping(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="ship", description="Calculate ship compatibility between two users")
    @app_commands.describe(
        user1="First user to ship",
        user2="Second user to ship"
    )
    async def shipping(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member):
        """Calculate a random ship percentage between two users"""
        # Generate consistent percentage based on user IDs
        seed = abs(hash(f"{min(user1.id, user2.id)}{max(user1.id, user2.id)}"))
        random.seed(seed)
        percentage = random.randint(0, 100)
        random.seed()  # Reset seed
        
        # Determine ship rating
        if percentage < 20:
            rating = "💔 Incompatible"
            color = discord.Color.dark_gray()
        elif percentage < 40:
            rating = "😐 Neutral"
            color = discord.Color.light_gray()
        elif percentage < 60:
            rating = "🤝 Good Friends"
            color = discord.Color.blue()
        elif percentage < 80:
            rating = "💖 Great Match"
            color = discord.Color.purple()
        else:
            rating = "💘 Perfect Match"
            color = discord.Color.red()
        
        # Create ship name
        name1 = user1.display_name[:len(user1.display_name)//2]
        name2 = user2.display_name[len(user2.display_name)//2:]
        ship_name = name1 + name2
        
        embed = discord.Embed(
            title=f"💕 Ship Calculator",
            description=f"{user1.mention} x {user2.mention}",
            color=color
        )
        embed.add_field(name="Compatibility", value=f"**{percentage}%**", inline=True)
        embed.add_field(name="Rating", value=rating, inline=True)
        embed.add_field(name="Ship Name", value=f"**{ship_name}**", inline=False)
        
        # Progress bar
        filled = int(percentage / 10)
        bar = "█" * filled + "░" * (10 - filled)
        embed.add_field(name="Progress", value=f"`{bar}` {percentage}%", inline=False)
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Shipping(bot))
