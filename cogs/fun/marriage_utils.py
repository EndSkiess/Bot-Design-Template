"""
Marriage and Family system utilities - Async data management for marriages and family trees using MongoDB
"""
import logging
from datetime import datetime, UTC
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Marriage')

MARRIAGES_PREFIX = "marriages"
FAMILY_TREE_PREFIX = "family_tree"

async def is_married(user_id):
    """Check if user is married"""
    doc_id = f"{MARRIAGES_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    return data is not None

async def get_partner(user_id):
    """Get user's partner ID"""
    doc_id = f"{MARRIAGES_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if data:
        return data.get("partner_id")
    return None

async def marry_users(user1_id, user2_id):
    """Marry two users"""
    married_at = datetime.now(UTC).isoformat()
    
    await raven_db.save_document(f"{MARRIAGES_PREFIX}/{user1_id}", {
        "partner_id": str(user2_id),
        "married_at": married_at,
        "joint_balance": False
    })
    
    await raven_db.save_document(f"{MARRIAGES_PREFIX}/{user2_id}", {
        "partner_id": str(user1_id),
        "married_at": married_at,
        "joint_balance": False
    })

async def divorce_users(user_id):
    """Divorce user and their partner"""
    doc_id = f"{MARRIAGES_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if data:
        partner_id = data["partner_id"]
        
        # Remove both marriage records
        await raven_db.delete_document(doc_id)
        await raven_db.delete_document(f"{MARRIAGES_PREFIX}/{partner_id}")
        
        return partner_id
    
    return None

async def get_marriage_data(user_id):
    """Get marriage data for user"""
    return await raven_db.load_document(f"{MARRIAGES_PREFIX}/{user_id}")

async def toggle_joint_balance(user_id):
    """Toggle joint balance for user's marriage"""
    doc_id = f"{MARRIAGES_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if data:
        partner_id = data["partner_id"]
        current = data.get("joint_balance", False)
        new_value = not current
        
        # Update both users
        await raven_db.patch_document(doc_id, {"joint_balance": new_value})
        await raven_db.patch_document(f"{MARRIAGES_PREFIX}/{partner_id}", {"joint_balance": new_value})
        
        return new_value
    
    return None

async def get_couple_leaderboard(limit=10):
    """Get top couples by marriage duration"""
    all_docs = await raven_db.get_all_in_collection(MARRIAGES_PREFIX, limit=500)
    
    results = []
    seen_couples = set()
    
    for doc in all_docs:
        u1 = doc['@metadata']['@id'].split('/')[-1]
        u2 = doc.get('partner_id')
        
        # Sort IDs to avoid duplicates (u1, u2) vs (u2, u1)
        couple_key = tuple(sorted([u1, u2]))
        if couple_key in seen_couples:
            continue
        seen_couples.add(couple_key)
        
        married_at_str = doc.get("married_at")
        if not married_at_str: continue
        
        married_at = datetime.fromisoformat(married_at_str)
        if married_at.tzinfo is None: married_at = married_at.replace(tzinfo=UTC)
        
        duration = (datetime.now(UTC) - married_at).total_seconds()
        results.append({
            "user1_id": u1,
            "user2_id": u2,
            "married_at": married_at_str,
            "duration": duration,
            "joint_balance": doc.get("joint_balance", False)
        })
    
    # Sort by duration descending (earliest marriage first)
    results.sort(key=lambda x: x['duration'], reverse=True)
    return results[:limit]

async def get_family_data(user_id):
    """Get family tree data for user from RavenDB"""
    doc_id = f"{FAMILY_TREE_PREFIX}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        data = {
            "parent_ids": [],
            "children_ids": []
        }
        await raven_db.save_document(doc_id, data)
    
    return data

async def add_child(parent_id, child_id):
    """Add child to parent's family"""
    # Parent's data
    parent_data = await get_family_data(parent_id)
    child_id_str = str(child_id)
    if child_id_str not in parent_data["children_ids"]:
        parent_data["children_ids"].append(child_id_str)
        await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{parent_id}", parent_data)
    
    # Child's data
    child_data = await get_family_data(child_id)
    parent_id_str = str(parent_id)
    if parent_id_str not in child_data["parent_ids"]:
        child_data["parent_ids"].append(parent_id_str)
        child_data["adopted_at"] = datetime.now(UTC).isoformat()
        await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{child_id}", child_data)
    
    # If parent is married, add spouse as parent too
    partner_id = await get_partner(parent_id)
    if partner_id:
        partner_data = await get_family_data(partner_id)
        if child_id_str not in partner_data["children_ids"]:
            partner_data["children_ids"].append(child_id_str)
            await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{partner_id}", partner_data)
        
        if str(partner_id) not in child_data["parent_ids"]:
            child_data["parent_ids"].append(str(partner_id))
            await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{child_id}", child_data)

