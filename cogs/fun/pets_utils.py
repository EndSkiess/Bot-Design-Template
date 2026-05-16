"""
Pet system utilities - Async data management for virtual pets with MongoDB
"""
import logging
import asyncio
from datetime import datetime, UTC, timedelta
import random
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Pets')

# Constants
MAX_PETS = 5

# ID Prefixes (mimicking collections)
PETS_PREFIX = "pets"
SPAWNS_PREFIX = "spawns"
USER_SPAWNS_PREFIX = "user_spawns"
REFILLS_PREFIX = "refills"

# Pet definitions with rarity and spawn chances
PET_TYPES = {
    # Common (60%)
    "dog": {"emoji": "<a:69969jump:1445525121942032465>", "name": "Dog", "rarity": "common", "spawn_weight": 20},
    "cat": {"emoji": "<a:774805kittydance:1445525133048418499>", "name": "Cat", "rarity": "common", "spawn_weight": 20},
    "rabbit": {"emoji": "<a:147931yellowbunny:1445525130607460564>", "name": "Rabbit", "rarity": "common", "spawn_weight": 20},
    
    # Uncommon (25%)
    "fox": {"emoji": "<:39119foxydealz:1445525112542724216>", "name": "Fox", "rarity": "uncommon", "spawn_weight": 8},
    "panda": {"emoji": "<:17506pandas:1445525108142899350>", "name": "Panda", "rarity": "uncommon", "spawn_weight": 8},
    "raccoon": {"emoji": "<:60997raccoon:1445525119593091202>", "name": "Raccoon", "rarity": "uncommon", "spawn_weight": 9},
    
    # Rare (10%)
    "lion": {"emoji": "<a:6201lionrun:1445525105374527488>", "name": "Lion", "rarity": "rare", "spawn_weight": 3},
    "wolf": {"emoji": "<:55469wolf:1445525117403795639>", "name": "Wolf", "rarity": "rare", "spawn_weight": 4},
    "eagle": {"emoji": "<:4396cursedeaglestare:1445525098667704532>", "name": "Eagle", "rarity": "rare", "spawn_weight": 3},
    "penguin": {"emoji": "<a:pengutablesmash:1445524691019235518>", "name": "Penguin", "rarity": "rare", "spawn_weight": 3},
    "cyclops": {"emoji": "<:cyclops:1445524684920721528>", "name": "Cyclops", "rarity": "rare", "spawn_weight": 3},
    
    # Epic (3%)
    "dragon": {"emoji": "<:978412nikkiloong:1445530080922173481>", "name": "Dragon", "rarity": "epic", "spawn_weight": 1},
    "unicorn": {"emoji": "<:851525fireunicorn:1445525135682703431>", "name": "Unicorn", "rarity": "epic", "spawn_weight": 1},
    "shark": {"emoji": "<a:74473jeffult:1445525128711635206>", "name": "Shark", "rarity": "epic", "spawn_weight": 1},
    
    # Legendary (1.5%)
    "ancient_dragon": {"emoji": "<:51058blueflamedragon:1445525115029688484>", "name": "Ancient Dragon", "rarity": "legendary", "spawn_weight": 0.75},
    "trex": {"emoji": "<a:1092trexparty:1445525096813957130>", "name": "T-Rex", "rarity": "legendary", "spawn_weight": 0.75},
    "griffin": {"emoji": "<:bloody:1445524682513191065>", "name": "Griffin", "rarity": "legendary", "spawn_weight": 0.75},
    
    # Mythical (0.5%)
    "phoenix": {"emoji": "<a:4726phoenix:1445525103323644005>", "name": "Phoenix", "rarity": "mythical", "spawn_weight": 0.5},
    "cerberus": {"emoji": "<:3headdog:1445528975022620722>", "name": "Cerberus", "rarity": "mythical", "spawn_weight": 0.5},
    "hydra": {"emoji": "<:image:1445524687781363963>", "name": "Hydra", "rarity": "mythical", "spawn_weight": 0.5}
}

