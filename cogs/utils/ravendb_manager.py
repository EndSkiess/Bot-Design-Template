import os
import logging
import asyncio
from ravendb import DocumentStore
from dotenv import load_dotenv
from concurrent.futures import ThreadPoolExecutor

load_dotenv()

logger = logging.getLogger('RavenDBManager')

class RavenDBManager:
    _instance = None
    _lock = asyncio.Lock()

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(RavenDBManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        urls = os.getenv('RAVEN_URL', 'http://localhost:8080').split(',')
        database = os.getenv('RAVEN_DATABASE', 'shizu_bot')
        cert_path = os.getenv('RAVEN_CERT_PATH')

        try:
            self.store = DocumentStore(urls=urls, database=database)
            if cert_path:
                # Ensure path is absolute relative to project root
                if not os.path.isabs(cert_path):
                    abs_cert_path = os.path.abspath(os.path.join(os.getcwd(), cert_path))
                else:
                    abs_cert_path = cert_path
                    
                if os.path.exists(abs_cert_path):
                    # RavenDB 7.x uses certificate_pem_path, older versions used certificate
                    if hasattr(self.store, 'certificate_pem_path'):
                        self.store.certificate_pem_path = abs_cert_path
                    else:
                        self.store.certificate = abs_cert_path
                    logger.info(f"Using certificate: {abs_cert_path}")
                else:
                    logger.warning(f"Certificate not found at: {abs_cert_path}")
            
            self.store.conventions.disable_topology_updates = True
            self.store.initialize()
            logger.info(f"Connected to RavenDB: {database} at {urls}")
        except Exception as e:
            logger.error(f"Failed to connect to RavenDB: {e}")
            self.store = None
            
        self._executor = ThreadPoolExecutor(max_workers=10)
        self._initialized = True

    def open_session(self):
        if self.store:
            return self.store.open_session()
        return None

    async def run_async(self, func, *args):
        """Run a synchronous RavenDB function in a thread pool"""
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(self._executor, func, *args)

    async def load_document(self, doc_id):
        if not self.store: return None
        def _load():
            with self.open_session() as session:
                return session.load(doc_id)
        return await self.run_async(_load)

    async def save_document(self, doc_id, data):
        if not self.store: return
        def _save():
            with self.open_session() as session:
                session.store(data, doc_id)
                session.save_changes()
        return await self.run_async(_save)

    async def patch_document(self, doc_id, patch_data):
        """Simple patch utility for dictionary updates"""
        if not self.store: return
        def _patch():
            with self.open_session() as session:
                doc = session.load(doc_id)
                if doc:
                    if isinstance(doc, dict):
                        doc.update(patch_data)
                    else:
                        for key, value in patch_data.items():
                            setattr(doc, key, value)
                    session.save_changes()
        return await self.run_async(_patch)

    async def increment_field(self, doc_id, field_name, amount):
        """Atomically increment a numeric field"""
        if not self.store: return None
        def _inc():
            with self.open_session() as session:
                doc = session.load(doc_id)
                if not doc:
                    return None
                
                # Handle both dicts and objects
                if isinstance(doc, dict):
                    doc[field_name] = doc.get(field_name, 0) + amount
                else:
                    val = getattr(doc, field_name, 0)
                    setattr(doc, field_name, val + amount)
                
                session.save_changes()
                return doc
        return await self.run_async(_inc)

    async def get_all_in_collection(self, collection_prefix, limit=100):
        """Load all documents starting with a prefix (collection-like)"""
        if not self.store: return []
        def _load_all():
            with self.open_session() as session:
                # Correct positional order: id_prefix, object_type, matches, start, page_size
                results = list(session.advanced.load_starting_with(f"{collection_prefix}/", None, None, 0, limit))
                return results
        return await self.run_async(_load_all)

    async def delete_document(self, doc_id):
        """Delete a document by ID"""
        if not self.store: return
        def _delete():
            with self.open_session() as session:
                session.delete(doc_id)
                session.save_changes()
        return await self.run_async(_delete)

# Global instance
raven_db = RavenDBManager()
