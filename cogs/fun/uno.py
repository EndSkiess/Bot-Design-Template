import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
import logging
from typing import List, Dict, Optional, Any
from ..utils.ravendb_manager import raven_db
from datetime import datetime, timedelta

logger = logging.getLogger('Lilith.Uno')


class UnoCard:
    """Represents a single UNO card"""
    COLORS = ['Red', 'Blue', 'Green', 'Yellow']
    NUMBERS = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
    ACTIONS = ['Skip', 'Reverse', 'Draw2']
    WILDS = ['Wild', 'WildDraw4']
    
    COLOR_EMOJIS = {
        'Red': '🔴',
        'Blue': '🔵',
        'Green': '🟢',
        'Yellow': '🟡',
        'Wild': '🌈'
    }
    
    def __init__(self, color, value):
        self.color = color
        self.value = value
    
    def __str__(self):
        emoji = self.COLOR_EMOJIS.get(self.color, '⚫')
        return f"{emoji} {self.color} {self.value}"
    
    def can_play_on(self, other_card, current_color):
        """Check if this card can be played on another card"""
        if self.color == 'Wild':
            return True
        if self.color == current_color:
            return True
        if self.value == other_card.value and self.value not in self.WILDS:
            return True
        return False


class UnoGame:
    """Manages a single UNO game instance"""
    
    def __init__(self, channel, host, starting_cards=7):
        self.channel = channel
        self.host = host
        self.starting_cards = min(max(starting_cards, 1), 8)  # Between 1-8
        self.players = {}  # {user_id: {'user': User, 'hand': [cards], 'name': str}}
        self.deck = []
        self.discard_pile = []
        self.current_player_index = 0
        self.direction = 1  # 1 for forward, -1 for reverse
        self.game_started = False
        self.game_message = None
        self.current_color = None
        self.waiting_for_color = False
        self.pending_wild_card = None
        self.game_cancelled = False
        
    def create_deck(self):
        """Create a standard UNO deck"""
        deck = []
        
        # Number cards (0: one of each color, 1-9: two of each color)
        for color in UnoCard.COLORS:
            deck.append(UnoCard(color, '0'))
            for number in UnoCard.NUMBERS[1:]:
                deck.append(UnoCard(color, number))
                deck.append(UnoCard(color, number))
        
        # Action cards (two of each per color)
        for color in UnoCard.COLORS:
            for action in UnoCard.ACTIONS:
                deck.append(UnoCard(color, action))
                deck.append(UnoCard(color, action))
        
        # Wild cards (four of each)
        for _ in range(4):
            deck.append(UnoCard('Wild', 'Wild'))
            deck.append(UnoCard('Wild', 'WildDraw4'))
        
        random.shuffle(deck)
        return deck
    
    def deal_cards(self):
        """Deal cards to all players"""
        for player_data in self.players.values():
            player_data['hand'] = [self.deck.pop() for _ in range(self.starting_cards)]
    
    def draw_card(self, player_id, count=1):
        """Draw cards for a player"""
        drawn = []
        for _ in range(count):
            if not self.deck:
                # Reshuffle discard pile into deck
                if len(self.discard_pile) > 1:
                    self.deck = self.discard_pile[:-1]
                    self.discard_pile = [self.discard_pile[-1]]
                    random.shuffle(self.deck)
                else:
                    # No cards left at all
                    break
            
            card = self.deck.pop()
            self.players[player_id]['hand'].append(card)
            drawn.append(card)
        return drawn
    
    def get_current_player(self):
        """Get the current player's data"""
        player_ids = list(self.players.keys())
        return player_ids[self.current_player_index], self.players[player_ids[self.current_player_index]]
    
    def get_next_player_id(self):
        """Peek at who the next player will be without advancing turn"""
        next_index = (self.current_player_index + self.direction) % len(self.players)
        player_ids = list(self.players.keys())
        return player_ids[next_index]
    
    def next_turn(self):
        """Move to the next player"""
        self.current_player_index = (self.current_player_index + self.direction) % len(self.players)
    
    def can_play_card(self, card):
        """Check if a card can be played"""
        if not self.discard_pile:
            return True
        return card.can_play_on(self.discard_pile[-1], self.current_color)
    
    def get_playable_cards(self, player_id):
        """Get list of playable cards for a player"""
        hand = self.players[player_id]['hand']
        return [card for card in hand if self.can_play_card(card)]
    
    def has_color_in_hand(self, player_id, color):
        """Check if player has any cards of a specific color"""
        hand = self.players[player_id]['hand']
        return any(card.color == color for card in hand if card.color != 'Wild')