# Rarity colors and bonuses
RARITY_INFO = {
    "common": {"color": 0x808080, "xp_bonus": 1.0, "stat_bonus": 1.0},
    "uncommon": {"color": 0x00FF00, "xp_bonus": 1.2, "stat_bonus": 1.1},
    "rare": {"color": 0x0099FF, "xp_bonus": 1.5, "stat_bonus": 1.3},
    "epic": {"color": 0x9B59B6, "xp_bonus": 2.0, "stat_bonus": 1.5},
    "legendary": {"color": 0xFFD700, "xp_bonus": 3.0, "stat_bonus": 2.0},
    "mythical": {"color": 0xFF0000, "xp_bonus": 5.0, "stat_bonus": 3.0}
}

# Rarity-based passive abilities
RARITY_ABILITIES = {
    "mythical": {"name": "Cosmic Power", "desc": "3x XP from all sources", "xp_mult": 3.0},
    "legendary": {"name": "Ancient Wisdom", "desc": "2x XP from battles", "battle_xp_mult": 2.0},
    "epic": {"name": "Rapid Recovery", "desc": "Energy regenerates 50% faster", "energy_regen_mult": 1.5},
    "rare": {"name": "Efficient Metabolism", "desc": "Hunger decreases 25% slower", "hunger_decay_mult": 0.75},
    "uncommon": {"name": "Quick Learner", "desc": "+20% XP from training", "train_xp_mult": 1.2},
    "common": {"name": "Loyal Companion", "desc": "+10% happiness from playing", "play_bonus": 1.1}
}

# Type advantages for battles
TYPE_ADVANTAGES = {
    "dragon": ["lion", "wolf", "eagle", "trex", "cyclops"],
    "ancient_dragon": ["dragon", "lion", "wolf", "eagle", "trex", "griffin"],
    "phoenix": ["dragon", "ancient_dragon", "eagle", "hydra"],
    "trex": ["lion", "wolf", "dog", "cat", "penguin"],
    "lion": ["fox", "rabbit", "raccoon", "dog", "cat"],
    "wolf": ["rabbit", "fox", "raccoon", "penguin"],
    "eagle": ["rabbit", "raccoon", "fox", "penguin"],
    "shark": ["dog", "cat", "rabbit", "penguin"],
    "unicorn": ["wolf", "lion", "cyclops"],
    "fox": ["rabbit"],
    "panda": ["rabbit"],
    "raccoon": [],
    "penguin": [],
    "cyclops": ["lion", "wolf"],
    "griffin": ["lion", "wolf", "eagle"],
    "cerberus": ["ghost", "skeleton", "human"],
    "hydra": ["dragon", "ancient_dragon"]
}

# Pet achievements
ACHIEVEMENTS = {
    "first_catch": {"name": "First Companion", "desc": "Caught for the first time", "emoji": "🎉"},
    "level_10": {"name": "Novice Trainer", "desc": "Reached level 10", "emoji": "📈"},
    "level_25": {"name": "Expert Trainer", "desc": "Reached level 25", "emoji": "⭐"},
    "level_50": {"name": "Master Trainer", "desc": "Reached level 50", "emoji": "🏆"},
    "level_100": {"name": "Legendary Trainer", "desc": "Reached level 100", "emoji": "👑"},
    "battle_won": {"name": "First Victory", "desc": "Won first battle", "emoji": "⚔️"},
    "battle_streak_5": {"name": "Winning Streak", "desc": "Won 5 battles in a row", "emoji": "🔥"},
    "battle_streak_10": {"name": "Unstoppable", "desc": "Won 10 battles in a row", "emoji": "💥"},
    "fully_fed": {"name": "Well Fed", "desc": "Fed 50 times", "emoji": "🍖"},
    "well_trained": {"name": "Disciplined", "desc": "Trained 50 times", "emoji": "💪"},
    "evolved_once": {"name": "Evolution", "desc": "Evolved to ⭐", "emoji": "✨"},
    "max_evolution": {"name": "Ultimate Form", "desc": "Reached ⭐⭐⭐", "emoji": "🌟"}
}

# Evolution thresholds
EVOLUTION_LEVELS = {
    1: 25,   
    2: 50,   
    3: 100   
}

