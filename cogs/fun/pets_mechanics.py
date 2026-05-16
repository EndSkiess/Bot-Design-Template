"""
Pets Mechanics - Feeding, playing, growth, and stat management
"""
import random
import logging
import asyncio
from datetime import datetime, UTC, timedelta
from .pets_data import load_pets_data, save_pets_data, load_user_spawn_timestamps, save_user_spawn_timestamps, load_last_refill, save_last_refill

logger = logging.getLogger('Lilith.Pets.Mechanics')

# Constants
MAX_PETS = 5
SHINY_CHANCE = 0.01
SHINY_STAT_BONUS = 1.2
SHINY_EMOJI_PREFIX = "✨"

# Pet definitions and rarity info (shortened for brevity, full list in original)
PET_TYPES = {
    "dog": {"emoji": "<a:69969jump:1445525121942032465>", "name": "Dog", "rarity": "common", "spawn_weight": 20},
    "cat": {"emoji": "<a:774805kittydance:1445525133048418499>", "name": "Cat", "rarity": "common", "spawn_weight": 20},
    "rabbit": {"emoji": "<a:147931yellowbunny:1445525130607460564>", "name": "Rabbit", "rarity": "common", "spawn_weight": 20},
    "fox": {"emoji": "<:39119foxydealz:1445525112542724216>", "name": "Fox", "rarity": "uncommon", "spawn_weight": 8},
    "panda": {"emoji": "<:17506pandas:1445525108142899350>", "name": "Panda", "rarity": "uncommon", "spawn_weight": 8},
    "raccoon": {"emoji": "<:60997raccoon:1445525119593091202>", "name": "Raccoon", "rarity": "uncommon", "spawn_weight": 9},
    "lion": {"emoji": "<a:6201lionrun:1445525105374527488>", "name": "Lion", "rarity": "rare", "spawn_weight": 3},
    "wolf": {"emoji": "<:55469wolf:1445525117403795639>", "name": "Wolf", "rarity": "rare", "spawn_weight": 4},
    "eagle": {"emoji": "<:4396cursedeaglestare:1445525098667704532>", "name": "Eagle", "rarity": "rare", "spawn_weight": 3},
    "penguin": {"emoji": "<a:pengutablesmash:1445524691019235518>", "name": "Penguin", "rarity": "rare", "spawn_weight": 3},
    "cyclops": {"emoji": "<:cyclops:1445524684920721528>", "name": "Cyclops", "rarity": "rare", "spawn_weight": 3},
    "dragon": {"emoji": "<:978412nikkiloong:1445530080922173481>", "name": "Dragon", "rarity": "epic", "spawn_weight": 1},
    "unicorn": {"emoji": "<:851525fireunicorn:1445525135682703431>", "name": "Unicorn", "rarity": "epic", "spawn_weight": 1},
    "shark": {"emoji": "<a:74473jeffult:1445525128711635206>", "name": "Shark", "rarity": "epic", "spawn_weight": 1},
    "ancient_dragon": {"emoji": "<:51058blueflamedragon:1445525115029688484>", "name": "Ancient Dragon", "rarity": "legendary", "spawn_weight": 0.75},
    "trex": {"emoji": "<a:1092trexparty:1445525096813957130>", "name": "T-Rex", "rarity": "legendary", "spawn_weight": 0.75},
    "griffin": {"emoji": "<:bloody:1445524682513191065>", "name": "Griffin", "rarity": "legendary", "spawn_weight": 0.75},
    "phoenix": {"emoji": "<a:4726phoenix:1445525103323644005>", "name": "Phoenix", "rarity": "mythical", "spawn_weight": 0.5},
    "cerberus": {"emoji": "<:3headdog:1445528975022620722>", "name": "Cerberus", "rarity": "mythical", "spawn_weight": 0.5},
    "hydra": {"emoji": "<:image:1445524687781363963>", "name": "Hydra", "rarity": "mythical", "spawn_weight": 0.5}
}

RARITY_INFO = {
    "common": {"color": 0x808080, "xp_bonus": 1.0, "stat_bonus": 1.0},
    "uncommon": {"color": 0x00FF00, "xp_bonus": 1.2, "stat_bonus": 1.1},
    "rare": {"color": 0x0099FF, "xp_bonus": 1.5, "stat_bonus": 1.3},
    "epic": {"color": 0x9B59B6, "xp_bonus": 2.0, "stat_bonus": 1.5},
    "legendary": {"color": 0xFFD700, "xp_bonus": 3.0, "stat_bonus": 2.0},
    "mythical": {"color": 0xFF0000, "xp_bonus": 5.0, "stat_bonus": 3.0}
}

RARITY_ABILITIES = {
    "mythical": {"name": "Cosmic Power", "desc": "3x XP from all sources", "xp_mult": 3.0},
    "legendary": {"name": "Ancient Wisdom", "desc": "2x XP from battles", "battle_xp_mult": 2.0},
    "epic": {"name": "Rapid Recovery", "desc": "Energy regenerates 50% faster", "energy_regen_mult": 1.5},
    "rare": {"name": "Efficient Metabolism", "desc": "Hunger decreases 25% slower", "hunger_decay_mult": 0.75},
    "uncommon": {"name": "Quick Learner", "desc": "+20% XP from training", "train_xp_mult": 1.2},
    "common": {"name": "Loyal Companion", "desc": "+10% happiness from playing", "play_bonus": 1.1}
}

