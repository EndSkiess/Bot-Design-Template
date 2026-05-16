import os
import logging
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger('DatabaseManager')

class DatabaseManager:
    _instance = None
    _client = None
    _db = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DatabaseManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        mongo_uri = os.getenv('MONGO_URI')
        db_name = os.getenv('MONGO_DB_NAME', 'shizu_bot')
        
        if not mongo_uri or True: # Force disabled during RavenDB migration
            # logger.error("MONGO_URI not found in environment variables!")
            self.client = None
            self.db = None
        else:
            self.client = AsyncIOMotorClient(mongo_uri)
            self.db = self.client[db_name]
            logger.info(f"Connected to MongoDB: {db_name}")
            
        self._initialized = True

    async def get_collection(self, name):
        """Get a collection by name"""
        if self.db is None:
            return None
        return self.db[name]

    async def find_one(self, collection_name, query):
        """Find a single document in a collection"""
        col = await self.get_collection(collection_name)
        if col is None: return None
        return await col.find_one(query)

    async def find_all(self, collection_name, query=None):
        """Find all documents in a collection matching a query"""
        col = await self.get_collection(collection_name)
        if col is None: return []
        cursor = col.find(query or {})
        return await cursor.to_list(length=None)

    async def update_one(self, collection_name, query, update, upsert=True):
        """Update a single document in a collection"""
        col = await self.get_collection(collection_name)
        if col is None: return None
        return await col.update_one(query, update, upsert=upsert)

    async def delete_one(self, collection_name, query):
        """Delete a single document in a collection"""
        col = await self.get_collection(collection_name)
        if col is None: return None
        return await col.delete_one(query)

    async def insert_one(self, collection_name, document):
        """Insert a single document into a collection"""
        col = await self.get_collection(collection_name)
        if col is None: return None
        return await col.insert_one(document)

# Global instance
db = DatabaseManager()