# Mood definitions
MOODS = {
    "happy": {"threshold": 70, "emoji": "😊", "battle_mult": 1.15, "desc": "Happy"},
    "content": {"threshold": 40, "emoji": "😐", "battle_mult": 1.0, "desc": "Content"},
    "sad": {"threshold": 20, "emoji": "😢", "battle_mult": 0.9, "desc": "Sad"},
    "neglected": {"threshold": 0, "emoji": "😭", "battle_mult": 0.75, "desc": "Neglected"}
}

# Shiny variants (rare spawns)
SHINY_CHANCE = 0.01
SHINY_STAT_BONUS = 1.2
SHINY_EMOJI_PREFIX = "✨"

async def load_pets_data(user_id):
    """Load user pets from RavenDB with error handling (supports 'pets' and 'value' schemas)"""
    doc_id = f"{PETS_PREFIX}/{user_id}"
    try:
        data = await raven_db.load_document(doc_id)
        if not data:
            return []
            
        # 1. Handle cases where RavenDB might return an object with attributes
        if hasattr(data, 'pets'):
            return data.pets or []
        if hasattr(data, 'value'):
            return data.value or []
            
        # 2. Handle dictionary responses (RavenDB Studio JSON structure)
        if isinstance(data, dict):
            # Check 'pets' first, then fallback to 'value'
            return data.get('pets', data.get('value', []))
            
        return []
    except Exception as e:
        logger.error(f"Failed to load pet data for {user_id}: {e}")
        return []

async def save_pets_data(user_id, pets_list):
    """Save user pets to RavenDB using standard 'pets' field"""
    doc_id = f"{PETS_PREFIX}/{user_id}"
    # We always save as 'pets' for new/updated docs, but load handles both
    await raven_db.save_document(doc_id, {'pets': pets_list})

async def can_user_spawn(user_id):
    """Check if user can spawn a pet (3 times per 4 hours)"""
    doc_id = f"{USER_SPAWNS_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if not data:
        return True, None
    
    timestamps = data.get('timestamps', [])
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=4)
    
    # Ensure items are datetime objects before comparing
    valid_timestamps = []
    for ts in timestamps:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        if dt > cutoff:
            valid_timestamps.append(ts)
    
    if len(valid_timestamps) < 3:
        return True, None
    
    # Safely get the oldest timestamp to calculate cooldown
    times = []
    for ts in valid_timestamps:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        times.append(dt)
        
    if not times:
        return True, None
        
    oldest_dt = min(times)
    reset_time = oldest_dt + timedelta(hours=4)
    remaining = (reset_time - now).total_seconds()
    
    return False, remaining

async def record_user_spawn(user_id):
    """Record a user spawn"""
    doc_id = f"{USER_SPAWNS_PREFIX}/{user_id}"
    now = datetime.now(UTC)
    cutoff = now - timedelta(hours=4)
    
    data = await raven_db.load_document(doc_id)
    timestamps = data.get('timestamps', []) if data else []
    
    # Add new and clean up old
    timestamps.append(now.isoformat())
    new_timestamps = []
    for ts in timestamps:
        dt = datetime.fromisoformat(ts)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        if dt > cutoff:
            new_timestamps.append(ts)
    
    await raven_db.save_document(doc_id, {'timestamps': new_timestamps})

def get_random_pet():
    pets = list(PET_TYPES.keys())
    weights = [PET_TYPES[p]["spawn_weight"] for p in pets]
    return random.choices(pets, weights=weights)[0]

def check_evolution(pet):
    if "evolution_level" not in pet:
        pet["evolution_level"] = 0
    
    level = pet.get("level", 1)
    current_evo = pet.get("evolution_level", 0)
    
    new_evo = current_evo
    for evo_level, required_level in EVOLUTION_LEVELS.items():
        if level >= required_level and current_evo < evo_level:
            new_evo = evo_level
    
    if new_evo > current_evo:
        pet["evolution_level"] = new_evo
        check_and_award_achievements(pet)
        return True
    return False

