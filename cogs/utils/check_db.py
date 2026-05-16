import asyncio
import sys
import os

# Add parent dir to path so we can import ravendb_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ravendb_manager import raven_db

async def main():
    try:
        data = await raven_db.load_document("easteregg/active_codes")
        print(f"DATABASE CONTENTS for easteregg/active_codes: {data}")
        if data and isinstance(data, dict):
            print(f"Codes list: {data.get('codes', [])}")
        elif data:
            print(f"Codes list (obj): {getattr(data, 'codes', [])}")
            
    except Exception as e:
        print(f"Error checking DB: {e}")

if __name__ == "__main__":
    asyncio.run(main())