async def can_adopt(parent_id, child_id):
    """Check if parent can adopt child, including circularity checks"""
    child_data = await raven_db.load_document(f"{FAMILY_TREE_PREFIX}/{child_id}")
    if child_data:
        if len(child_data.get("parent_ids", [])) >= 2:
            return False
    
    # Circularity check: parent cannot adopt their own ancestor
    if await is_related(child_id, parent_id):
        return False
        
    return True

async def get_full_family(user_id):
    """Get complete family tree for user"""
    family = {
        "user_id": str(user_id),
        "parents": [],
        "children": [],
        "grandparents": [],
        "spouse": None
    }
    
    # Get user data
    user_data = await get_family_data(user_id)
    family["parents"] = user_data.get("parent_ids", [])
    family["children"] = user_data.get("children_ids", [])
    
    # Get spouse
    family["spouse"] = await get_partner(user_id)
    
    # Get grandparents
    for parent_id in family["parents"]:
        parent_data = await raven_db.load_document(f"{FAMILY_TREE_PREFIX}/{parent_id}")
        if parent_data:
            family["grandparents"].extend(parent_data.get("parent_ids", []))
    
    return family

async def is_related(user1_id, user2_id):
    """Check if two users are related in any way in the family tree"""
    u1_str = str(user1_id)
    u2_str = str(user2_id)
    
    if u1_str == u2_str:
        return True
        
    # BFS to find any connection
    queue = [u1_str]
    visited = {u1_str}
    
    while queue:
        current = queue.pop(0)
        if current == u2_str:
            return True
            
        data = await raven_db.load_document(f"{FAMILY_TREE_PREFIX}/{current}")
        if not data:
            data = {"parent_ids": [], "children_ids": []}
            
        # Check parents, children, and their connections
        connections = data.get("parent_ids", []) + data.get("children_ids", [])
        
        # Also check spouse (marriage relation)
        spouse = await get_partner(current)
        if spouse:
            connections.append(str(spouse))
            
        for conn in connections:
            if conn not in visited:
                visited.add(conn)
                queue.append(conn)
                
    return False

async def remove_child(parent_id, child_id):
    """Remove a child from parent's family (disown)"""
    parent_data = await get_family_data(parent_id)
    child_id_str = str(child_id)
    if child_id_str in parent_data.get("children_ids", []):
        parent_data["children_ids"].remove(child_id_str)
        await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{parent_id}", parent_data)
    
    child_data = await get_family_data(child_id)
    parent_id_str = str(parent_id)
    if parent_id_str in child_data.get("parent_ids", []):
        child_data["parent_ids"].remove(parent_id_str)
        await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{child_id}", child_data)
    
    # Also remove from spouse if married
    partner_id = await get_partner(parent_id)
    if partner_id:
        partner_data = await get_family_data(partner_id)
        if child_id_str in partner_data.get("children_ids", []):
            partner_data["children_ids"].remove(child_id_str)
            await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{partner_id}", partner_data)
        
        if str(partner_id) in child_data.get("parent_ids", []):
            child_data["parent_ids"].remove(str(partner_id))
            await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{child_id}", child_data)
    
    return True

async def remove_from_family(user_id):
    """Remove user from entire family tree (runaway)"""
    user_id_str = str(user_id)
    user_data = await get_family_data(user_id)
    
    if not user_data:
        return False
    
    # Remove user from all parents' children lists
    for parent_id in user_data.get("parent_ids", []):
        parent_data = await get_family_data(parent_id)
        if user_id_str in parent_data.get("children_ids", []):
            parent_data["children_ids"].remove(user_id_str)
            await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{parent_id}", parent_data)
    
    # Remove user from all children's parent lists
    for child_id in user_data.get("children_ids", []):
        child_data = await get_family_data(child_id)
        if user_id_str in child_data.get("parent_ids", []):
            child_data["parent_ids"].remove(user_id_str)
            await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{child_id}", child_data)
    
    # Clear user's family data
    await raven_db.save_document(f"{FAMILY_TREE_PREFIX}/{user_id_str}", {"parent_ids": [], "children_ids": []})
    
    return True

# Compatibility functions (optional, but keep for safety if used elsewhere)
def load_marriages(): return {}
def save_marriages(data): pass
def load_family_tree(): return {}
def save_family_tree(data): pass