async def send_low_energy_warning(bot, user_id, pet):
    try:
        user = await bot.fetch_user(int(user_id))
        pet_info = PET_TYPES.get(pet["type"])
        if not pet_info: return
        
        pet_name = pet.get("nickname") or pet_info["name"]
        
        import discord
        embed = discord.Embed(
            title="⚠️ Pet Warning: Critical Energy Level!",
            description=f"Your pet **{pet_name}** is in critical condition!",
            color=discord.Color.red()
        )
        embed.add_field(
            name=f"{pet_info['emoji']} {pet_name}",
            value=f"⚡ **Energy: {pet['energy']}/100** 🔴\n💚 Hunger: {pet['hunger']}/100\n😊 Happiness: {pet['happiness']}/100",
            inline=False
        )
        embed.set_footer(text="Energy regenerates at 15 per hour. Take care of your pet!")
        await user.send(embed=embed)
    except Exception as e:
        logger.error(f"Failed to send DM warning: {e}")

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

async def update_pet_stats(pet, user_id=None, bot=None):
    if "last_updated" not in pet:
        pet["last_updated"] = datetime.now(UTC).isoformat()
        return True
    
    last_updated = datetime.fromisoformat(pet["last_updated"])
    if last_updated.tzinfo is None:
        last_updated = last_updated.replace(tzinfo=UTC)
        
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
    
    if user_id and bot and pet["energy"] < 10:
        last_warn = pet.get("last_warning")
        if not last_warn or (now - datetime.fromisoformat(last_warn)).total_seconds() > 86400:
            asyncio.create_task(send_low_energy_warning(bot, user_id, pet))
            pet["last_warning"] = now.isoformat()
    return True

def get_pet_mood(pet):
    avg_stat = (pet["hunger"] + pet["happiness"] + pet["energy"]) / 3
    if avg_stat >= MOODS["happy"]["threshold"]: return "happy"
    if avg_stat >= MOODS["content"]["threshold"]: return "content"
    if avg_stat >= MOODS["sad"]["threshold"]: return "sad"
    return "neglected"

def get_pet_display_name(pet):
    pet_info = PET_TYPES.get(pet["type"])
    if not pet_info: return "Unknown"
    nickname = pet.get("nickname")
    if nickname: return f"{nickname} ({pet_info['name']})"
    if pet.get("is_shiny", False): return f"{SHINY_EMOJI_PREFIX} {pet_info['name']}"
    return pet_info["name"]

def get_evolution_stars(evo_level):
    return "⭐" * evo_level if evo_level > 0 else ""

def check_and_award_achievements(pet, action=None):
    if "achievements" not in pet: pet["achievements"] = []
    new_ach = []
    level = pet.get("level", 1)
    for l in [10, 25, 50, 100]:
        key = f"level_{l}"
        if level >= l and key not in pet["achievements"]:
            pet["achievements"].append(key); new_ach.append(key)
    
    evo = pet.get("evolution_level", 0)
    if evo >= 1 and "evolved_once" not in pet["achievements"]:
        pet["achievements"].append("evolved_once"); new_ach.append("evolved_once")
    if evo >= 3 and "max_evolution" not in pet["achievements"]:
        pet["achievements"].append("max_evolution"); new_ach.append("max_evolution")
        
    if action == "battle_won" and "battle_won" not in pet["achievements"]:
        pet["achievements"].append("battle_won"); new_ach.append("battle_won")
        
    streak = pet.get("battle_streak", 0)
    if streak >= 5 and "battle_streak_5" not in pet["achievements"]:
        pet["achievements"].append("battle_streak_5"); new_ach.append("battle_streak_5")
    if streak >= 10 and "battle_streak_10" not in pet["achievements"]:
        pet["achievements"].append("battle_streak_10"); new_ach.append("battle_streak_10")
        
    if pet.get("times_fed", 0) >= 50 and "fully_fed" not in pet["achievements"]:
        pet["achievements"].append("fully_fed"); new_ach.append("fully_fed")
    if pet.get("times_trained", 0) >= 50 and "well_trained" not in pet["achievements"]:
        pet["achievements"].append("well_trained"); new_ach.append("well_trained")
    return new_ach

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

async def remove_pet(user_id, pet_name):
    user_pets = await load_pets_data(user_id)
    pet_name_lower = pet_name.lower()
    removed = None
    for i, pet in enumerate(user_pets):
        info = PET_TYPES.get(pet["type"])
        if (info and info["name"].lower() == pet_name_lower) or ((pet.get("nickname") or "").lower() == pet_name_lower):
            removed = user_pets.pop(i); break
    if not removed: return {"status": "not_found", "pet_name": pet_name}
    await save_pets_data(user_id, user_pets)
    return {"status": "removed", "pet": removed}

