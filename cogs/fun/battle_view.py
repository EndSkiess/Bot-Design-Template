"""
Interactive Battle System - Discord UI Views for turn-based pet battles
"""
import discord
from discord import ui
import random
from datetime import datetime
import asyncio

from .pets_utils import (
    PET_TYPES, RARITY_INFO, TYPE_ADVANTAGES, MOODS, 
    get_pet_mood, xp_for_next_level, save_pets_data, load_pets_data,
    check_evolution, check_and_award_achievements
)


class BattleState:
    """Manages the state of an ongoing battle"""
    
    def __init__(self, challenger, opponent, pet1, pet2, pet1_name, pet2_name):
        self.challenger = challenger
        self.opponent = opponent
        self.pet1 = pet1
        self.pet2 = pet2
        self.pet1_name = pet1_name
        self.pet2_name = pet2_name
        
        # Calculate max HP
        self.pet1_max_hp = pet1["level"] * 50 + 100
        self.pet2_max_hp = pet2["level"] * 50 + 100
        
        # Current HP
        self.pet1_hp = self.pet1_max_hp
        self.pet2_hp = self.pet2_max_hp
        
        # Battle state
        self.current_turn = 1  # 1 = challenger, 2 = opponent
        self.turn_number = 1
        self.battle_log = []
        self.pet1_defending = False
        self.pet2_defending = False
        self.winner = None
        
    def get_current_player(self):
        """Get the user whose turn it is"""
        return self.challenger if self.current_turn == 1 else self.opponent
    
    def get_current_pet(self):
        """Get the pet whose turn it is"""
        return self.pet1 if self.current_turn == 1 else self.pet2
    
    def get_opponent_pet(self):
        """Get the opponent's pet"""
        return self.pet2 if self.current_turn == 1 else self.pet1
    
    def switch_turn(self):
        """Switch to the other player's turn"""
        self.current_turn = 2 if self.current_turn == 1 else 1
        self.turn_number += 1
    
    def create_health_bar(self, current_hp, max_hp, length=10):
        """Create a visual health bar"""
        if max_hp == 0:
            return "▱" * length
        filled = int((current_hp / max_hp) * length)
        filled = max(0, min(filled, length))
        return "▰" * filled + "▱" * (length - filled)
    
    def get_hp_percentage(self, hp, max_hp):
        """Get HP as percentage"""
        if max_hp == 0:
            return 0
        return int((hp / max_hp) * 100)


