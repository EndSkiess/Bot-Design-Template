import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime


class Snipe(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.sniped_messages = {}

    @commands.Cog.listener()
    async def on_message_delete(self, message):
        """Store deleted messages for sniping"""
        if message.author.bot:
            return
        
        self.sniped_messages[message.channel.id] = {
            'content': message.content,
            'author': message.author,
            'avatar': message.author.display_avatar.url,
            'timestamp': datetime.utcnow()
        }

    @app_commands.command(name="snipe", description="View the last deleted message in this channel")
    async def snipe(self, interaction: discord.Interaction):
        """Show the last deleted message in the channel"""
        channel_id = interaction.channel.id
        
        if channel_id not in self.sniped_messages:
            await interaction.response.send_message("❌ No recently deleted messages to snipe!", ephemeral=True)
            return
        
        data = self.sniped_messages[channel_id]
        
        embed = discord.Embed(
            description=data['content'] if data['content'] else "*[No content]*",
            color=discord.Color.red(),
            timestamp=data['timestamp']
        )
        embed.set_author(name=str(data['author']), icon_url=data['avatar'])
        embed.set_footer(text="Deleted message")
        
        await interaction.response.send_message(embed=embed)


async def setup(bot):
    await bot.add_cog(Snipe(bot))