async def can_feed(user_id, pet_name):
    pet = await get_user_pet_by_name(user_id, pet_name)
    if not pet: return False
    if not pet.get("last_fed"): return True
    since = datetime.now(UTC) - datetime.fromisoformat(pet["last_fed"])
    return since >= timedelta(hours=1)

async def can_play(user_id, pet_name):
    pet = await get_user_pet_by_name(user_id, pet_name)
    if not pet: return False
    if not pet.get("last_played"): return True
    since = datetime.now(UTC) - datetime.fromisoformat(pet["last_played"])
    return since >= timedelta(hours=1)

async def can_train(user_id, pet_name):
    pet = await get_user_pet_by_name(user_id, pet_name)
    if not pet or pet.get("energy", 0) < 20: return False
    if not pet.get("last_trained"): return True
    since = datetime.now(UTC) - datetime.fromisoformat(pet["last_trained"])
    return since >= timedelta(hours=2)

async def can_battle(user_id, pet_name):
    pet = await get_user_pet_by_name(user_id, pet_name)
    if not pet or pet.get("energy", 0) < 30: return False
    if not pet.get("last_battled"): return True
    since = datetime.now(UTC) - datetime.fromisoformat(pet["last_battled"])
    return since >= timedelta(hours=3)

async def feed_pet(user_id, pet_name=None):
    user_pets = await load_pets_data(user_id)
    target = None
    if pet_name:
        pet_name_l = pet_name.lower()
        for p in user_pets:
            info = PET_TYPES.get(p["type"])
            if (info and info["name"].lower() == pet_name_l) or ((p.get("nickname") or "").lower() == pet_name_l):
                target = p; break
    else:
        target = user_pets[0] if user_pets else None
    
    if not target: return None
    target["hunger"] = min(100, target["hunger"] + 30)
    target["last_fed"] = datetime.now(UTC).isoformat()
    target["times_fed"] = target.get("times_fed", 0) + 1
    check_and_award_achievements(target)
    await save_pets_data(user_id, user_pets)
    return target["hunger"]

async def play_with_pet(user_id, pet_name=None):
    user_pets = await load_pets_data(user_id)
    target = None
    if pet_name:
        pet_name_l = pet_name.lower()
        for p in user_pets:
            info = PET_TYPES.get(p["type"])
            if (info and info["name"].lower() == pet_name_l) or ((p.get("nickname") or "").lower() == pet_name_l):
                target = p; break
    else:
        target = user_pets[0] if user_pets else None
    
    if not target: return None
    mult = RARITY_ABILITIES.get(target.get("rarity", "common"), {}).get("play_bonus", 1.0)
    target["happiness"] = min(100, target["happiness"] + int(30 * mult))
    target["last_played"] = datetime.now(UTC).isoformat()
    await save_pets_data(user_id, user_pets)
    return target["happiness"]

async def can_refill_all(user_id):
    doc_id = f"{REFILLS_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if not data: return True, None
    last = datetime.fromisoformat(data['last_refill'])
    if last.tzinfo is None: last = last.replace(tzinfo=UTC)
    now = datetime.now(UTC)
    if now - last >= timedelta(hours=24): return True, None
    rem = (last + timedelta(hours=24) - now).total_seconds()
    return False, rem

async def refill_all_pets(user_id):
    user_pets = await get_user_pets(user_id)
    now_dt = datetime.now(UTC)
    now = now_dt.isoformat()
    for pet in user_pets:
        for s in ["hunger", "happiness", "energy"]: pet[s] = 100
        pet["last_fed"] = pet["last_played"] = pet["last_updated"] = now
        pet["times_fed"] = pet.get("times_fed", 0) + 1
        check_and_award_achievements(pet)
    await save_pets_data(user_id, user_pets)
    await raven_db.save_document(f"{REFILLS_PREFIX}/{user_id}", {'last_refill': now})
    return user_pets

