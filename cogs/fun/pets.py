"""
Pet System - Virtual pets with spawn mechanics, care, and battles
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
from typing import Union, Optional
from datetime import datetime, timedelta
import random
import logging
import aiohttp
import os
from dotenv import load_dotenv

from .pets_utils import (
    PET_TYPES, RARITY_INFO, MAX_PETS, MOODS, ACHIEVEMENTS, RARITY_ABILITIES,
    get_user_pets, get_user_pet_by_name, create_pet, remove_pet,
    can_feed, feed_pet, can_play, play_with_pet, can_train, train_pet,
    xp_for_next_level, can_battle, battle_pets, get_pet_leaderboard,
    set_spawn_channel, get_spawn_channel, create_spawn, clear_spawn, get_current_spawn,
    get_pet_mood, get_pet_display_name, get_evolution_stars, set_pet_nickname,
    create_progress_bar, format_time_remaining, get_cooldown_info, get_stat_color_indicator,
    can_user_spawn, record_user_spawn, can_refill_all, refill_all_pets
)


# Try to import economy utils
try:
    from .economy_utils import has_balance, remove_balance, CURRENCY_NAME
    ECONOMY_AVAILABLE = True
except ImportError:
    ECONOMY_AVAILABLE = False

# Load Tenor API key
load_dotenv()
TENOR_API_KEY = os.getenv('TENOR_API_KEY', '')

logger = logging.getLogger('Lilith.Pets')


class Pets(commands.Cog):
    """Virtual pet system"""
    
    def __init__(self, bot):
        self.bot = bot
        self.tenor_base_url = "https://tenor.googleapis.com/v2/search"
        self.spawn_task.start()
    
    def cog_unload(self):
        self.spawn_task.cancel()
    
    @tasks.loop(minutes=30)
    async def spawn_task(self):
        """Periodically spawn pets in all configured channels"""
        try:
            # Get all spawn configurations
            from ..utils.ravendb_manager import raven_db
            from .pets_utils import SPAWNS_PREFIX, create_spawn, PET_TYPES
            
            all_configs = await raven_db.get_all_in_collection(SPAWNS_PREFIX)
            
            for config in all_configs:
                try:
                    # Handle both dict and object responses
                    gid = None
                    cid = None
                    if isinstance(config, dict):
                        gid = config.get('@metadata', {}).get('@id', '').split('/')[-1]
                        cid = config.get('channel_id')
                    else:
                        gid = getattr(config, 'id', '').split('/')[-1]
                        cid = getattr(config, 'channel_id', None)
                    
                    if not gid or not cid:
                        continue
                        
                    # 20% chance to spawn every 30 mins (approx once every 2.5 hours)
                    if random.random() > 0.2:
                        continue
                        
                    guild = self.bot.get_guild(int(gid))
                    if not guild:
                        continue
                        
                    channel = guild.get_channel(int(cid))
                    if not channel:
                        continue
                        
                    # Create spawn
                    spawn_data = await create_spawn(int(gid))
                    pet_type = spawn_data["pet_type"]
                    is_shiny = spawn_data["is_shiny"]
                    pet_info = PET_TYPES[pet_type]
                    
                    rarity_color = RARITY_INFO[pet_info["rarity"]]["color"]
                    title = f"✨ A Shiny {pet_info['name']} Appeared! ✨" if is_shiny else f"A Wild {pet_info['name']} Appeared!"
                    
                    embed = discord.Embed(
                        title=title,
                        description="Use `/catch` to catch it before it runs away!",
                        color=rarity_color
                    )
                    embed.add_field(name="Rarity", value=pet_info["rarity"].title(), inline=True)
                    
                    gif_file = self.get_pet_gif(pet_type)
                    if gif_file:
                        embed.set_thumbnail(url=f"attachment://{pet_type}.gif")
                        await channel.send(embed=embed, file=gif_file)
                    else:
                        await channel.send(embed=embed)
                        
                except Exception as e:
                    logger.error(f"Error in spawn_task for guild {config}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in spawn_task loop: {e}")

    @spawn_task.before_loop
    async def before_spawn_task(self):
        await self.bot.wait_until_ready()
    
    def get_pet_gif(self, pet_type: str) -> discord.File:
        """Get a local GIF file for a specific pet type from pets folder"""
        from pathlib import Path
        
        # Get bot root directory (3 levels up from this file)
        bot_root = Path(__file__).parent.parent.parent
        pets_folder = bot_root / "pets"
        
        # Try to find the GIF file for this pet type
        gif_path = pets_folder / f"{pet_type}.gif"
        
        # Check if file exists
        if gif_path.exists():
            return discord.File(gif_path, filename=f"{pet_type}.gif")
        
        # If no GIF found, return None
        return None
    
    @app_commands.command(name="catch", description="Catch a spawned pet")
    @app_commands.describe(nickname="Give your new pet a nickname (optional)")
    async def catch(self, interaction: discord.Interaction, nickname: str = None):
        """Catch a spawned pet"""
        # Defer interaction to prevent timeout
        await interaction.response.defer()
        
        # Check if there's a spawn
        current_spawn = await get_current_spawn(interaction.guild_id)
        
        if not current_spawn:
            await interaction.followup.send("❌ No pet is currently spawned!", ephemeral=True)
            return
        
        # Extract pet_type and is_shiny from spawn result
        pet_type = current_spawn["pet_type"]
        is_shiny = current_spawn.get("is_shiny", False)
        
        # Attempt to create/level up pet
        pet_info = PET_TYPES[pet_type]
        result = await create_pet(interaction.user.id, pet_type, is_shiny=is_shiny, nickname=nickname)
        
        # Handle different outcomes
        if result["status"] == "new":
            # New pet caught
            await clear_spawn(interaction.guild_id)
            rarity_color = RARITY_INFO[pet_info["rarity"]]["color"]
            
            user_pets = await get_user_pets(interaction.user.id)
            
            pet_name_display = f"{nickname} ({pet_info['name']})" if nickname else pet_info['name']
            if is_shiny:
                pet_name_display = f"✨ {pet_name_display}"
            
            embed = discord.Embed(
                title="🎉 Shiny Pet Caught! 🎉" if is_shiny else "🎉 Pet Caught! 🎉",
                description=f"{interaction.user.mention} caught a **{pet_name_display}**!",
                color=rarity_color
            )
            embed.add_field(name="Type", value=f"{pet_info['emoji']} {pet_info['name']}", inline=True)
            embed.add_field(name="Rarity", value=pet_info["rarity"].title(), inline=True)
            embed.add_field(name="Your Pets", value=f"{len(user_pets)}/{MAX_PETS}", inline=True)
            embed.set_footer(text="Use /pet to view your pets!")
            
            # Add GIF as thumbnail if available
            gif_file = self.get_pet_gif(pet_type)
            if gif_file:
                embed.set_thumbnail(url=f"attachment://{pet_type}.gif")
                await interaction.followup.send(embed=embed, file=gif_file)
            else:
                await interaction.followup.send(embed=embed)
        
        elif result["status"] == "leveled_up":
            # Duplicate pet - leveled up
            await clear_spawn(interaction.guild_id)
            pet = result["pet"]
            old_level = result["old_level"]
            xp_gained = result["xp_gained"]
            rarity_color = RARITY_INFO[pet_info["rarity"]]["color"]
            
            embed = discord.Embed(
                title="⬆️ Pet Leveled Up! ⬆️",
                description=f"{interaction.user.mention} caught another **{pet_info['name']}**!",
                color=rarity_color
            )
            embed.add_field(name="Pet", value=f"{pet_info['emoji']} {pet_info['name']}", inline=True)
            embed.add_field(name="Level", value=f"{old_level} → **{pet['level']}**", inline=True)
            embed.add_field(name="XP Gained", value=f"+{xp_gained} XP", inline=True)
            
            if pet["level"] > old_level:
                embed.set_footer(text=f"🎊 Your pet leveled up to Level {pet['level']}!")
            else:
                embed.set_footer(text=f"Keep catching to level up! ({pet['xp']}/{xp_for_next_level(pet['level'])} XP)")
            
            await interaction.followup.send(embed=embed)
        
        elif result["status"] == "max_reached":
            # User has reached max pets
            embed = discord.Embed(
                title="❌ Maximum Pets Reached",
                description=f"You already have {MAX_PETS} pets! Remove one with `/removepet` to catch more.",
                color=discord.Color.red()
            )
            
            # Show current pets
            current_pets = result["current_pets"]
            pets_list = []
            for pet in current_pets:
                p_info = PET_TYPES.get(pet["type"])
                if p_info:  # Only add if pet type is valid
                    pets_list.append(f"{p_info['emoji']} **{p_info['name']}** (Lv. {pet['level']})")
            
            embed.add_field(
                name="Your Current Pets",
                value="\n".join(pets_list) if pets_list else "No valid pets",
                inline=False
            )
            embed.set_footer(text=f"Use /removepet <pet_name> to remove a pet")
            
            await interaction.followup.send(embed=embed, ephemeral=True)

    @app_commands.command(name="rename", description="Rename one of your pets")
    @app_commands.describe(
        pet_name="Current name/type of the pet",
        new_nickname="New nickname for the pet"
    )
    async def rename(self, interaction: discord.Interaction, pet_name: str, new_nickname: str):
        """Rename a pet"""
        user_pets = await get_user_pets(interaction.user.id)
        
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
        
        # Find the pet
        pet = await get_user_pet_by_name(interaction.user.id, pet_name)
        if not pet:
            await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
            return
        
        # Update nickname
        await set_pet_nickname(interaction.user.id, pet_name, new_nickname)
        pet_info = PET_TYPES.get(pet["type"])
        
        if not pet_info:
            await interaction.response.send_message(f"❌ Error: Unknown pet type '{pet.get('type')}'!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏷️ Pet Renamed",
            description=f"Your **{pet_info['name']}** is now named **{new_nickname}**!",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="viewpets", description="View all catchable pets")
    async def viewpets(self, interaction: discord.Interaction):
        """View all catchable pets"""
        embed = discord.Embed(
            title="🐾 Petpedia",
            description="All pets that can be caught in the wild!",
            color=discord.Color.gold()
        )
        
        # Group by rarity
        pets_by_rarity = {}
        for pet_id, pet_info in PET_TYPES.items():
            rarity = pet_info["rarity"]
            if rarity not in pets_by_rarity:
                pets_by_rarity[rarity] = []
            pets_by_rarity[rarity].append(f"{pet_info['emoji']} **{pet_info['name']}**")
        
        # Order rarities
        rarity_order = ["common", "uncommon", "rare", "epic", "legendary", "mythical"]
        
        for rarity in rarity_order:
            if rarity in pets_by_rarity:
                pets_list = pets_by_rarity[rarity]
                
                embed.add_field(
                    name=f"{rarity.title()} ({len(pets_list)})",
                    value="\n".join(pets_list),
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pet", description="View your pet(s) status")
    @app_commands.describe(pet_name="Name of specific pet to view (optional)")
    async def pet(self, interaction: discord.Interaction, pet_name: str = None):
        """View pet status"""
        user_pets = await get_user_pets(interaction.user.id)
        
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets! Wait for one to spawn and use `/catch`.", ephemeral=True)
            return
        
        # If pet_name specified, show that specific pet
        if pet_name:
            pet = await get_user_pet_by_name(interaction.user.id, pet_name)
            
            if not pet:
                await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
                return
            
            pet_info = PET_TYPES.get(pet["type"])
            
            if not pet_info:
                await interaction.response.send_message(f"❌ Error: Unknown pet type '{pet.get('type')}'! Please contact an admin.", ephemeral=True)
                return
            
            rarity_color = RARITY_INFO[pet["rarity"]]["color"]
            
            # Calculate XP progress
            xp_needed = xp_for_next_level(pet["level"])
            xp_progress = (pet["xp"] / xp_needed) * 100 if xp_needed > 0 else 0
            
            display_name = get_pet_display_name(pet)
            
            embed = discord.Embed(
                title=f"{pet_info['emoji']} {display_name}",
                color=rarity_color
            )
            
            embed.add_field(name="Level", value=f"**{pet['level']}**", inline=True)
            embed.add_field(name="Rarity", value=pet["rarity"].title(), inline=True)
            embed.add_field(name="XP", value=f"{pet['xp']}/{xp_needed} ({int(xp_progress)}%)", inline=True)
            
            # Stats with bars
            hunger_bar = "█" * (pet["hunger"] // 10) + "░" * (10 - pet["hunger"] // 10)
            happiness_bar = "█" * (pet["happiness"] // 10) + "░" * (10 - pet["happiness"] // 10)
            energy_bar = "█" * (pet["energy"] // 10) + "░" * (10 - pet["energy"] // 10)
            
            embed.add_field(name="Hunger", value=f"{hunger_bar} {pet['hunger']}/100", inline=False)
            embed.add_field(name="Happiness", value=f"{happiness_bar} {pet['happiness']}/100", inline=False)
            embed.add_field(name="Energy", value=f"{energy_bar} {pet['energy']}/100", inline=False)
            
            caught_at = datetime.fromisoformat(pet["caught_at"])
            embed.set_footer(text=f"Caught on {caught_at.strftime('%Y-%m-%d')}")
            
            # Add GIF as thumbnail if available
            gif_file = self.get_pet_gif(pet["type"])
            if gif_file:
                embed.set_thumbnail(url=f"attachment://{pet['type']}.gif")
                await interaction.response.send_message(embed=embed, file=gif_file)
            else:
                await interaction.response.send_message(embed=embed)
        
        else:
            # Show all pets
            embed = discord.Embed(
                title=f"🐾 {interaction.user.display_name}'s Pets ({len(user_pets)}/{MAX_PETS})",
                color=discord.Color.blue()
            )
            
            for i, pet in enumerate(user_pets, 1):
                pet_info = PET_TYPES.get(pet["type"])
                
                # Skip pets with invalid/unknown types
                if not pet_info:
                    logger.warning(f"Unknown pet type '{pet.get('type')}' for user {interaction.user.id}, skipping")
                    continue
                
                xp_needed = xp_for_next_level(pet["level"])
                display_name = get_pet_display_name(pet)
                
                value = (
                    f"**Level:** {pet['level']} | **XP:** {pet['xp']}/{xp_needed}\n"
                    f"**Rarity:** {pet['rarity'].title()}\n"
                    f"💚 {pet['hunger']} | 😊 {pet['happiness']} | ⚡ {pet['energy']}"
                )
                
                embed.add_field(
                    name=f"{i}. {pet_info['emoji']} {display_name}",
                    value=value,
                    inline=False
                )
            
            embed.set_footer(text="Use /pet <pet_name> to view detailed stats for a specific pet")
            
            await interaction.response.send_message(embed=embed)

    
    @app_commands.command(name="removepet", description="Remove a pet from your collection")
    @app_commands.describe(pet_name="Name of the pet to remove")
    async def removepet(self, interaction: discord.Interaction, pet_name: str):
        """Remove a pet"""
        user_pets = await get_user_pets(interaction.user.id)
        
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
        
        # Check if pet exists
        pet = await get_user_pet_by_name(interaction.user.id, pet_name)
        if not pet:
            await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
            return
        
        # Remove the pet
        result = await remove_pet(interaction.user.id, pet_name)
        
        if result["status"] == "removed":
            removed_pet = result["pet"]
            pet_info = PET_TYPES.get(removed_pet["type"])
            
            if not pet_info:
                await interaction.response.send_message(f"✅ Pet removed (unknown type: {removed_pet.get('type')})")
                return
            
            rarity_color = RARITY_INFO[removed_pet["rarity"]]["color"]
            
            embed = discord.Embed(
                title="👋 Pet Removed",
                description=f"You released your **{pet_info['name']}**!",
                color=rarity_color
            )
            embed.add_field(name="Pet", value=f"{pet_info['emoji']} {pet_info['name']}", inline=True)
            embed.add_field(name="Level", value=str(removed_pet["level"]), inline=True)
            embed.add_field(name="Rarity", value=removed_pet["rarity"].title(), inline=True)
            
            remaining_pets = await get_user_pets(interaction.user.id)
            embed.set_footer(text=f"You now have {len(remaining_pets)}/{MAX_PETS} pets")
            
            await interaction.response.send_message(embed=embed)
        else:
            await interaction.response.send_message("❌ Failed to remove pet!", ephemeral=True)

    
    @app_commands.command(name="feed", description="Feed your pet")
    @app_commands.describe(pet_name="Name of the pet to feed (required if you have multiple pets)")
    async def feed(self, interaction: discord.Interaction, pet_name: str = None):
        """Feed pet"""
        if not ECONOMY_AVAILABLE:
            await interaction.response.send_message("❌ Economy system not available!", ephemeral=True)
            return
        
        user_pets = await get_user_pets(interaction.user.id)
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
        
        # If user has multiple pets and no pet_name specified, ask for it
        if len(user_pets) > 1 and not pet_name:
            pets_list = [get_pet_display_name(p) for p in user_pets]
            await interaction.response.send_message(
                f"❌ You have multiple pets! Please specify which one to feed: `/feed <pet_name>`\n"
                f"Your pets: {', '.join(pets_list)}",
                ephemeral=True
            )
            return
        
        if pet_name:
            pet = await get_user_pet_by_name(interaction.user.id, pet_name)
            if not pet:
                await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
                return
        else:
            pet = user_pets[0]
        
        pet_info = PET_TYPES.get(pet["type"])
        if not pet_info:
            await interaction.response.send_message(f"❌ Error: Unknown pet type '{pet.get('type')}'!", ephemeral=True)
            return
        
        display_name = get_pet_display_name(pet)
        check_name = pet_name if pet_name else pet_info["name"]
        
        if not await can_feed(interaction.user.id, check_name):
             await interaction.response.send_message(f"❌ You can only feed **{display_name}** once per hour!", ephemeral=True)
             return
        
        # Check balance
        cost = 50
        if not await has_balance(interaction.user.id, cost):
            await interaction.response.send_message(f"❌ You need {cost} {CURRENCY_NAME} to feed your pet!", ephemeral=True)
            return
        
        # Deduct cost and feed
        await remove_balance(interaction.user.id, cost)
        new_hunger = await feed_pet(interaction.user.id, check_name)
        
        embed = discord.Embed(
            title=f"🍖 Fed {display_name}!",
            description=f"Your pet's hunger is now **{new_hunger}/100**",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Cost: {cost} {CURRENCY_NAME}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="playpet", description="Play with your pet")
    @app_commands.describe(pet_name="Name of the pet to play with (required if you have multiple pets)")
    async def playpet(self, interaction: discord.Interaction, pet_name: str = None):
        """Play with pet"""
        if not ECONOMY_AVAILABLE:
            await interaction.response.send_message("❌ Economy system not available!", ephemeral=True)
            return
        
        user_pets = await get_user_pets(interaction.user.id)
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
        
        # If user has multiple pets and no pet_name specified, ask for it
        if len(user_pets) > 1 and not pet_name:
            pets_list = [get_pet_display_name(p) for p in user_pets]
            await interaction.response.send_message(
                f"❌ You have multiple pets! Please specify which one to play with: `/playpet <pet_name>`\n"
                f"Your pets: {', '.join(pets_list)}",
                ephemeral=True
            )
            return
        
        if pet_name:
            pet = await get_user_pet_by_name(interaction.user.id, pet_name)
            if not pet:
                await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
                return
        else:
            pet = user_pets[0]
        
        pet_info = PET_TYPES.get(pet["type"])
        if not pet_info:
            await interaction.response.send_message(f"❌ Error: Unknown pet type '{pet.get('type')}'!", ephemeral=True)
            return
        
        display_name = get_pet_display_name(pet)
        check_name = pet_name if pet_name else pet_info["name"]
        
        if not await can_play(interaction.user.id, check_name):
            await interaction.response.send_message(f"❌ You can only play with **{display_name}** once per hour!", ephemeral=True)
            return
        
        # Check balance
        cost = 50
        if not await has_balance(interaction.user.id, cost):
            await interaction.response.send_message(f"❌ You need {cost} {CURRENCY_NAME} to play with your pet!", ephemeral=True)
            return
        
        # Deduct cost and play
        await remove_balance(interaction.user.id, cost)
        new_happiness = await play_with_pet(interaction.user.id, check_name)
        
        embed = discord.Embed(
            title=f"🎾 Played with {display_name}!",
            description=f"Your pet's happiness is now **{new_happiness}/100**",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Cost: {cost} {CURRENCY_NAME}")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="refill", description="Fully restore hunger, happiness, and energy for ALL your pets (24h cooldown)")
    async def refill(self, interaction: discord.Interaction):
        """Bulk refill all pets stats"""
        user_pets = await get_user_pets(interaction.user.id)
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
            
        # Check cooldown
        can_refill, remaining = await can_refill_all(interaction.user.id)
        if not can_refill:
            time_str = format_time_remaining(remaining)
            await interaction.response.send_message(f"❌ You are on cooldown! You can use `/refill` again in **{time_str}**.", ephemeral=True)
            return
            
        # Refill all
        refilled_pets = await refill_all_pets(interaction.user.id)
        
        embed = discord.Embed(
            title="🪄 Magical Refill! 🪄",
            description=f"All of your pets has been fully restored to 100% stats!",
            color=discord.Color.gold()
        )
        
        for pet in refilled_pets:
            display_name = get_pet_display_name(pet)
            pet_info = PET_TYPES.get(pet["type"])
            emoji = pet_info["emoji"] if pet_info else "🐾"
            
            embed.add_field(
                name=f"{emoji} {display_name}",
                value="🍖 Hunger: 100%\n😊 Happiness: 100%\n⚡ Energy: 100%",
                inline=True
            )
            
        embed.set_footer(text="Your pets are happy and full of energy! ✨")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="train", description="Train your pet to gain XP")
    @app_commands.describe(pet_name="Name of the pet to train (required if you have multiple pets)")
    async def train(self, interaction: discord.Interaction, pet_name: str = None):
        """Train pet"""
        user_pets = await get_user_pets(interaction.user.id)
        if not user_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
        
        # If user has multiple pets and no pet_name specified, ask for it
        if len(user_pets) > 1 and not pet_name:
            pets_list = [get_pet_display_name(p) for p in user_pets]
            await interaction.response.send_message(
                f"❌ You have multiple pets! Please specify which one to train: `/train <pet_name>`\n"
                f"Your pets: {', '.join(pets_list)}",
                ephemeral=True
            )
            return
        
        if pet_name:
            pet = await get_user_pet_by_name(interaction.user.id, pet_name)
            if not pet:
                await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
                return
        else:
            pet = user_pets[0]
        
        pet_info = PET_TYPES.get(pet["type"])
        if not pet_info:
            await interaction.response.send_message(f"❌ Error: Unknown pet type '{pet.get('type')}'!", ephemeral=True)
            return
        
        display_name = get_pet_display_name(pet)
        check_name = pet_name if pet_name else pet_info["name"]
        
        if not await can_train(interaction.user.id, check_name):
            if pet["energy"] < 20:
                await interaction.response.send_message(f"❌ **{display_name}** doesn't have enough energy (need 20)!", ephemeral=True)
            else:
                await interaction.response.send_message(f"❌ You can only train **{display_name}** once every 2 hours!", ephemeral=True)
            return
        
        # Train
        result = await train_pet(interaction.user.id, check_name)
        if not result:
            await interaction.response.send_message("❌ Failed to train pet!", ephemeral=True)
            return
        
        xp_gain, new_level, old_level = result
        
        embed = discord.Embed(
            title=f"💪 Trained {display_name}!",
            description=f"Gained **{xp_gain} XP**!",
            color=discord.Color.blue()
        )
        
        if new_level > old_level:
            embed.add_field(name="Level Up!", value=f"Level {old_level} → {new_level}", inline=False)
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="petbattle", description="Challenge another user to a pet battle")
    @app_commands.describe(
        user="User to battle",
        pet_name="Name of your pet to battle with (required if you have multiple pets)"
    )
    async def petbattle(self, interaction: discord.Interaction, user: discord.Member, pet_name: str = None):
        """Interactive turn-based pet battle"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't battle yourself!", ephemeral=True)
            return
        
        if user.bot:
            await interaction.response.send_message("❌ You can't battle a bot!", ephemeral=True)
            return
        
        # Check both have pets
        user1_pets = await get_user_pets(interaction.user.id)
        user2_pets = await get_user_pets(user.id)
        
        if not user1_pets:
            await interaction.response.send_message("❌ You don't have any pets!", ephemeral=True)
            return
        
        if not user2_pets:
            await interaction.response.send_message(f"❌ {user.mention} doesn't have any pets!", ephemeral=True)
            return
        
        # If user has multiple pets and no pet_name specified, ask for it
        if len(user1_pets) > 1 and not pet_name:
            pets_list = [get_pet_display_name(p) for p in user1_pets]
            await interaction.response.send_message(
                f"❌ You have multiple pets! Please specify which one to battle with: `/petbattle @{user.name} <pet_name>`\n"
                f"Your pets: {', '.join(pets_list)}",
                ephemeral=True
            )
            return
        
        # Get user's pet
        if pet_name:
            pet1 = await get_user_pet_by_name(interaction.user.id, pet_name)
            if not pet1:
                await interaction.response.send_message(f"❌ You don't have a pet named **{pet_name}**!", ephemeral=True)
                return
        else:
            pet1 = user1_pets[0]
        
        pet1_info = PET_TYPES.get(pet1["type"])
        if not pet1_info:
            await interaction.response.send_message(f"❌ Error: Unknown pet type '{pet1.get('type')}'!", ephemeral=True)
            return
        
        # Auto-select opponent's first pet
        pet2 = user2_pets[0]
        pet2_info = PET_TYPES.get(pet2["type"])
        if not pet2_info:
            await interaction.response.send_message(f"❌ Error: Opponent has unknown pet type '{pet2.get('type')}'!", ephemeral=True)
            return
        
        check_name = pet_name if pet_name else pet1_info["name"]
        
        # Check cooldown
        if not await can_battle(interaction.user.id, check_name):
            await interaction.response.send_message(f"❌ Your {pet1_info['name']} can only battle once every 3 hours!", ephemeral=True)
            return
        
        # Get display names
        pet1_display = pet1.get("nickname") or pet1_info["name"]
        pet2_display = pet2.get("nickname") or pet2_info["name"]
        
        # Import battle view
        from .battle_view import BattleInviteView
        
        # Create battle invitation embed
        embed = discord.Embed(
            title="🗡️ Battle Challenge!",
            description=f"{interaction.user.mention}'s **{pet1_display}** challenges {user.mention}'s **{pet2_display}**!",
            color=discord.Color.orange()
        )
        
        # Pet 1 stats
        pet1_hp = pet1["level"] * 50 + 100
        pet1_mood = get_pet_mood(pet1)
        pet1_mood_emoji = MOODS[pet1_mood]["emoji"]
        
        embed.add_field(
            name=f"{pet1_info['emoji']} {pet1_display} (Lv. {pet1['level']})",
            value=f"**HP:** {pet1_hp}\n"
                  f"**Rarity:** {pet1['rarity'].title()}\n"
                  f"**Mood:** {pet1_mood_emoji} {pet1_mood.title()}\n"
                  f"**Energy:** {pet1['energy']}/100",
            inline=True
        )
        
        # VS
        embed.add_field(name="⚔️", value="VS", inline=True)
        
        # Pet 2 stats
        pet2_hp = pet2["level"] * 50 + 100
        pet2_mood = get_pet_mood(pet2)
        pet2_mood_emoji = MOODS[pet2_mood]["emoji"]
        
        embed.add_field(
            name=f"{pet2_info['emoji']} {pet2_display} (Lv. {pet2['level']})",
            value=f"**HP:** {pet2_hp}\n"
                  f"**Rarity:** {pet2['rarity'].title()}\n"
                  f"**Mood:** {pet2_mood_emoji} {pet2_mood.title()}\n"
                  f"**Energy:** {pet2['energy']}/100",
            inline=True
        )
        
        embed.set_footer(text=f"{user.display_name}, do you accept this challenge?")
        
        # Create battle invite view
        view = BattleInviteView(interaction.user, user, pet1, pet2, pet1_display, pet2_display)
        
        await interaction.response.send_message(embed=embed, view=view)
        
        # Store message for later updates
        message = await interaction.original_response()
        view.message = message
    
    @app_commands.command(name="petleaderboard", description="View top pets by level")
    async def petleaderboard(self, interaction: discord.Interaction):
        """Display pet leaderboard"""
        leaderboard = await get_pet_leaderboard(10)
        
        if not leaderboard:
            await interaction.response.send_message("❌ No pets found!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🏆 Pet Leaderboard",
            description="Top 10 pets by level",
            color=discord.Color.gold()
        )
        
        for i, (user_id, pet) in enumerate(leaderboard, 1):
            try:
                user = await self.bot.fetch_user(int(user_id))
                pet_info = PET_TYPES.get(pet["type"])
                
                # Skip pets with invalid types
                if not pet_info:
                    logger.warning(f"Skipping pet with unknown type '{pet.get('type')}' in leaderboard")
                    continue
                
                display_name = get_pet_display_name(pet)
                
                embed.add_field(
                    name=f"{i}. {user.display_name}",
                    value=f"{pet_info['emoji']} {display_name} (Lv. {pet['level']}) - {pet['rarity'].title()}",
                    inline=False
                )
            except Exception as e:
                logger.error(f"Failed to fetch user: {e}")
                continue
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="setspawn", description="Set pet spawn channel (Admin only)")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(channel="Channel where pets will spawn (ID, mention, or name)")
    async def setspawn(self, interaction: discord.Interaction, channel: Optional[str] = None):
        """Set spawn channel (Foolproof Rewrite)"""
        target_channel = None
        
        if not channel:
            target_channel = interaction.channel
        else:
            # 1. Try ID
            if channel.isdigit():
                target_channel = interaction.guild.get_channel(int(channel))
                
            # 2. Try Mention <#12345...>
            if not target_channel and channel.startswith('<#') and channel.endswith('>'):
                try:
                    c_id = int(channel[2:-1].replace('!', ''))
                    target_channel = interaction.guild.get_channel(c_id)
                except: pass
                
            # 3. Try Name Search (Case-insensitive)
            if not target_channel:
                clean_name = channel.lstrip('#').lower()
                target_channel = discord.utils.get(interaction.guild.channels, name=clean_name)
                if not target_channel:
                    # Fuzzy/Lower name match fallback
                    target_channel = next((c for c in interaction.guild.channels if c.name.lower() == clean_name), None)

        if not target_channel:
            await interaction.response.send_message(f"❌ Could not find channel '{channel}'. Please provide a valid ID, mention, or exact name.", ephemeral=True)
            return

        # Verify the channel is messageable
        if not hasattr(target_channel, 'send'):
            await interaction.response.send_message(f"❌ {target_channel.mention} is not a valid channel type! It must be a channel that supports messages.", ephemeral=True)
            return
            
        # Save to database
        await set_spawn_channel(interaction.guild_id, target_channel.id)
        
        embed = discord.Embed(
            title="✅ Spawn Channel Set",
            description=f"Pets will now spawn in {target_channel.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text="Users can use /spawn to summon pets (3/4h limit)")
        
        await interaction.response.send_message(embed=embed)
        
        # Trigger immediate spawn
        spawn_data = await create_spawn(interaction.guild.id)
        if spawn_data:
            pet_type = spawn_data["pet_type"]
            is_shiny = spawn_data.get("is_shiny", False)
            pet_info = PET_TYPES[pet_type]
            rarity_color = RARITY_INFO[pet_info["rarity"]]["color"]
            
            spawn_embed = discord.Embed(
                title=f"✨ A Shiny {pet_info['name']} Appeared! ✨" if is_shiny else f"A Wild {pet_info['name']} Appeared!",
                description=f"Use `/catch` to catch it!",
                color=rarity_color
            )
            spawn_embed.add_field(name="Rarity", value=pet_info["rarity"].title(), inline=True)
            
            gif_file = self.get_pet_gif(pet_type)
            if gif_file:
                spawn_embed.set_thumbnail(url=f"attachment://{pet_type}.gif")
                await target_channel.send(embed=spawn_embed, file=gif_file)
            else:
                await target_channel.send(embed=spawn_embed)

    @app_commands.command(name="spawn", description="Spawn a wild pet (3 uses per 4 hours)")
    async def spawn(self, interaction: discord.Interaction):
        """Spawn a wild pet"""
        # Check if channel is the spawn channel
        spawn_channel_data = await get_spawn_channel(interaction.guild_id)
        
        # Robust retrieval of channel_id from dict or object
        assigned_cid = None
        if spawn_channel_data:
            if isinstance(spawn_channel_data, dict):
                assigned_cid = spawn_channel_data.get("channel_id")
            else:
                assigned_cid = getattr(spawn_channel_data, "channel_id", None)

        if not assigned_cid or str(interaction.channel_id) != str(assigned_cid):
            # Get the correct channel mention if set
            channel_mention = "unknown channel"
            if assigned_cid:
                try:
                    channel = interaction.guild.get_channel(int(assigned_cid))
                    if channel:
                        channel_mention = channel.mention
                except:
                    pass
            
            await interaction.response.send_message(f"❌ You can only spawn pets in {channel_mention}!", ephemeral=True)
            return


        # Check cooldown
        can_spawn, remaining = await can_user_spawn(interaction.user.id)
        if not can_spawn:
            time_str = format_time_remaining(remaining)
            await interaction.response.send_message(f"❌ You are on cooldown! You can spawn again in **{time_str}**.\n(Limit: 3 spawns per 4 hours)", ephemeral=True)
            return

        # Spawn the pet
        spawn_data = await create_spawn(interaction.guild_id)
        if not spawn_data:
            await interaction.response.send_message("❌ Failed to spawn pet!", ephemeral=True)
            return
        
        await record_user_spawn(interaction.user.id)
        
        # Create spawn embed
        pet_type = spawn_data["pet_type"]
        is_shiny = spawn_data["is_shiny"]
        pet_info = PET_TYPES[pet_type]
        
        rarity_color = RARITY_INFO[pet_info["rarity"]]["color"]
        title = f"✨ A Shiny {pet_info['name']} Appeared! ✨" if is_shiny else f"A Wild {pet_info['name']} Appeared!"
        
        embed = discord.Embed(
            title=title,
            description=f"Use `/catch` to catch it before it runs away!",
            color=rarity_color
        )
        embed.add_field(name="Rarity", value=pet_info["rarity"].title(), inline=True)
        
        # Add GIF
        gif_file = self.get_pet_gif(pet_type)
        if gif_file:
            embed.set_thumbnail(url=f"attachment://{pet_type}.gif")
            await interaction.response.send_message(f"{interaction.user.mention} summoned a pet!", embed=embed, file=gif_file)
        else:
            await interaction.response.send_message(f"{interaction.user.mention} summoned a pet!", embed=embed)
    



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        elif isinstance(error, app_commands.TransformerError):
            logger.error(f"Transformer error in pet command '{interaction.command.name}': {error}")
            msg = f"❌ Failed to resolve the channel '{error.value}'. Please try selecting it from the list rather than typing its name."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        else:
            logger.error(f"Error in pet command '{interaction.command.name}': {error}", exc_info=True)
            msg = "❌ An error occurred while processing this command."
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pets(bot))