MOODS = {
    "happy": {"threshold": 70, "emoji": "😊", "battle_mult": 1.15, "desc": "Happy"},
    "content": {"threshold": 40, "emoji": "😐", "battle_mult": 1.0, "desc": "Content"},
    "sad": {"threshold": 20, "emoji": "😢", "battle_mult": 0.9, "desc": "Sad"},
    "neglected": {"threshold": 0, "emoji": "😭", "battle_mult": 0.75, "desc": "Neglected"}
}

EVOLUTION_LEVELS = {1: 25, 2: 50, 3: 100}

def xp_for_next_level(level): return 100 * level

def get_pet_mood(pet):
    avg_stat = (pet["hunger"] + pet["happiness"] + pet["energy"]) / 3
    if avg_stat >= MOODS["happy"]["threshold"]: return "happy"
    if avg_stat >= MOODS["content"]["threshold"]: return "content"
    if avg_stat >= MOODS["sad"]["threshold"]: return "sad"
    return "neglected"

async def update_pet_stats(pet, user_id=None, bot=None):
    if "last_updated" not in pet:
        pet["last_updated"] = datetime.now(UTC).isoformat()
        return True
    
    last_updated = datetime.fromisoformat(pet["last_updated"])
    now = datetime.now(UTC)
    hours_elapsed = (now - last_updated).total_seconds() / 3600
    
    if hours_elapsed < 0.1: return False
    
    rarity = pet.get("rarity", "common")
    ability = RARITY_ABILITIES.get(rarity, {})
    
    hunger_decay_rate = 10 / 6
    hunger_mult = ability.get("hunger_decay_mult", 1.0)
    pet["hunger"] = max(0, pet["hunger"] - int(hours_elapsed * hunger_decay_rate * hunger_mult))
    
    happiness_decay_rate = 10 / 6
    pet["happiness"] = max(0, pet["happiness"] - int(hours_elapsed * happiness_decay_rate))
    
    energy_regen_rate = 15
    energy_mult = ability.get("energy_regen_mult", 1.0)
    pet["energy"] = min(100, pet["energy"] + int(hours_elapsed * energy_regen_rate * energy_mult))
    
    pet["last_updated"] = now.isoformat()
    return True

async def get_user_pets(user_id, bot=None):
    user_pets = await load_pets_data(user_id)
    updated = False
    for pet in user_pets:
        if await update_pet_stats(pet, user_id, bot):
            updated = True
    
    if updated:
        await save_pets_data(user_id, user_pets)
    return user_pets

async def get_user_pet_by_name(user_id, pet_name):
    user_pets = await get_user_pets(user_id)
    pet_name_lower = pet_name.lower()
    for pet in user_pets:
        pet_info = PET_TYPES.get(pet["type"])
        if pet_info and pet_info["name"].lower() == pet_name_lower: return pet
        if pet.get("nickname") and pet["nickname"].lower() == pet_name_lower: return pet
    return None

async def create_pet(user_id, pet_type, is_shiny=False, nickname=None):
    user_pets = await load_pets_data(user_id)
    pet_info = PET_TYPES[pet_type]
    
    existing = next((p for p in user_pets if p["type"] == pet_type), None)
    if existing:
        xp_gain = int(200 * RARITY_INFO[pet_info["rarity"]]["xp_bonus"])
        old_level = existing["level"]
        existing["xp"] += xp_gain
        while existing["xp"] >= xp_for_next_level(existing["level"]):
            existing["xp"] -= xp_for_next_level(existing["level"])
            existing["level"] += 1
        await save_pets_data(user_id, user_pets)
        return {"status": "leveled_up", "pet": existing, "old_level": old_level, "xp_gained": xp_gain}
    
    if len(user_pets) >= MAX_PETS:
        return {"status": "max_reached", "max_pets": MAX_PETS, "current_pets": user_pets}
    
    new_pet = {
        "type": pet_type, "rarity": pet_info["rarity"], "level": 1, "xp": 0, "total_xp": 0,
        "hunger": 100, "happiness": 100, "energy": 100, "last_fed": None, "last_played": None,
        "last_trained": None, "last_battled": None, "last_updated": datetime.now(UTC).isoformat(),
        "caught_at": datetime.now(UTC).isoformat(), "nickname": nickname, "is_shiny": is_shiny,
        "evolution_level": 0, "achievements": ["first_catch"], "battle_wins": 0, "battle_losses": 0,
        "battle_streak": 0, "times_fed": 0, "times_trained": 0
    }
    if is_shiny:
        for s in ["hunger", "happiness", "energy"]: new_pet[s] = int(100 * SHINY_STAT_BONUS)
    
    user_pets.append(new_pet)
    await save_pets_data(user_id, user_pets)
    return {"status": "new", "pet": new_pet}

async def can_user_spawn(user_id):
    timestamps = await load_user_spawn_timestamps(user_id)
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=4)
    
    valid = []
    for ts in timestamps:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None: dt = dt.replace(tzinfo=UTC)
        if dt > cutoff: valid.append(ts)
    
    if len(valid) < 3: return True, None
    
    oldest = min([datetime.fromisoformat(ts).replace(tzinfo=UTC) if datetime.fromisoformat(ts).tzinfo is None else datetime.fromisoformat(ts) for ts in valid])
    rem = (oldest + timedelta(hours=4) - now).total_seconds()
    return False, rem

async def record_user_spawn(user_id):
    timestamps = await load_user_spawn_timestamps(user_id)
    now = datetime.now(UTC)
    timestamps.append(now.isoformat())
    # Cleanup in save logic usually, or here
    cutoff = now - timedelta(hours=4)
    new_ts = [ts for ts in timestamps if datetime.fromisoformat(ts).replace(tzinfo=UTC) > cutoff]
    await save_user_spawn_timestamps(user_id, new_ts)