async def train_pet(user_id, pet_name=None):
    user_pets = await load_pets_data(user_id)
    target = None
    if pet_name:
        pet_name_l = pet_name.lower()
        for p in user_pets:
            info = PET_TYPES.get(p["type"])
            if (info and info["name"].lower() == pet_name_l) or ((p.get("nickname") or "").lower() == pet_name_l):
                target = p; break
    else:
        target = user_pets[0] if user_pets else None
    
    if not target or target["energy"] < 20: return None
    target["energy"] -= 20
    rarity = target.get("rarity", "common")
    ability = RARITY_ABILITIES.get(rarity, {})
    xp_gain = int(random.randint(50, 100) * RARITY_INFO[rarity]["xp_bonus"] * ability.get("train_xp_mult", 1.0) * ability.get("xp_mult", 1.0))
    
    target["xp"] += xp_gain
    target["total_xp"] = target.get("total_xp", 0) + xp_gain
    target["last_trained"] = datetime.now(UTC).isoformat()
    target["times_trained"] = target.get("times_trained", 0) + 1
    
    old_lv = target["level"]
    while target["xp"] >= xp_for_next_level(target["level"]):
        target["xp"] -= xp_for_next_level(target["level"]); target["level"] += 1
    check_evolution(target); check_and_award_achievements(target)
    await save_pets_data(user_id, user_pets)
    return (xp_gain, target["level"], old_lv)

def xp_for_next_level(level): return 100 * level

async def battle_pets(u1, u2, n1=None, n2=None):
    p1s = await load_pets_data(u1); p2s = await load_pets_data(u2)
    pet1 = None; pet2 = None
    
    if n1:
        n1l = n1.lower()
        for p in p1s:
            info = PET_TYPES.get(p["type"])
            if (info and info["name"].lower() == n1l) or ((p.get("nickname") or "").lower() == n1l):
                pet1 = p; break
    else: pet1 = p1s[0] if p1s else None
    
    if n2:
        n2l = n2.lower()
        for p in p2s:
            info = PET_TYPES.get(p["type"])
            if (info and info["name"].lower() == n2l) or ((p.get("nickname") or "").lower() == n2l):
                pet2 = p; break
    else: pet2 = p2s[0] if p2s else None
    
    if not pet1 or not pet2: return None
    
    def gp(p):
        evo = 1.0 + (p.get("evolution_level", 0) * 0.2)
        mood = MOODS[get_pet_mood(p)]["battle_mult"]
        shiny = SHINY_STAT_BONUS if p.get("is_shiny", False) else 1.0
        return int(p["level"] * 10 * RARITY_INFO[p["rarity"]]["stat_bonus"] * (p["energy"]/100) * evo * mood * shiny)
    
    pw1 = gp(pet1) + random.randint(-10, 10); pw2 = gp(pet2) + random.randint(-10, 10)
    adv1 = pet2["type"] in TYPE_ADVANTAGES.get(pet1["type"], []); adv2 = pet1["type"] in TYPE_ADVANTAGES.get(pet2["type"], [])
    if adv1: pw1 = int(pw1 * 1.3); 
    if adv2: pw2 = int(pw2 * 1.3)
    
    cr1 = pet1["happiness"] > 80 and random.random() < 0.15; cr2 = pet2["happiness"] > 80 and random.random() < 0.15
    if cr1: pw1 = int(pw1 * 1.5); 
    if cr2: pw2 = int(pw2 * 1.5)
    
    win = pet1 if pw1 > pw2 else pet2; los = pet2 if win == pet1 else pet1
    for p in [pet1, pet2]:
        for k in ["wins", "losses", "streak"]:
            key = f"battle_{k}"
            if key not in p: p[key] = 0
            
    win["battle_wins"] += 1; win["battle_streak"] += 1; los["battle_losses"] += 1; los["battle_streak"] = 0
    ability = RARITY_ABILITIES.get(win.get("rarity", "common"), {})
    xp = int((100 + min(win["battle_streak"]*10, 100)) * RARITY_INFO[win["rarity"]]["xp_bonus"] * ability.get("battle_xp_mult", 1.0) * ability.get("xp_mult", 1.0))
    win["xp"] += xp; win["total_xp"] = win.get("total_xp", 0) + xp
    win["last_battled"] = los["last_battled"] = datetime.now(UTC).isoformat()
    
    old_lv = win["level"]
    while win["xp"] >= xp_for_next_level(win["level"]):
        win["xp"] -= xp_for_next_level(win["level"]); win["level"] += 1
    evo_done = check_evolution(win); check_and_award_achievements(win, "battle_won")
    await save_pets_data(u1, p1s); await save_pets_data(u2, p2s)
    return {"winner_id": str(u1 if win==pet1 else u2), "loser_id": str(u2 if win==pet1 else u1), "power1": pw1, "power2": pw2, "xp_gain": xp, "new_level": win["level"], "old_level": old_lv, "evolved": evo_done}