class ColorSelectView(discord.ui.View):
    """View for selecting a color after playing a Wild card"""
    
    def __init__(self, game, user_id):
        super().__init__(timeout=60)
        self.game = game
        self.user_id = user_id
        self.selected_color = None
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in view interactions"""
        import logging
        logger = logging.getLogger('Lilith.UnoView')
        logger.error(f"Error in ColorSelectView: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing this action.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred processing this action.", ephemeral=True)
        except:
            pass

    @discord.ui.button(label="Red", style=discord.ButtonStyle.danger, emoji="🔴")
    async def red_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your choice!", ephemeral=True)
            return
        self.selected_color = "Red"
        await interaction.response.send_message(f"✅ Selected color: 🔴 Red", ephemeral=False)
        self.stop()
    
    @discord.ui.button(label="Blue", style=discord.ButtonStyle.primary, emoji="🔵")
    async def blue_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your choice!", ephemeral=True)
            return
        self.selected_color = "Blue"
        await interaction.response.send_message(f"✅ Selected color: 🔵 Blue", ephemeral=False)
        self.stop()
    
    @discord.ui.button(label="Green", style=discord.ButtonStyle.success, emoji="🟢")
    async def green_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your choice!", ephemeral=True)
            return
        self.selected_color = "Green"
        await interaction.response.send_message(f"✅ Selected color: 🟢 Green", ephemeral=False)
        self.stop()
    
    @discord.ui.button(label="Yellow", style=discord.ButtonStyle.secondary, emoji="🟡")
    async def yellow_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This isn't your choice!", ephemeral=True)
            return
        self.selected_color = "Yellow"
        await interaction.response.send_message(f"✅ Selected color: 🟡 Yellow", ephemeral=False)
        self.stop()


class Uno(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # {channel_id: UnoGame}
        self.role_check_task = self.bot.loop.create_task(self.check_expired_roles())

    def cog_unload(self):
        self.role_check_task.cancel()

    async def get_settings(self, guild_id: int) -> Dict[str, Any]:
        """Load UNO settings from RavenDB"""
        return await raven_db.load_document(f"uno_setup/{guild_id}") or {}

    async def save_settings(self, guild_id: int, settings: Dict[str, Any]):
        """Save UNO settings to RavenDB"""
        await raven_db.save_document(f"uno_setup/{guild_id}", settings)


    async def check_expired_roles(self):
        """Background task to remove expired winner roles"""
        await self.bot.wait_until_ready()
        while not self.bot.is_closed():
            try:
                # We need to scan all guilds that have role expirations
                # For simplicity in this implementation, we'll store expirations in a specific document
                expirations = await raven_db.load_document("uno_expirations") or {}
                now = datetime.utcnow().timestamp()
                
                changed = False
                to_remove = []
                
                for entry_id, data in expirations.items():
                    if now >= data['expires_at']:
                        guild = self.bot.get_guild(data['guild_id'])
                        if guild:
                            member = guild.get_member(data['user_id'])
                            role = guild.get_role(data['role_id'])
                            if member and role:
                                try:
                                    await member.remove_roles(role, reason="UNO winner role expired")
                                    logger.info(f"Removed expired UNO role from {member} in {guild}")
                                except Exception as e:
                                    logger.error(f"Failed to remove role from {member}: {e}")
                        
                        to_remove.append(entry_id)
                        changed = True
                
                for entry_id in to_remove:
                    del expirations[entry_id]
                
                if changed:
                    await raven_db.save_document("uno_expirations", expirations)
                    
            except Exception as e:
                logger.error(f"Error in check_expired_roles: {e}")
            
            await asyncio.sleep(60) # Check every minute
    
    @app_commands.command(name="uno", description="Start a game of UNO")
    @app_commands.describe(
        starting_cards="Number of starting cards per player (1-8, default: 7)",
        max_players="Maximum number of players (2-10, default: 10)"
    )
    async def uno(self, interaction: discord.Interaction, starting_cards: int = 7, max_players: int = 10):
        """Start a new UNO game"""
        channel_id = interaction.channel.id
        
        # Check settings
        settings = await self.get_settings(interaction.guild_id)
        if settings.get("channel_id") and settings["channel_id"] != channel_id:
            allowed_channel = self.bot.get_channel(settings["channel_id"])
            await interaction.response.send_message(
                f"❌ UNO can only be played in {allowed_channel.mention if allowed_channel else 'the configured channel'}!",
                ephemeral=True
            )
            return

        # Validate inputs
        if starting_cards < 1 or starting_cards > 8:
            await interaction.response.send_message("❌ Starting cards must be between 1 and 8!", ephemeral=True)
            return
        
        if max_players < 2 or max_players > 10:
            await interaction.response.send_message("❌ Max players must be between 2 and 10!", ephemeral=True)
            return
        
        if channel_id in self.active_games:
            await interaction.response.send_message("❌ There's already an active UNO game in this channel!", ephemeral=True)
            return
        
        # Create game
        game = UnoGame(interaction.channel, interaction.user, starting_cards)
        game.players[interaction.user.id] = {
            'user': interaction.user,
            'hand': [],
            'name': interaction.user.display_name
        }
        
        self.active_games[channel_id] = game
        
        # Create join embed
        embed = discord.Embed(
            title="🎴 UNO Game Starting!",
            description=f"**Host:** {interaction.user.mention}\n\n"
                       f"React with 🎮 to join!\n\n"
                       f"**Settings:**\n"
                       f"• Starting Cards: {starting_cards}\n"
                       f"• Max Players: {max_players}\n"
                       f"• Min Players: 2\n\n"
                       f"Game will start in **60 seconds** or when {max_players} players join!",
            color=discord.Color.red()
        )
        embed.add_field(name="Players", value=f"1/{max_players}", inline=True)
        embed.add_field(name="Status", value="⏳ Waiting", inline=True)
        
        await interaction.response.send_message(embed=embed)
        message = await interaction.original_response()
        await message.add_reaction("🎮")
        
        game.game_message = message
        
        # Start join timer
        asyncio.create_task(self.wait_for_players(channel_id, message, max_players))
    
    async def wait_for_players(self, channel_id, message, max_players):
        """Wait for players to join, then start game"""
        await asyncio.sleep(60)  # 60 second timer
        
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        
        # Check if game already started or cancelled
        if game.game_started or game.game_cancelled:
            return
        
        if len(game.players) < 2:
            embed = discord.Embed(
                title="❌ UNO Game Cancelled",
                description="Not enough players joined (minimum 2 required).",
                color=discord.Color.red()
            )
            await message.edit(embed=embed)
            del self.active_games[channel_id]
            return
        
        # Start the game
        await self.start_game(channel_id)
    
    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        """Handle players joining via reactions"""
        if user.bot:
            return
        
        channel_id = reaction.message.channel.id
        
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        
        if game.game_started or game.game_cancelled:
            return
        
        if str(reaction.emoji) == "🎮":
            # Check if already joined
            if user.id in game.players:
                return
            
            # Check max players (get from embed)
            embed = reaction.message.embeds[0]
            max_players = int(embed.description.split("Max Players: ")[1].split("\n")[0])
            
            if len(game.players) >= max_players:
                try:
                    await user.send("❌ This UNO game is full!")
                except:
                    pass
                return
            
            # Add player
            game.players[user.id] = {
                'user': user,
                'hand': [],
                'name': user.display_name
            }
            
            # Update embed
            embed.set_field_at(0, name="Players", value=f"{len(game.players)}/{max_players}", inline=True)
            await reaction.message.edit(embed=embed)
            
            # Auto-start if max players reached
            if len(game.players) >= max_players:
                game.game_cancelled = True  # Prevent timer from starting it again
                await self.start_game(channel_id)
    
    async def start_game(self, channel_id):
        """Start the UNO game"""
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        
        if game.game_started:
            return
        
        game.game_started = True
        
        # Setup game
        game.deck = game.create_deck()
        game.deal_cards()
        
        # Start discard pile with a number card
        first_card = game.deck.pop()
        while first_card.color == 'Wild' or first_card.value in UnoCard.ACTIONS:
            game.deck.insert(0, first_card)
            first_card = game.deck.pop()
        
        game.discard_pile.append(first_card)
        game.current_color = first_card.color
        
        # Announce start
        players_list = "\n".join([f"{i+1}. {p['name']}" for i, p in enumerate(game.players.values())])
        
        embed = discord.Embed(
            title="🎴 UNO Game Started!",
            description=f"**Players ({len(game.players)}):**\n{players_list}\n\n"
                       f"Game is starting now!",
            color=discord.Color.green()
        )
        
        await game.channel.send(embed=embed)
        
        # Send hands to players
        dm_failed = []
        for player_id, player_data in game.players.items():
            success = await self.send_hand_dm(player_data['user'], player_data['hand'])
            if not success:
                dm_failed.append(player_data['name'])
        
        if dm_failed:
            await game.channel.send(
                f"⚠️ Warning: Couldn't send DMs to: {', '.join(dm_failed)}\n"
                f"Please enable DMs from server members to play!"
            )
        
        # Start first turn
        await self.next_turn(channel_id)
    
    async def send_hand_dm(self, user, hand):
        """Send a player their hand via DM. Returns True if successful."""
        hand_str = "\n".join([f"{i+1}. {card}" for i, card in enumerate(hand)])
        
        embed = discord.Embed(
            title="🎴 Your UNO Hand",
            description=f"**Your Cards ({len(hand)}):**\n{hand_str}\n\n"
                       f"Use `/play <number>` to play a card!\n"
                       f"Use `/draw` to draw a card!",
            color=discord.Color.blue()
        )
        
        try:
            await user.send(embed=embed)
            return True
        except:
            return False
    
    async def next_turn(self, channel_id):
        """Handle the next turn"""
        if channel_id not in self.active_games:
            return
        
        game = self.active_games[channel_id]
        
        # Check for winner
        for player_id, player_data in game.players.items():
            if len(player_data['hand']) == 0:
                await self.end_game(channel_id, player_id)
                return
        
        current_player_id, current_player_data = game.get_current_player()
        current_user = current_player_data['user']
        
        # Show game state
        top_card = game.discard_pile[-1]
        playable = game.get_playable_cards(current_player_id)
        
        embed = discord.Embed(
            title="🎴 UNO - Current Turn",
            description=f"**Current Player:** {current_user.mention}\n\n"
                       f"**Top Card:** {top_card}\n"
                       f"**Current Color:** {UnoCard.COLOR_EMOJIS.get(game.current_color, '⚫')} {game.current_color}\n\n"
                       f"**Playable cards:** {len(playable)}\n"
                       f"Check your DMs for your hand!",
            color=discord.Color.gold()
        )
        
        # Player counts
        player_info = "\n".join([
            f"{'➡️ ' if i == game.current_player_index else ''}{p['name']}: {len(p['hand'])} cards"
            for i, p in enumerate(game.players.values())
        ])
        embed.add_field(name="Players", value=player_info, inline=False)
        embed.set_footer(text="Use /play <card number> or /draw")
        
        await game.channel.send(embed=embed)
        
        # Send updated hand to current player
        await self.send_hand_dm(current_user, current_player_data['hand'])
    
    @app_commands.command(name="play", description="Play a card from your hand")
    @app_commands.describe(card_number="The number of the card to play")
    async def play(self, interaction: discord.Interaction, card_number: int):
        """Play a card"""
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_games:
            await interaction.followup.send("❌ No active UNO game!", ephemeral=True)
            return
        
        game = self.active_games[channel_id]
        
        if not game.game_started:
            await interaction.followup.send("❌ Game hasn't started yet!", ephemeral=True)
            return
        
        # Check if it's player's turn
        current_player_id, _ = game.get_current_player()
        
        if interaction.user.id != current_player_id:
            await interaction.followup.send("❌ It's not your turn!", ephemeral=True)
            return
        
        if interaction.user.id not in game.players:
            await interaction.followup.send("❌ You're not in this game!", ephemeral=True)
            return
        
        # Validate card number
        hand = game.players[interaction.user.id]['hand']
        
        if card_number < 1 or card_number > len(hand):
            await interaction.followup.send(f"❌ Invalid card number! You have {len(hand)} cards.", ephemeral=True)
            return
        
        card = hand[card_number - 1]
        
        # Check if card can be played
        if not game.can_play_card(card):
            await interaction.followup.send("❌ You can't play that card!", ephemeral=True)
            return
        
        # Validate Wild Draw 4 (can only play if no cards of current color)
        if card.value == 'WildDraw4' and game.has_color_in_hand(interaction.user.id, game.current_color):
            await interaction.followup.send(
                "❌ You can't play Wild Draw 4 when you have a card of the current color!",
                ephemeral=True
            )
            return
        
        # Play the card
        hand.pop(card_number - 1)
        game.discard_pile.append(card)
        
        await interaction.followup.send(f"✅ Played: {card}", ephemeral=False)
        
        # Check for UNO before handling special cards
        if len(hand) == 1:
            await game.channel.send(f"🎴 **UNO!** {interaction.user.mention} has 1 card left!")
        
        # Check for winner
        if len(hand) == 0:
            await self.end_game(channel_id, interaction.user.id)
            return
        
        # Handle special cards
        if card.value == 'Skip':
            game.next_turn()
            skipped_player_id, skipped_player_data = game.get_current_player()
            await game.channel.send(
                f"⏭️ {interaction.user.mention} played Skip! "
                f"{skipped_player_data['user'].mention} is skipped."
            )
            
        elif card.value == 'Reverse':
            game.direction *= -1
            await game.channel.send(f"🔄 {interaction.user.mention} played Reverse! Direction changed.")
            
        elif card.value == 'Draw2':
            next_player_id = game.get_next_player_id()
            next_player = game.players[next_player_id]['user']
            drawn = game.draw_card(next_player_id, 2)
            await game.channel.send(
                f"➕2️⃣ {next_player.mention} draws 2 cards and loses their turn!"
            )
            await self.send_hand_dm(next_player, game.players[next_player_id]['hand'])
            game.next_turn()  # Skip the affected player
            
        elif card.value in ['Wild', 'WildDraw4']:
            # Handle Wild Draw 4 effect first
            if card.value == 'WildDraw4':
                next_player_id = game.get_next_player_id()
                next_player = game.players[next_player_id]['user']
                drawn = game.draw_card(next_player_id, 4)
                await game.channel.send(
                    f"➕4️⃣ {next_player.mention} draws 4 cards and loses their turn!"
                )
                await self.send_hand_dm(next_player, game.players[next_player_id]['hand'])
                game.next_turn()  # Skip the affected player
            
            # Now ask for color selection
            view = ColorSelectView(game, interaction.user.id)
            msg = await game.channel.send(
                f"{interaction.user.mention}, choose a color:",
                view=view
            )
            
            # Wait for color selection
            await view.wait()
            
            if view.selected_color:
                game.current_color = view.selected_color
                await msg.edit(content=f"Color changed to {UnoCard.COLOR_EMOJIS[view.selected_color]} {view.selected_color}!", view=None)
            else:
                # Timeout - pick random color
                game.current_color = random.choice(UnoCard.COLORS)
                await msg.edit(
                    content=f"⏱️ Time's up! Random color selected: {UnoCard.COLOR_EMOJIS[game.current_color]} {game.current_color}",
                    view=None
                )
        else:
            # Regular number card
            game.current_color = card.color
        
        # Next turn
        game.next_turn()
        await self.next_turn(channel_id)
    
    @app_commands.command(name="draw", description="Draw a card")
    async def draw(self, interaction: discord.Interaction):
        """Draw a card"""
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_games:
            await interaction.followup.send("❌ No active UNO game!", ephemeral=True)
            return
        
        game = self.active_games[channel_id]
        
        if not game.game_started:
            await interaction.followup.send("❌ Game hasn't started yet!", ephemeral=True)
            return
        
        # Check if it's player's turn
        current_player_id, _ = game.get_current_player()
        
        if interaction.user.id != current_player_id:
            await interaction.followup.send("❌ It's not your turn!", ephemeral=True)
            return
        
        if interaction.user.id not in game.players:
            await interaction.followup.send("❌ You're not in this game!", ephemeral=True)
            return
        
        # Draw card
        drawn = game.draw_card(interaction.user.id, 1)
        
        if not drawn:
            await interaction.followup.send("⚠️ No cards left in deck!", ephemeral=True)
            # Still end turn
            game.next_turn()
            await self.next_turn(channel_id)
            return
        
        drawn_card = drawn[0]
        
        # Check if the drawn card is playable
        if game.can_play_card(drawn_card):
            await interaction.followup.send(
                f"✅ You drew: {drawn_card}\n"
                f"This card is playable! You can play it now or pass.",
                ephemeral=True
            )
        else:
            await interaction.followup.send(
                f"✅ You drew a card (not playable). Your turn ends. Check your DMs.",
                ephemeral=True
            )
            # Send updated hand
            await self.send_hand_dm(interaction.user, game.players[interaction.user.id]['hand'])
            
            # End turn
            game.next_turn()
            await self.next_turn(channel_id)
    
    @app_commands.command(name="unohand", description="View your current hand")
    async def unohand(self, interaction: discord.Interaction):
        """Show the player their hand"""
        await interaction.response.defer(ephemeral=True)
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_games:
            await interaction.followup.send("❌ No active UNO game!", ephemeral=True)
            return
        
        game = self.active_games[channel_id]
        
        if interaction.user.id not in game.players:
            await interaction.followup.send("❌ You're not in this game!", ephemeral=True)
            return
        
        hand = game.players[interaction.user.id]['hand']
        await self.send_hand_dm(interaction.user, hand)
        await interaction.followup.send("✅ Sent your hand to your DMs!", ephemeral=True)
    
    @app_commands.command(name="unocancel", description="Cancel the current UNO game (host only)")
    async def unocancel(self, interaction: discord.Interaction):
        """Cancel the current game"""
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_games:
            await interaction.response.send_message("❌ No active UNO game!", ephemeral=True)
            return
        
        game = self.active_games[channel_id]
        
        # Only host can cancel
        if interaction.user.id != game.host.id:
            await interaction.response.send_message("❌ Only the host can cancel the game!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="❌ UNO Game Cancelled",
            description=f"Game cancelled by {interaction.user.mention}",
            color=discord.Color.red()
        )
        
        await interaction.response.send_message(embed=embed)
        
        game.game_cancelled = True
        del self.active_games[channel_id]

    @app_commands.command(name="unofstop", description="Force stop the UNO game in this channel (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    async def unofstop(self, interaction: discord.Interaction):
        """Force stop the current game"""
        channel_id = interaction.channel.id
        
        if channel_id not in self.active_games:
            await interaction.response.send_message("❌ No active UNO game in this channel!", ephemeral=True)
            return
            
        del self.active_games[channel_id]
        
        embed = discord.Embed(
            title="🛑 UNO Game Force Stopped",
            description=f"The UNO game has been forcibly stopped by an administrator ({interaction.user.mention}).",
            color=discord.Color.dark_red()
        )
        
        await interaction.response.send_message(embed=embed)
    
    async def end_game(self, channel_id, winner_id):
        """End the game and announce winner"""
        if channel_id not in self.active_games:
            return
            
        game = self.active_games[channel_id]
        winner = game.players[winner_id]['user']
        
        embed = discord.Embed(
            title="🎉 UNO Game Over!",
            description=f"**Winner:** {winner.mention}\n\nCongratulations! 🎊",
            color=discord.Color.gold()
        )
        
        # Final standings
        standings = sorted(
            [(p['name'], len(p['hand'])) for p in game.players.values()],
            key=lambda x: x[1]
        )
        
        standings_str = "\n".join([f"{i+1}. {name}: {cards} cards" for i, (name, cards) in enumerate(standings)])
        embed.add_field(name="Final Standings", value=standings_str, inline=False)
        
        await game.channel.send(embed=embed)
        
        # Award Winner Role
        settings = await self.get_settings(game.channel.guild.id)
        role_id = settings.get("winner_role_id")
        if role_id:
            role = game.channel.guild.get_role(role_id)
            if role:
                try:
                    await winner.add_roles(role, reason="UNO Game Winner")
                    await game.channel.send(f"👑 {winner.mention} has been awarded the **{role.name}** role!")
                    
                    # Handle Duration
                    duration = settings.get("role_duration")
                    if duration:
                        expirations = await raven_db.load_document("uno_expirations") or {}
                        # Key by guild_id:user_id to handle multiple wins/guilds
                        entry_id = f"{game.channel.guild.id}_{winner.id}"
                        expires_at = (datetime.utcnow() + timedelta(minutes=duration)).timestamp()
                        
                        expirations[entry_id] = {
                            "user_id": winner.id,
                            "guild_id": game.channel.guild.id,
                            "role_id": role.id,
                            "expires_at": expires_at
                        }
                        await raven_db.save_document("uno_expirations", expirations)
                except Exception as e:
                    logger.error(f"Failed to award role to {winner}: {e}")

        # Clean up
        del self.active_games[channel_id]



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in uno command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Uno(bot))
