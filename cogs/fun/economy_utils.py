"""
Economy utility functions for managing user balances using MongoDB
"""
import logging
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('EconomyUtils')

COLLECTION = 'economy'
STARTING_BALANCE = 100
CURRENCY_NAME = "cursed coins"

async def get_balance(user_id: int) -> int:
    """Get user balance, create account if doesn't exist"""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        data = {
            'balance': STARTING_BALANCE,
            'last_daily': None,
            'total_earned': STARTING_BALANCE,
            'total_spent': 0
        }
        await raven_db.save_document(doc_id, data)
        return STARTING_BALANCE
    
    return data.get('balance', STARTING_BALANCE)

async def set_balance(user_id: int, amount: int):
    """Set user balance"""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if not data:
        data = {
            'balance': amount,
            'last_daily': None,
            'total_earned': amount,
            'total_spent': 0
        }
    else:
        data['balance'] = amount
    
    await raven_db.save_document(doc_id, data)

async def add_balance(user_id: int, amount: int):
    """Add to user balance"""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        new_balance = STARTING_BALANCE + amount
        data = {
            'balance': new_balance,
            'last_daily': None,
            'total_earned': new_balance,
            'total_spent': 0
        }
        await raven_db.save_document(doc_id, data)
        return new_balance
    
    data['balance'] = data.get('balance', 0) + amount
    data['total_earned'] = data.get('total_earned', 0) + amount
    await raven_db.save_document(doc_id, data)
    return data['balance']

async def remove_balance(user_id: int, amount: int) -> bool:
    """Remove from user balance, returns True if successful"""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        # Create user with starting balance
        if STARTING_BALANCE < amount:
            return False
        data = {
            'balance': STARTING_BALANCE - amount,
            'last_daily': None,
            'total_earned': STARTING_BALANCE,
            'total_spent': amount
        }
        await raven_db.save_document(doc_id, data)
        return True
    
    if data.get('balance', 0) < amount:
        return False
    
    data['balance'] = data['balance'] - amount
    data['total_spent'] = data.get('total_spent', 0) + amount
    await raven_db.save_document(doc_id, data)
    return True

async def force_remove_balance(user_id: int, amount: int) -> int:
    """Remove from user balance, allowing it to go negative (e.g. fines). Returns new balance."""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        new_balance = STARTING_BALANCE - amount
        data = {
            'balance': new_balance,
            'last_daily': None,
            'total_earned': STARTING_BALANCE,
            'total_spent': amount
        }
    else:
        data['balance'] = data.get('balance', 0) - amount
        data['total_spent'] = data.get('total_spent', 0) + amount
    
    await raven_db.save_document(doc_id, data)
    return data['balance']

async def has_balance(user_id: int, amount: int) -> bool:
    """Check if user has enough balance"""
    balance = await get_balance(user_id)
    return balance >= amount

async def get_last_daily(user_id: int) -> str:
    """Get last daily claim timestamp"""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    if not data:
        return None
    return data.get('last_daily')

async def set_last_daily(user_id: int, timestamp: str):
    """Set last daily claim timestamp"""
    doc_id = f"{COLLECTION}/{user_id}"
    await raven_db.patch_document(doc_id, {'last_daily': timestamp})

async def get_leaderboard(limit: int = 10):
    """Get top users by balance"""
    all_docs = await raven_db.get_all_in_collection(COLLECTION, limit=100)
    # Sort by balance descending
    sorted_docs = sorted(all_docs, key=lambda x: x.get('balance', 0), reverse=True)
    # Convert to expected format [(id, data), ...]
    # RavenDB ID usually looks like "economy/123456"
    return [(doc['@metadata']['@id'].split('/')[-1], doc) for doc in sorted_docs[:limit]]

async def get_user_stats(user_id: int):
    """Get user statistics"""
    doc_id = f"{COLLECTION}/{user_id}"
    data = await raven_db.load_document(doc_id)
    
    if not data:
        return {
            'balance': STARTING_BALANCE,
            'total_earned': STARTING_BALANCE,
            'total_spent': 0,
            'net_profit': STARTING_BALANCE
        }
    
    total_earned = data.get('total_earned', 0)
    total_spent = data.get('total_spent', 0)
    return {
        'balance': data.get('balance', 0),
        'total_earned': total_earned,
        'total_spent': total_spent,
        'net_profit': total_earned - total_spent
    }

# Compatibility functions (optional, but keep for safety if used elsewhere)
def load_economy():
    """NOT RECOMMENDED - use async functions. Returning empty dict to avoid crashes."""
    return {}

def save_economy(data):
    """NOT RECOMMENDED - use async functions."""
    pass