async def get_pet_leaderboard(limit=10):
    all_user_docs = await raven_db.get_all_in_collection(PETS_PREFIX, limit=500)
    
    flattened_pets = []
    for doc in all_user_docs:
        uid = doc['@metadata']['@id'].split('/')[-1]
        for pet in doc.get('pets', []):
            flattened_pets.append((uid, pet))
    
    flattened_pets.sort(key=lambda x: (x[1].get('level', 1), x[1].get('total_xp', 0)), reverse=True)
    return flattened_pets[:limit]

async def set_spawn_channel(gid, cid):
    doc_id = f"{SPAWNS_PREFIX}/{gid}"
    data = await raven_db.load_document(doc_id) or {}
    data.update({'channel_id': str(cid), 'last_spawn': None, 'current_spawn': None})
    await raven_db.save_document(doc_id, data)

async def get_spawn_channel(gid):
    return await raven_db.load_document(f"{SPAWNS_PREFIX}/{gid}")

async def create_spawn(gid):
    pet_type = get_random_pet(); is_shiny = random.random() < SHINY_CHANCE
    doc_id = f"{SPAWNS_PREFIX}/{gid}"
    data = await raven_db.load_document(doc_id) or {}
    data.update({
        'current_spawn': pet_type,
        'is_shiny': is_shiny,
        'last_spawn': datetime.now(UTC).isoformat()
    })
    await raven_db.save_document(doc_id, data)
    return {"pet_type": pet_type, "is_shiny": is_shiny}

async def clear_spawn(gid):
    doc_id = f"{SPAWNS_PREFIX}/{gid}"
    await raven_db.patch_document(doc_id, {'current_spawn': None, 'is_shiny': False})

async def get_current_spawn(gid):
    data = await raven_db.load_document(f"{SPAWNS_PREFIX}/{gid}")
    if data and data.get("current_spawn"): return {"pet_type": data["current_spawn"], "is_shiny": data.get("is_shiny", False)}
    return None

async def set_pet_nickname(uid, name, nick):
    pets = await load_pets_data(uid)
    name_l = name.lower()
    target = None
    for p in pets:
        info = PET_TYPES.get(p["type"])
        if (info and info["name"].lower() == name_l) or ((p.get("nickname") or "").lower() == name_l):
            target = p; break
    if not target: return {"status": "not_found", "pet_name": name}
    target["nickname"] = nick if nick and nick.strip() else None
    await save_pets_data(uid, pets)
    return {"status": "success", "pet": target, "nickname": target["nickname"]}

def create_progress_bar(c, m, l=10):
    if m == 0: return "▱" * l
    f = int((c / m) * l); return "▰" * f + "▱" * (l - f)

def format_time_remaining(s):
    if s <= 0: return "Available now"
    h = int(s // 3600); m = int((s % 3600) // 60)
    return f"{h}h {m}m" if h > 0 else (f"{m}m" if m > 0 else "<1m")

def get_cooldown_info(last_iso, cd_h):
    if not last_iso: return {"ready": True, "remaining": "Available now"}
    since = datetime.now(UTC) - datetime.fromisoformat(last_iso)
    if since >= timedelta(hours=cd_h): return {"ready": True, "remaining": "Available now"}
    rem = (timedelta(hours=cd_h) - since).total_seconds()
    return {"ready": False, "remaining": format_time_remaining(rem)}

def get_stat_color_indicator(v):
    if v >= 70: return "🟢"
    if v >= 40: return "🟡"
    return "🔴"
