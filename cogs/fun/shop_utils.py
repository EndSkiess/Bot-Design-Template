"""
Shop system utilities - Async data management for shop items and user inventories using MongoDB
"""
import logging
from datetime import datetime, UTC
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Shop')

SHOP_CONFIG_ID = "config/shop"
INVENTORIES_PREFIX = "inventories"

async def load_shop_items():
    """Load shop items from RavenDB"""
    data = await raven_db.load_document(SHOP_CONFIG_ID)
    if not data:
        # If not in DB, return empty structure
        return {"items": {}}
    return data

async def save_shop_items(data):
    """Save shop items to RavenDB"""
    await raven_db.save_document(SHOP_CONFIG_ID, data)

async def get_user_inventory(user_id):
    """Get user's inventory from RavenDB"""
    doc_id = f"{INVENTORIES_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        data = {
            "items": {},
            "active_perks": {},
            "badges": []
        }
        await raven_db.save_document(doc_id, data)
    
    return data

async def set_user_inventory(user_id, inventory):
    """Set user's inventory in RavenDB"""
    doc_id = f"{INVENTORIES_PREFIX}/{user_id}"
    await raven_db.save_document(doc_id, inventory)

async def add_item_to_inventory(user_id, item_id, quantity=1):
    """Add item to user's inventory"""
    inventory = await get_user_inventory(user_id)
    shop_data = await load_shop_items()
    item = shop_data["items"].get(item_id)
    
    if not item:
        return False
    
    if item_id not in inventory["items"]:
        inventory["items"][item_id] = {
            "quantity": 0,
            "purchased_at": datetime.now(UTC).isoformat()
        }
        
        # Add uses for consumable items
        if item.get("uses"):
            inventory["items"][item_id]["uses_remaining"] = item["uses"]
    
    inventory["items"][item_id]["quantity"] += quantity
    await set_user_inventory(user_id, inventory)
    return True

async def remove_item_from_inventory(user_id, item_id, quantity=1):
    """Remove item from user's inventory"""
    inventory = await get_user_inventory(user_id)
    
    if item_id not in inventory["items"]:
        return False
    
    inventory["items"][item_id]["quantity"] -= quantity
    
    if inventory["items"][item_id]["quantity"] <= 0:
        if item_id in inventory["items"]:
            del inventory["items"][item_id]
    
    await set_user_inventory(user_id, inventory)
    return True

async def has_item(user_id, item_id):
    """Check if user has an item"""
    inventory = await get_user_inventory(user_id)
    return item_id in inventory["items"] and inventory["items"][item_id]["quantity"] > 0

async def get_active_luck_boost(user_id, game=None):
    """Get active luck boost percentage"""
    inventory = await get_user_inventory(user_id)
    
    if "luck_boost" in inventory["active_perks"]:
        perk = inventory["active_perks"]["luck_boost"]
        
        # Check if uses remaining
        if perk.get("uses_remaining", 0) > 0:
            # Check if game-specific
            shop_data = await load_shop_items()
            item = shop_data["items"].get(perk["item_id"])
            
            if item and item.get("game_specific"):
                if game and game.lower() == item["game_specific"].lower():
                    return perk["boost"]
                return 0.0
            
            return perk["boost"]
        else:
            # No uses left, remove it
            del inventory["active_perks"]["luck_boost"]
            await set_user_inventory(user_id, inventory)
    
    return 0.0

async def use_luck_boost(user_id):
    """Use one charge of active luck boost"""
    inventory = await get_user_inventory(user_id)
    
    if "luck_boost" in inventory["active_perks"]:
        inventory["active_perks"]["luck_boost"]["uses_remaining"] -= 1
        
        if inventory["active_perks"]["luck_boost"]["uses_remaining"] <= 0:
            del inventory["active_perks"]["luck_boost"]
        
        await set_user_inventory(user_id, inventory)
        return True
    
    return False

async def activate_luck_boost(user_id, item_id):
    """Activate luck boost item"""
    shop_data = await load_shop_items()
    item = shop_data["items"].get(item_id)
    
    if not item or item["category"] != "luck":
        return False
    
    inventory = await get_user_inventory(user_id)
    
    inventory["active_perks"]["luck_boost"] = {
        "boost": item["luck_boost"],
        "uses_remaining": item["uses"],
        "item_id": item_id
    }
    
    await set_user_inventory(user_id, inventory)
    return True

async def add_badge(user_id, badge_id):
    """Add badge to user's collection"""
    inventory = await get_user_inventory(user_id)
    
    if badge_id not in inventory["badges"]:
        inventory["badges"].append(badge_id)
        await set_user_inventory(user_id, inventory)
        return True
    
    return False

async def get_items_by_category(category=None):
    """Get shop items filtered by category"""
    shop_data = await load_shop_items()
    items = shop_data["items"]
    
    if category:
        return {k: v for k, v in items.items() if v.get("category") == category}
    
    return items
