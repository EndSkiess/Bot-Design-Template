"""
Gambling games cog - Blackjack, Slots, Dice, Coinflip, Roulette, Horse Race
"""
import discord
from discord.ext import commands
from discord import app_commands
import random
import logging

logger = logging.getLogger('Lilith.Gambling')
from .economy_utils import (
    get_balance, add_balance, remove_balance, has_balance, CURRENCY_NAME
)

# Try to import shop utils for luck boosts
try:
    from .shop_utils import get_active_luck_boost, use_luck_boost
    SHOP_AVAILABLE = True
except ImportError:
    SHOP_AVAILABLE = False


class Gambling(commands.Cog):
    """Gambling games"""
    
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {}  # Track active blackjack games
    
    @app_commands.command(name="dice", description="Roll a dice and bet on the outcome")
    @app_commands.describe(amount="Amount to bet", prediction="Number you predict (1-6)")
    async def dice(self, interaction: discord.Interaction, amount: int, prediction: int):
        """Roll a dice - guess correctly for 6x payout"""
        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
            return
        
        if prediction < 1 or prediction > 6:
            await interaction.response.send_message("❌ Prediction must be between 1 and 6!", ephemeral=True)
            return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Remove bet
        await remove_balance(interaction.user.id, amount)
        
        # Check for luck boost
        luck_boost = 0.0
        if SHOP_AVAILABLE:
            luck_boost = get_active_luck_boost(interaction.user.id, "dice")
        
        # Roll dice with luck boost
        result = random.randint(1, 6)
        
        # Apply luck boost (give extra chance to win)
        if luck_boost > 0 and result != prediction:
            # Luck boost gives a chance to change the result to the prediction
            if random.random() < luck_boost:
                result = prediction
                if SHOP_AVAILABLE:
                    use_luck_boost(interaction.user.id)
        
        # Dice emoji
        dice_emoji = ["1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣"][result - 1]
        
        if result == prediction:
            # Win - 6x payout
            winnings = amount * 6
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🎲 Dice Roll - YOU WIN!",
                description=f"You rolled: {dice_emoji} **{result}**\n\nYou predicted **{prediction}** and won!",
                color=discord.Color.green()
            )
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            
            if luck_boost > 0:
                embed.set_footer(text=f"🍀 Luck boost active: +{int(luck_boost*100)}%")
        else:
            # Lose
            new_balance = await get_balance(interaction.user.id)
            
            embed = discord.Embed(
                title="🎲 Dice Roll - You Lost",
                description=f"You rolled: {dice_emoji} **{result}**\n\nYou predicted **{prediction}**",
                color=discord.Color.red()
            )
            embed.add_field(name="Lost", value=f"-{amount:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="slots", description="Play the slot machine")
    @app_commands.describe(amount="Amount to bet")
    async def slots(self, interaction: discord.Interaction, amount: int):
        """Slot machine with emoji symbols"""
        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
            return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Remove bet
        await remove_balance(interaction.user.id, amount)
        
        # Check for luck boost
        luck_boost = 0.0
        if SHOP_AVAILABLE:
            luck_boost = get_active_luck_boost(interaction.user.id, "slots")
        
        # Slot symbols with weights
        symbols = ["🍒", "🍋", "🍊", "🍇", "💎", "7️⃣", "🔔", "⭐"]
        weights = [25, 25, 20, 15, 8, 3, 2, 2]  # Higher weight = more common
        
        # Spin
        slot1 = random.choices(symbols, weights=weights)[0]
        slot2 = random.choices(symbols, weights=weights)[0]
        slot3 = random.choices(symbols, weights=weights)[0]
        
        # Apply luck boost (chance to make slots match)
        if luck_boost > 0 and not (slot1 == slot2 == slot3):
            if random.random() < luck_boost:
                # Make all three match
                slot2 = slot1
                slot3 = slot1
                if SHOP_AVAILABLE:
                    use_luck_boost(interaction.user.id)
        
        # Check results
        if slot1 == slot2 == slot3:
            # Jackpot - all three match
            multipliers = {
                "🍒": 5, "🍋": 5, "🍊": 8, "🍇": 10,
                "💎": 20, "7️⃣": 50, "🔔": 30, "⭐": 40
            }
            multiplier = multipliers.get(slot1, 10)
            winnings = amount * multiplier
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🎰 JACKPOT! 🎰",
                description=f"**{slot1} {slot2} {slot3}**\n\nAll three match!",
                color=discord.Color.gold()
            )
            embed.add_field(name="Multiplier", value=f"{multiplier}x", inline=True)
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=False)
            
            if luck_boost > 0:
                embed.set_footer(text=f"🍀 Luck boost active: +{int(luck_boost*100)}%")
        elif slot1 == slot2 or slot2 == slot3 or slot1 == slot3:
            # Small win - two match
            winnings = amount * 2
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🎰 Slots - Small Win!",
                description=f"**{slot1} {slot2} {slot3}**\n\nTwo symbols match!",
                color=discord.Color.green()
            )
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        else:
            # Lose
            new_balance = await get_balance(interaction.user.id)
            
            embed = discord.Embed(
                title="🎰 Slots - No Match",
                description=f"**{slot1} {slot2} {slot3}**\n\nBetter luck next time!",
                color=discord.Color.red()
            )
            embed.add_field(name="Lost", value=f"-{amount:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="blackjack", description="Play blackjack against the dealer")
    @app_commands.describe(amount="Amount to bet")
    async def blackjack(self, interaction: discord.Interaction, amount: int):
        """Play blackjack with interactive buttons"""
        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
            return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Check if user already has an active game
        if interaction.user.id in self.active_games:
            await interaction.response.send_message(
                "❌ You already have an active blackjack game! Finish it first.",
                ephemeral=True
            )
            return
        
        # Remove bet
        await remove_balance(interaction.user.id, amount)
        
        # Create deck
        deck = self._create_deck()
        
        # Deal cards
        player_hand = [self._draw_card(deck), self._draw_card(deck)]
        dealer_hand = [self._draw_card(deck), self._draw_card(deck)]
        
        # Store game state
        self.active_games[interaction.user.id] = {
            'deck': deck,
            'player_hand': player_hand,
            'dealer_hand': dealer_hand,
            'bet': amount,
            'interaction': interaction
        }
        
        # Check for natural blackjack
        player_value = self._calculate_hand(player_hand)
        dealer_value = self._calculate_hand(dealer_hand)
        
        if player_value == 21:
            # Player blackjack
            del self.active_games[interaction.user.id]
            winnings = int(amount * 2.5)  # Blackjack pays 3:2
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🃏 BLACKJACK! 🃏",
                description=f"**Your hand:** {self._format_hand(player_hand)} = **21**\n**Dealer:** {self._format_hand(dealer_hand)} = **{dealer_value}**",
                color=discord.Color.gold()
            )
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            await interaction.response.send_message(embed=embed)
            return
        
        # Show initial hands
        embed = discord.Embed(
            title="🃏 Blackjack",
            description=f"**Your hand:** {self._format_hand(player_hand)} = **{player_value}**\n**Dealer shows:** {self._format_card(dealer_hand[0])} ?",
            color=discord.Color.blue()
        )
        embed.add_field(name="Bet", value=f"{amount:,} {CURRENCY_NAME}")
        embed.set_footer(text="Hit to draw another card, Stand to end your turn")
        
        # Create buttons
        view = BlackjackView(self, interaction.user.id)
        await interaction.response.send_message(embed=embed, view=view)
    
    def _create_deck(self):
        """Create a standard 52-card deck"""
        suits = ['♠️', '♥️', '♦️', '♣️']
        ranks = ['A', '2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K']
        deck = [{'rank': rank, 'suit': suit} for suit in suits for rank in ranks]
        random.shuffle(deck)
        return deck
    
    def _draw_card(self, deck):
        """Draw a card from the deck"""
        return deck.pop()
    
    def _format_card(self, card):
        """Format a card for display"""
        return f"{card['rank']}{card['suit']}"
    
    def _format_hand(self, hand):
        """Format a hand for display"""
        return ' '.join([self._format_card(card) for card in hand])
    
    def _calculate_hand(self, hand):
        """Calculate the value of a hand"""
        value = 0
        aces = 0
        
        for card in hand:
            rank = card['rank']
            if rank in ['J', 'Q', 'K']:
                value += 10
            elif rank == 'A':
                aces += 1
                value += 11
            else:
                value += int(rank)
        
        # Adjust for aces
        while value > 21 and aces > 0:
            value -= 10
            aces -= 1
        
        return value
    
    async def _finish_blackjack(self, user_id, action):
        """Finish a blackjack game"""
        if user_id not in self.active_games:
            return None
        
        game = self.active_games[user_id]
        player_hand = game['player_hand']
        dealer_hand = game['dealer_hand']
        deck = game['deck']
        bet = game['bet']
        
        player_value = self._calculate_hand(player_hand)
        
        # Player busted
        if player_value > 21:
            del self.active_games[user_id]
            new_balance = await get_balance(user_id)
            
            embed = discord.Embed(
                title="🃏 Blackjack - BUST!",
                description=f"**Your hand:** {self._format_hand(player_hand)} = **{player_value}**\n**Dealer:** {self._format_hand(dealer_hand)} = **{self._calculate_hand(dealer_hand)}**\n\nYou busted!",
                color=discord.Color.red()
            )
            embed.add_field(name="Lost", value=f"-{bet:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            return embed
        
        # Dealer's turn
        dealer_value = self._calculate_hand(dealer_hand)
        while dealer_value < 17:
            dealer_hand.append(self._draw_card(deck))
            dealer_value = self._calculate_hand(dealer_hand)
        
        # Determine winner
        del self.active_games[user_id]
        
        if dealer_value > 21:
            # Dealer busts, player wins
            winnings = bet * 2
            new_balance = await add_balance(user_id, winnings)
            
            embed = discord.Embed(
                title="🃏 Blackjack - YOU WIN!",
                description=f"**Your hand:** {self._format_hand(player_hand)} = **{player_value}**\n**Dealer:** {self._format_hand(dealer_hand)} = **{dealer_value}**\n\nDealer busted!",
                color=discord.Color.green()
            )
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        elif player_value > dealer_value:
            # Player wins
            winnings = bet * 2
            new_balance = await add_balance(user_id, winnings)
            
            embed = discord.Embed(
                title="🃏 Blackjack - YOU WIN!",
                description=f"**Your hand:** {self._format_hand(player_hand)} = **{player_value}**\n**Dealer:** {self._format_hand(dealer_hand)} = **{dealer_value}**",
                color=discord.Color.green()
            )
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        elif player_value == dealer_value:
            # Push (tie) - return bet
            new_balance = await add_balance(user_id, bet)
            
            embed = discord.Embed(
                title="🃏 Blackjack - PUSH",
                description=f"**Your hand:** {self._format_hand(player_hand)} = **{player_value}**\n**Dealer:** {self._format_hand(dealer_hand)} = **{dealer_value}**\n\nIt's a tie! Your bet is returned.",
                color=discord.Color.blue()
            )
            embed.add_field(name="Returned", value=f"{bet:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        else:
            # Dealer wins
            new_balance = await get_balance(user_id)
            
            embed = discord.Embed(
                title="🃏 Blackjack - Dealer Wins",
                description=f"**Your hand:** {self._format_hand(player_hand)} = **{player_value}**\n**Dealer:** {self._format_hand(dealer_hand)} = **{dealer_value}**",
                color=discord.Color.red()
            )
            embed.add_field(name="Lost", value=f"-{bet:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        
        return embed
    
    @app_commands.command(name="coinflip", description="Flip a coin - heads or tails")
    @app_commands.describe(amount="Amount to bet", choice="Your choice (heads/tails)")
    @app_commands.choices(choice=[
        app_commands.Choice(name="Heads", value="heads"),
        app_commands.Choice(name="Tails", value="tails")
    ])
    async def coinflip(self, interaction: discord.Interaction, amount: int, choice: str):
        """Coinflip - 50/50 chance, 2x payout"""
        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
            return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Remove bet
        await remove_balance(interaction.user.id, amount)
        
        # Check for luck boost
        luck_boost = 0.0
        if SHOP_AVAILABLE:
            luck_boost = get_active_luck_boost(interaction.user.id, "coinflip")
        
        # Flip coin
        result = random.choice(["heads", "tails"])
        
        # Apply luck boost
        if luck_boost > 0 and result != choice:
            if random.random() < luck_boost:
                result = choice
                if SHOP_AVAILABLE:
                    use_luck_boost(interaction.user.id)
        
        # Determine win/loss
        if result == choice:
            # Win
            winnings = amount * 2
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🪙 Coinflip - YOU WIN!",
                description=f"Result: **{result.title()}** 🎉",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Choice", value=choice.title(), inline=True)
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            
            if luck_boost > 0:
                embed.set_footer(text=f"🍀 Luck boost active: +{int(luck_boost*100)}%")
        else:
            # Lose
            new_balance = await get_balance(interaction.user.id)
            
            embed = discord.Embed(
                title="🪙 Coinflip - You Lost",
                description=f"Result: **{result.title()}** 😔",
                color=discord.Color.red()
            )
            embed.add_field(name="Your Choice", value=choice.title(), inline=True)
            embed.add_field(name="Lost", value=f"-{amount:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="roulette", description="Play roulette - bet on colors, odd/even, or numbers")
    @app_commands.describe(
        amount="Amount to bet",
        bet_type="Type of bet (red, black, odd, even, number)",
        number="Specific number (0-36) if betting on number"
    )
    @app_commands.choices(bet_type=[
        app_commands.Choice(name="Red", value="red"),
        app_commands.Choice(name="Black", value="black"),
        app_commands.Choice(name="Odd", value="odd"),
        app_commands.Choice(name="Even", value="even"),
        app_commands.Choice(name="Number", value="number")
    ])
    async def roulette(self, interaction: discord.Interaction, amount: int, bet_type: str, number: int = None):
        """Roulette with multiple bet types"""
        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
            return
        
        if bet_type == "number":
            if number is None or number < 0 or number > 36:
                await interaction.response.send_message("❌ Please specify a number between 0 and 36!", ephemeral=True)
                return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Remove bet
        await remove_balance(interaction.user.id, amount)
        
        # Check for luck boost
        luck_boost = 0.0
        if SHOP_AVAILABLE:
            luck_boost = get_active_luck_boost(interaction.user.id, "roulette")
        
        # Spin roulette
        result_number = random.randint(0, 36)
        
        # Define red and black numbers
        red_numbers = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
        black_numbers = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]
        
        result_color = "green" if result_number == 0 else ("red" if result_number in red_numbers else "black")
        result_parity = "even" if result_number % 2 == 0 and result_number != 0 else ("odd" if result_number != 0 else "zero")
        
        # Check win
        won = False
        multiplier = 0
        
        if bet_type == "red" and result_color == "red":
            won = True
            multiplier = 2
        elif bet_type == "black" and result_color == "black":
            won = True
            multiplier = 2
        elif bet_type == "odd" and result_parity == "odd":
            won = True
            multiplier = 2
        elif bet_type == "even" and result_parity == "even":
            won = True
            multiplier = 2
        elif bet_type == "number" and result_number == number:
            won = True
            multiplier = 35
        
        # Apply luck boost
        if luck_boost > 0 and not won:
            if random.random() < luck_boost:
                won = True
                multiplier = 2 if bet_type != "number" else 35
                if SHOP_AVAILABLE:
                    use_luck_boost(interaction.user.id)
        
        # Result
        color_emoji = "🔴" if result_color == "red" else ("⚫" if result_color == "black" else "🟢")
        
        if won:
            winnings = amount * multiplier
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🎰 Roulette - YOU WIN!",
                description=f"Result: {color_emoji} **{result_number}** ({result_color.title()})",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Bet", value=bet_type.title() + (f" ({number})" if bet_type == "number" else ""), inline=True)
            embed.add_field(name="Multiplier", value=f"{multiplier}x", inline=True)
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            
            if luck_boost > 0:
                embed.set_footer(text=f"🍀 Luck boost active: +{int(luck_boost*100)}%")
        else:
            new_balance = await get_balance(interaction.user.id)
            
            embed = discord.Embed(
                title="🎰 Roulette - You Lost",
                description=f"Result: {color_emoji} **{result_number}** ({result_color.title()})",
                color=discord.Color.red()
            )
            embed.add_field(name="Your Bet", value=bet_type.title() + (f" ({number})" if bet_type == "number" else ""), inline=True)
            embed.add_field(name="Lost", value=f"-{amount:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="horserace", description="Bet on a horse race")
    @app_commands.describe(amount="Amount to bet", horse="Horse number (1-5)")
    @app_commands.choices(horse=[
        app_commands.Choice(name="Horse 1 🐴", value=1),
        app_commands.Choice(name="Horse 2 🐎", value=2),
        app_commands.Choice(name="Horse 3 🏇", value=3),
        app_commands.Choice(name="Horse 4 🦄", value=4),
        app_commands.Choice(name="Horse 5 🎠", value=5)
    ])
    async def horserace(self, interaction: discord.Interaction, amount: int, horse: int):
        """Horse racing - bet on which horse wins"""
        # Validation
        if amount <= 0:
            await interaction.response.send_message("❌ Bet amount must be positive!", ephemeral=True)
            return
        
        # Check balance
        if not await has_balance(interaction.user.id, amount):
            balance = await get_balance(interaction.user.id)
            await interaction.response.send_message(
                f"❌ Insufficient balance! You have {balance:,} {CURRENCY_NAME}.",
                ephemeral=True
            )
            return
        
        # Remove bet
        await remove_balance(interaction.user.id, amount)
        
        # Check for luck boost
        luck_boost = 0.0
        if SHOP_AVAILABLE:
            luck_boost = get_active_luck_boost(interaction.user.id, "horserace")
        
        # Simulate race
        speeds = {}
        
        for h in range(1, 6):
            base_speed = random.randint(50, 100)
            # Apply luck boost to chosen horse
            if h == horse and luck_boost > 0:
                base_speed += int(luck_boost * 100)
                if SHOP_AVAILABLE:
                    use_luck_boost(interaction.user.id)
            speeds[h] = base_speed
        
        # Determine winner
        winner = max(speeds, key=speeds.get)
        
        # Horse emojis
        horse_emojis = {1: "🐴", 2: "🐎", 3: "🏇", 4: "🦄", 5: "🎠"}
        
        if winner == horse:
            # Win
            winnings = amount * 4
            new_balance = await add_balance(interaction.user.id, winnings)
            
            embed = discord.Embed(
                title="🏇 Horse Race - YOU WIN!",
                description=f"{horse_emojis[winner]} **Horse {winner} WINS!**",
                color=discord.Color.green()
            )
            embed.add_field(name="Your Horse", value=f"{horse_emojis[horse]} Horse {horse}", inline=True)
            embed.add_field(name="Winnings", value=f"+{winnings:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            
            # Show race results
            race_results = "\n".join([f"{horse_emojis[h]} Horse {h}: {speeds[h]} speed" for h in sorted(speeds, key=speeds.get, reverse=True)])
            embed.add_field(name="Race Results", value=race_results, inline=False)
            
            if luck_boost > 0:
                embed.set_footer(text=f"🍀 Luck boost active: +{int(luck_boost*100)}%")
        else:
            # Lose
            new_balance = await get_balance(interaction.user.id)
            
            embed = discord.Embed(
                title="🏇 Horse Race - You Lost",
                description=f"{horse_emojis[winner]} **Horse {winner} WINS!**",
                color=discord.Color.red()
            )
            embed.add_field(name="Your Horse", value=f"{horse_emojis[horse]} Horse {horse}", inline=True)
            embed.add_field(name="Lost", value=f"-{amount:,} {CURRENCY_NAME}", inline=True)
            embed.add_field(name="New Balance", value=f"{new_balance:,} {CURRENCY_NAME}", inline=True)
            
            # Show race results
            race_results = "\n".join([f"{horse_emojis[h]} Horse {h}: {speeds[h]} speed" for h in sorted(speeds, key=speeds.get, reverse=True)])
            embed.add_field(name="Race Results", value=race_results, inline=False)
        
        await interaction.response.send_message(embed=embed)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in gambling command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

class BlackjackView(discord.ui.View):
    """Interactive buttons for blackjack"""
    
    def __init__(self, cog, user_id):
        super().__init__(timeout=60)
        self.cog = cog
        self.user_id = user_id
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in view interactions"""
        import logging
        logger = logging.getLogger('Lilith.GamblingView')
        logger.error(f"Error in BlackjackView: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing this action.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred processing this action.", ephemeral=True)
        except:
            pass

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green, emoji="🎯")
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        
        if self.user_id not in self.cog.active_games:
            await interaction.response.send_message("Game not found!", ephemeral=True)
            return
        
        game = self.cog.active_games[self.user_id]
        
        # Draw card
        card = self.cog._draw_card(game['deck'])
        game['player_hand'].append(card)
        
        player_value = self.cog._calculate_hand(game['player_hand'])
        dealer_hand = game['dealer_hand']
        
        if player_value > 21:
            # Busted
            embed = await self.cog._finish_blackjack(self.user_id, 'bust')
            self.stop()
            await interaction.response.edit_message(embed=embed, view=None)
        else:
            # Update hand
            embed = discord.Embed(
                title="🃏 Blackjack",
                description=f"**Your hand:** {self.cog._format_hand(game['player_hand'])} = **{player_value}**\n**Dealer shows:** {self.cog._format_card(dealer_hand[0])} ?",
                color=discord.Color.blue()
            )
            embed.add_field(name="Bet", value=f"{game['bet']:,} {CURRENCY_NAME}")
            embed.set_footer(text="Hit to draw another card, Stand to end your turn")
            
            await interaction.response.edit_message(embed=embed, view=self)
    
    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red, emoji="✋")
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("This isn't your game!", ephemeral=True)
            return
        
        if self.user_id not in self.cog.active_games:
            await interaction.response.send_message("Game not found!", ephemeral=True)
            return
        
        # Finish game
        embed = await self.cog._finish_blackjack(self.user_id, 'stand')
        self.stop()
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout"""
        if self.user_id in self.cog.active_games:
            # Auto-stand on timeout
            del self.cog.active_games[self.user_id]


async def setup(bot):
    await bot.add_cog(Gambling(bot))