class BattleInviteView(ui.View):
    """View for battle invitation with Accept/Decline buttons"""
    
    def __init__(self, challenger, opponent, pet1, pet2, pet1_name, pet2_name, timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.opponent = opponent
        self.pet1 = pet1
        self.pet2 = pet2
        self.pet1_name = pet1_name
        self.pet2_name = pet2_name
        self.accepted = False
        self.message = None
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in view interactions"""
        import logging
        logger = logging.getLogger('Lilith.BattleView')
        logger.error(f"Error in BattleInviteView: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing this action.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred processing this action.", ephemeral=True)
        except:
            pass
    
    @ui.button(label="Accept Battle", style=discord.ButtonStyle.green, emoji="⚔️")
    async def accept_button(self, interaction: discord.Interaction, button: ui.Button):
        """Accept the battle challenge"""
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Only the challenged player can accept!", ephemeral=True)
            return
        
        self.accepted = True
        self.stop()
        
        # Start the battle
        battle_state = BattleState(self.challenger, self.opponent, self.pet1, self.pet2, self.pet1_name, self.pet2_name)
        battle_view = BattleTurnView(battle_state, self.message)
        
        embed = battle_view.create_battle_embed()
        await interaction.response.edit_message(embed=embed, view=battle_view)
    
    @ui.button(label="Decline", style=discord.ButtonStyle.red, emoji="❌")
    async def decline_button(self, interaction: discord.Interaction, button: ui.Button):
        """Decline the battle challenge"""
        if interaction.user.id != self.opponent.id:
            await interaction.response.send_message("❌ Only the challenged player can decline!", ephemeral=True)
            return
        
        self.stop()
        
        embed = discord.Embed(
            title="❌ Battle Declined",
            description=f"{self.opponent.mention} declined the battle challenge!",
            color=discord.Color.red()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def on_timeout(self):
        """Handle timeout"""
        if self.message and not self.accepted:
            embed = discord.Embed(
                title="⏱️ Battle Expired",
                description=f"{self.opponent.mention} didn't respond in time. Battle cancelled.",
                color=discord.Color.orange()
            )
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                pass


class BattleTurnView(ui.View):
    """View for battle turns with Attack/Defend/Special buttons"""
    
    def __init__(self, battle_state: BattleState, message=None, timeout=120):
        super().__init__(timeout=timeout)
        self.state = battle_state
        self.message = message
    
    async def on_error(self, interaction: discord.Interaction, error: Exception, item: discord.ui.Item):
        """Handle errors in view interactions"""
        import logging
        logger = logging.getLogger('Lilith.BattleView')
        logger.error(f"Error in BattleTurnView: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred processing this action.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred processing this action.", ephemeral=True)
        except:
            pass
    
    def create_battle_embed(self):
        """Create the battle embed showing current state"""
        pet1_info = PET_TYPES[self.state.pet1["type"]]
        pet2_info = PET_TYPES[self.state.pet2["type"]]
        
        # Health bars
        pet1_hp_bar = self.state.create_health_bar(self.state.pet1_hp, self.state.pet1_max_hp)
        pet2_hp_bar = self.state.create_health_bar(self.state.pet2_hp, self.state.pet2_max_hp)
        
        pet1_hp_pct = self.state.get_hp_percentage(self.state.pet1_hp, self.state.pet1_max_hp)
        pet2_hp_pct = self.state.get_hp_percentage(self.state.pet2_hp, self.state.pet2_max_hp)
        
        # Determine embed color based on whose turn it is
        color = discord.Color.blue() if self.state.current_turn == 1 else discord.Color.red()
        
        embed = discord.Embed(
            title=f"⚔️ Pet Battle - Turn {self.state.turn_number}",
            color=color
        )
        
        # Pet 1 stats
        pet1_display = f"{pet1_info['emoji']} **{self.state.challenger.display_name}'s {self.state.pet1_name}**"
        pet1_stats = f"{pet1_hp_bar} {pet1_hp_pct}% HP ({self.state.pet1_hp}/{self.state.pet1_max_hp})\n⚡ Energy: {self.state.pet1['energy']}/100"
        if self.state.pet1_defending:
            pet1_stats += "\n🛡️ **Defending**"
        
        embed.add_field(name=pet1_display, value=pet1_stats, inline=False)
        
        # VS separator
        embed.add_field(name="━━━━━━━━━━━━━━━━━━━━", value="", inline=False)
        
        # Pet 2 stats
        pet2_display = f"{pet2_info['emoji']} **{self.state.opponent.display_name}'s {self.state.pet2_name}**"
        pet2_stats = f"{pet2_hp_bar} {pet2_hp_pct}% HP ({self.state.pet2_hp}/{self.state.pet2_max_hp})\n⚡ Energy: {self.state.pet2['energy']}/100"
        if self.state.pet2_defending:
            pet2_stats += "\n🛡️ **Defending**"
        
        embed.add_field(name=pet2_display, value=pet2_stats, inline=False)
        
        # Battle log (last 3 actions)
        if self.state.battle_log:
            log_text = "\n".join(self.state.battle_log[-3:])
            embed.add_field(name="📜 Battle Log", value=log_text, inline=False)
        
        # Current turn indicator
        current_player = self.state.get_current_player()
        embed.set_footer(text=f"⏳ {current_player.display_name}'s turn!")
        
        return embed
    
    def calculate_damage(self, move_type: str):
        """Calculate damage for a move"""
        attacker = self.state.get_current_pet()
        defender = self.state.get_opponent_pet()
        
        # Base damage - reduced by 40% for longer battles
        base_damage = int(((attacker["level"] * 3) + random.randint(5, 15)) * 0.6)
        
        # Move multiplier
        move_mult = {
            "attack": 1.0,
            "defend": 0.0,
            "special": 2.0
        }[move_type]
        
        # Rarity bonus
        rarity_bonus = RARITY_INFO[attacker["rarity"]]["stat_bonus"]
        
        # Type advantage
        type_mult = 1.0
        if self.state.current_turn == 1:
            if self.state.pet2["type"] in TYPE_ADVANTAGES.get(self.state.pet1["type"], []):
                type_mult = 1.3
        else:
            if self.state.pet1["type"] in TYPE_ADVANTAGES.get(self.state.pet2["type"], []):
                type_mult = 1.3
        
        # Mood multiplier
        mood = get_pet_mood(attacker)
        mood_mult = MOODS[mood]["battle_mult"]
        
        # Critical hit chance (15% if happiness > 80)
        crit_mult = 1.0
        is_crit = False
        if attacker["happiness"] > 80 and random.random() < 0.15:
            crit_mult = 1.5
            is_crit = True
        
        # Calculate final damage
        damage = int(base_damage * move_mult * rarity_bonus * type_mult * mood_mult * crit_mult)
        
        # Check if defender is defending
        is_defending = self.state.pet2_defending if self.state.current_turn == 1 else self.state.pet1_defending
        if is_defending and move_type != "defend":
            damage = int(damage * 0.95)
        
        return damage, is_crit, type_mult > 1.0
    
    async def execute_move(self, interaction: discord.Interaction, move_type: str):
        """Execute a battle move"""
        # Verify it's the correct player's turn
        current_player = self.state.get_current_player()
        if interaction.user.id != current_player.id:
            await interaction.response.send_message("❌ It's not your turn!", ephemeral=True)
            return
        
        # Get pet info
        attacker_pet = self.state.get_current_pet()
        attacker_info = PET_TYPES[attacker_pet["type"]]
        attacker_name = self.state.pet1_name if self.state.current_turn == 1 else self.state.pet2_name
        
        # Check energy requirement for special move
        if move_type == "special":
            if attacker_pet["energy"] < 45:
                await interaction.response.send_message("❌ Not enough energy! Special move requires 45 energy.", ephemeral=True)
                return
        
        # Reset defending status for attacker
        if self.state.current_turn == 1:
            self.state.pet1_defending = False
        else:
            self.state.pet2_defending = False
        
        # Execute move
        if move_type == "defend":
            # Set defending status
            if self.state.current_turn == 1:
                self.state.pet1_defending = True
            else:
                self.state.pet2_defending = True
            
            log_entry = f"• {attacker_name} used **Defend**! Damage reduced by 5% next turn."
            self.state.battle_log.append(log_entry)
        else:
            # Calculate and apply damage
            damage, is_crit, has_advantage = self.calculate_damage(move_type)
            
            # Deduct energy for special move (30%)
            if move_type == "special":
                energy_cost = 45
                attacker_pet["energy"] = max(0, attacker_pet["energy"] - energy_cost)
            
            # Apply damage to opponent
            if self.state.current_turn == 1:
                self.state.pet2_hp = max(0, self.state.pet2_hp - damage)
            else:
                self.state.pet1_hp = max(0, self.state.pet1_hp - damage)
            
            # Create log entry
            move_name = "Attack" if move_type == "attack" else "Special Move"
            log_entry = f"• {attacker_name} used **{move_name}**!"
            
            if is_crit:
                log_entry += " **Critical hit!**"
            if has_advantage:
                log_entry += " **Super effective!**"
            
            log_entry += f" (-{damage} HP)"
            self.state.battle_log.append(log_entry)
            
            # Save energy change if special move was used
            if move_type == "special":
                # CRITICAL FIX: Load full lists first to avoid overwriting other pets
                full_list1 = await load_pets_data(self.state.challenger.id)
                for i, p in enumerate(full_list1):
                    if p["type"] == self.state.pet1["type"]:
                        full_list1[i] = self.state.pet1
                        break
                await save_pets_data(self.state.challenger.id, full_list1)
                
                full_list2 = await load_pets_data(self.state.opponent.id)
                for i, p in enumerate(full_list2):
                    if p["type"] == self.state.pet2["type"]:
                        full_list2[i] = self.state.pet2
                        break
                await save_pets_data(self.state.opponent.id, full_list2)
        
        # Check if battle is over
        if self.state.pet1_hp <= 0:
            self.state.winner = self.state.opponent
            await self.end_battle(interaction)
            return
        elif self.state.pet2_hp <= 0:
            self.state.winner = self.state.challenger
            await self.end_battle(interaction)
            return
        
        # Switch turn
        self.state.switch_turn()
        
        # Update embed
        embed = self.create_battle_embed()
        await interaction.response.edit_message(embed=embed, view=self)
    
    async def end_battle(self, interaction: discord.Interaction):
        """End the battle and show results"""
        self.stop()
        
        winner_pet = self.state.pet1 if self.state.winner == self.state.challenger else self.state.pet2
        loser_pet = self.state.pet2 if self.state.winner == self.state.challenger else self.state.pet1
        
        winner_name = self.state.pet1_name if self.state.winner == self.state.challenger else self.state.pet2_name
        winner_info = PET_TYPES[winner_pet["type"]]
        
        # Calculate rewards
        base_xp = 150
        rarity_bonus = RARITY_INFO[winner_pet["rarity"]]["xp_bonus"]
        xp_gain = int(base_xp * rarity_bonus)
        
        # Create victory embed
        embed = discord.Embed(
            title="🏆 Victory!",
            description=f"{self.state.winner.mention}'s **{winner_name}** wins the battle!",
            color=discord.Color.gold()
        )
        
        # Final HP
        pet1_hp_bar = self.state.create_health_bar(self.state.pet1_hp, self.state.pet1_max_hp)
        pet2_hp_bar = self.state.create_health_bar(self.state.pet2_hp, self.state.pet2_max_hp)
        
        embed.add_field(
            name="Final HP",
            value=f"{self.state.pet1_name}: {pet1_hp_bar} {self.state.pet1_hp}/{self.state.pet1_max_hp}\n"
                  f"{self.state.pet2_name}: {pet2_hp_bar} {self.state.pet2_hp}/{self.state.pet2_max_hp}",
            inline=False
        )
        
        # Rewards
        embed.add_field(
            name="🎁 Rewards",
            value=f"+{xp_gain} XP\n+50 mayem",
            inline=False
        )
        
        embed.set_footer(text=f"Battle lasted {self.state.turn_number} turns")
        
        # Save rewards to database
        winner_pet["xp"] += xp_gain
        winner_pet["total_xp"] = winner_pet.get("total_xp", 0) + xp_gain
        
        # Check for level ups
        old_level = winner_pet["level"]
        while winner_pet["xp"] >= xp_for_next_level(winner_pet["level"]):
            winner_pet["xp"] -= xp_for_next_level(winner_pet["level"])
            winner_pet["level"] += 1
        
        if winner_pet["level"] > old_level:
            embed.add_field(name="✨ Level Up!", value=f"Level {old_level} → {winner_pet['level']}", inline=False)
        
        # Check evolution and achievements
        if check_evolution(winner_pet):
            embed.add_field(name="🌟 Evolution!", value=f"**{winner_name}** has evolved!", inline=False)
        
        check_and_award_achievements(winner_pet, action="battle_won")
        
        # CRITICAL FIX: Load full lists first to avoid overwriting other pets
        full_list1 = await load_pets_data(self.state.challenger.id)
        for i, p in enumerate(full_list1):
            if p["type"] == self.state.pet1["type"]:
                full_list1[i] = self.state.pet1
                break
        await save_pets_data(self.state.challenger.id, full_list1)
        
        full_list2 = await load_pets_data(self.state.opponent.id)
        for i, p in enumerate(full_list2):
            if p["type"] == self.state.pet2["type"]:
                full_list2[i] = self.state.pet2
                break
        await save_pets_data(self.state.opponent.id, full_list2)
        
        await interaction.response.edit_message(embed=embed, view=None)
    
    @ui.button(label="Attack", style=discord.ButtonStyle.primary, emoji="⚔️")
    async def attack_button(self, interaction: discord.Interaction, button: ui.Button):
        """Standard attack move"""
        await self.execute_move(interaction, "attack")
    
    @ui.button(label="Defend", style=discord.ButtonStyle.secondary, emoji="🛡️")
    async def defend_button(self, interaction: discord.Interaction, button: ui.Button):
        """Defensive move - reduces next damage by 50%"""
        await self.execute_move(interaction, "defend")
    
    @ui.button(label="Special", style=discord.ButtonStyle.danger, emoji="✨")
    async def special_button(self, interaction: discord.Interaction, button: ui.Button):
        """Special move - high damage with type advantage bonus (Requires 30 energy)"""
        # Check if current player has enough energy
        current_pet = self.state.get_current_pet()
        if current_pet["energy"] < 30:
            await interaction.response.send_message("❌ Not enough energy! Special move requires 30 energy.", ephemeral=True)
            return
        await self.execute_move(interaction, "special")
    
    async def on_timeout(self):
        """Handle timeout - current player loses"""
        if self.message and not self.state.winner:
            current_player = self.state.get_current_player()
            other_player = self.state.opponent if current_player == self.state.challenger else self.state.challenger
            
            embed = discord.Embed(
                title="⏱️ Battle Timeout",
                description=f"{current_player.mention} took too long to respond!\n{other_player.mention} wins by default!",
                color=discord.Color.orange()
            )
            try:
                await self.message.edit(embed=embed, view=None)
            except:
                pass
