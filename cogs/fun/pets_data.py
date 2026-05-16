"""
Pets Data Management - Loading and saving pet data to RavenDB
"""
import logging
from datetime import datetime, UTC, timedelta
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Pets.Data')

# ID Prefixes
PETS_PREFIX = "pets"
SPAWNS_PREFIX = "spawns"
USER_SPAWNS_PREFIX = "user_spawns"
REFILLS_PREFIX = "refills"

async def load_pets_data(user_id):
    """Load user pets from RavenDB (supports 'pets' and 'value' schemas)"""
    doc_id = f"{PETS_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if not data:
        return []
        
    # Handle both dictionary and object formats
    if hasattr(data, 'pets'):
        return data.pets or []
    if hasattr(data, 'value'):
        return data.value or []
        
    if isinstance(data, dict):
        return data.get('pets', data.get('value', []))
        
    return []

async def save_pets_data(user_id, pets_list):
    """Save user pets to RavenDB using standard 'pets' field"""
    doc_id = f"{PETS_PREFIX}/{user_id}"
    # Consistently save as 'pets' for future standardization
    await raven_db.save_document(doc_id, {'pets': pets_list})

async def get_spawn_channel(gid):
    return await raven_db.load_document(f"{SPAWNS_PREFIX}/{gid}")

async def set_spawn_channel(gid, cid):
    doc_id = f"{SPAWNS_PREFIX}/{gid}"
    data = await raven_db.load_document(doc_id) or {}
    data.update({'channel_id': str(cid), 'last_spawn': None, 'current_spawn': None})
    await raven_db.save_document(doc_id, data)

async def get_current_spawn(gid):
    data = await raven_db.load_document(f"{SPAWNS_PREFIX}/{gid}")
    if data and data.get("current_spawn"): 
        return {"pet_type": data["current_spawn"], "is_shiny": data.get("is_shiny", False)}
    return None

async def clear_spawn(gid):
    doc_id = f"{SPAWNS_PREFIX}/{gid}"
    await raven_db.patch_document(doc_id, {'current_spawn': None, 'is_shiny': False})

async def save_spawn(gid, pet_type, is_shiny):
    doc_id = f"{SPAWNS_PREFIX}/{gid}"
    data = await raven_db.load_document(doc_id) or {}
    data.update({
        'current_spawn': pet_type,
        'is_shiny': is_shiny,
        'last_spawn': datetime.now(UTC).isoformat()
    })
    await raven_db.save_document(doc_id, data)

async def load_user_spawn_timestamps(user_id):
    doc_id = f"{USER_SPAWNS_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    return data.get('timestamps', []) if data else []

async def save_user_spawn_timestamps(user_id, timestamps):
    doc_id = f"{USER_SPAWNS_PREFIX}/{user_id}"
    await raven_db.save_document(doc_id, {'timestamps': timestamps})

async def load_last_refill(user_id):
    doc_id = f"{REFILLS_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if not data: return None
    last = datetime.fromisoformat(data['last_refill'])
    if last.tzinfo is None: last = last.replace(tzinfo=UTC)
    return last

async def save_last_refill(user_id, iso_str):
    await raven_db.save_document(f"{REFILLS_PREFIX}/{user_id}", {'last_refill': iso_str})
