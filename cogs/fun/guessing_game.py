import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio


class GuessingGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}

    @app_commands.command(name="guess", description="Start a multiplayer number guessing game")
    @app_commands.describe(max_number="Maximum number to guess (default: 100)")
    async def guess(self, interaction: discord.Interaction, max_number: int = 100):
        """Start a multiplayer number guessing mini-game"""
        if max_number < 10:
            await interaction.response.send_message("❌ Maximum number must be at least 10!", ephemeral=True)
            return
        
        if max_number > 10000:
            await interaction.response.send_message("❌ Maximum number cannot exceed 10,000!", ephemeral=True)
            return
        
        channel_id = interaction.channel.id
        
        if channel_id in self.active_games:
            await interaction.response.send_message("❌ There's already an active game in this channel!", ephemeral=True)
            return
        
        number = random.randint(1, max_number)
        self.active_games[channel_id] = {
            'number': number,
            'max': max_number,
            'players': {interaction.user.id: {'name': interaction.user.display_name, 'attempts': 0}},
            'total_attempts': 0,
            'started': False,
            'host': interaction.user.id
        }
        
        embed = discord.Embed(
            title="🎲 Multiplayer Number Guessing Game",
            description=f"**Host:** {interaction.user.mention}\n\nWaiting for players to join...\n\n**How to play:**\n• React with ✅ to join (max 2 players)\n• Type your guess in chat once game starts\n• First to guess correctly wins!",
            color=discord.Color.blue()
        )
        embed.add_field(name="Range", value=f"1 - {max_number}", inline=True)
        embed.add_field(name="Players", value="1/2", inline=True)
        embed.set_footer(text="Game will start automatically when 2 players join or host can start early!")
        
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("✅")
        
        # Store message for later updates
        self.active_games[channel_id]['message'] = message
        
        # Auto-start timer (30 seconds)
        await asyncio.sleep(30)
        if channel_id in self.active_games and not self.active_games[channel_id]['started']:
            await self.start_game(interaction.channel, channel_id)

    @app_commands.command(name="startgame", description="Start the guessing game early (host only)")
    async def start_game_command(self, interaction: discord.Interaction):
        """Start the game early"""
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_games:
            await interaction.response.send_message("❌ No active game in this channel!", ephemeral=True)
            return
        
        game = self.active_games[channel_id]
        
        if interaction.user.id != game['host']:
            await interaction.response.send_message("❌ Only the host can start the game early!", ephemeral=True)
            return
        
        if game['started']:
            await interaction.response.send_message("❌ Game has already started!", ephemeral=True)
            return
        
        await interaction.response.send_message("🎮 Starting game now!", ephemeral=True)
        await self.start_game(interaction.channel, channel_id)

    async def start_game(self, channel, channel_id):
        """Start the game"""
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        if game['started']:
            return
        
        game['started'] = True
        
        players_list = "\n".join([f"• {p['name']}" for p in game['players'].values()])
        
        embed = discord.Embed(
            title="🎮 Game Started!",
            description=f"I'm thinking of a number between **1** and **{game['max']}**!\n\n**Players:**\n{players_list}\n\nType your guesses in chat now!",
            color=discord.Color.green()
        )
        embed.set_footer(text="Type 'quit' to end the game | First correct guess wins!")
        
        await channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle player joins via reactions"""
        if user.bot:
            return
        
        channel_id = reaction.message.channel.id
        
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        
        if game['started']:
            return
        
        if str(reaction.emoji) == "✅":
            if user.id in game['players']:
                return
            
            if len(game['players']) >= 2:
                try:
                    await user.send("❌ Game is already full (2/2 players)!")
                except:
                    pass
                return
            
            game['players'][user.id] = {'name': user.display_name, 'attempts': 0}
            
            # Update embed
            embed = reaction.message.embeds[0]
            embed.set_field_at(1, name="Players", value=f"{len(game['players'])}/2", inline=True)
            await reaction.message.edit(embed=embed)
            
            # Auto-start if 2 players
            if len(game['players']) >= 2:
                await self.start_game(reaction.message.channel, channel_id)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Listen for guesses"""
        if message.author.bot:
            return
        
        channel_id = message.channel.id
        
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        
        if not game['started']:
            return
        
        if message.author.id not in game['players']:
            return
        
        if message.content.lower() == 'quit':
            embed = discord.Embed(
                title="🛑 Game Ended",
                description=f"Game ended by {message.author.mention}. The number was **{game['number']}**.",
                color=discord.Color.red()
            )
            await message.channel.send(embed=embed)
            del self.active_games[channel_id]
            return
        
        try:
            guess = int(message.content)
        except ValueError:
            return
        
        game['players'][message.author.id]['attempts'] += 1
        game['total_attempts'] += 1
        
        if guess < 1 or guess > game['max']:
            await message.channel.send(f"❌ {message.author.mention}, please guess between 1 and {game['max']}!")
            return
        
        if guess < game['number']:
            await message.channel.send(f"📈 {message.author.mention}: Higher!")
        elif guess > game['number']:
            await message.channel.send(f"📉 {message.author.mention}: Lower!")
        else:
            player_attempts = game['players'][message.author.id]['attempts']
            
            embed = discord.Embed(
                title="🎉 We Have a Winner!",
                description=f"**{message.author.mention}** guessed the number **{game['number']}**!",
                color=discord.Color.gold()
            )
            embed.add_field(name="Personal Attempts", value=str(player_attempts), inline=True)
            embed.add_field(name="Total Attempts", value=str(game['total_attempts']), inline=True)
            
            # Show all players' stats
            stats = "\n".join([f"• {p['name']}: {p['attempts']} attempts" for p in game['players'].values()])
            embed.add_field(name="Player Stats", value=stats, inline=False)
            
            await message.channel.send(embed=embed)
            del self.active_games[channel_id]


async def setup(bot):
    await bot.add_cog(GuessingGame(bot))
