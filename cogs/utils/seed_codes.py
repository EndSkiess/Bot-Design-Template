import random
import string
from cogs.utils.ravendb_manager import raven_db

CODES_DOC_ID = "easteregg/codes"
TOTAL_CODES = 100


def _generate_code():
    """Generate a random XXXX-XXXX-XXXX style code."""
    parts = [''.join(random.choices(string.ascii_uppercase + string.digits, k=4)) for _ in range(3)]
    return "-".join(parts)


async def seed_codes_if_needed():
    """
    Check if the codes document exists in RavenDB. If not (or if it has
    fewer than TOTAL_CODES entries), generate codes up to the target count.
    Each code is stored as:  { "code": "XXXX-XXXX-XXXX", "used": False }
    """
    data = await raven_db.load_document(CODES_DOC_ID)

    if data and isinstance(data, dict):
        existing = data.get("codes", [])
    else:
        existing = []

    # Build a set of already-known code strings so we don't duplicate
    existing_strings = {entry["code"] for entry in existing if isinstance(entry, dict)}

    needed = TOTAL_CODES - len(existing)
    if needed <= 0:
        print(f"[CodeSeeder] {len(existing)} codes already in DB — no seeding needed.")
        return

    new_entries = []
    while len(new_entries) < needed:
        code = _generate_code()
        if code not in existing_strings:
            existing_strings.add(code)
            new_entries.append({"code": code, "used": False})

    all_codes = existing + new_entries
    await raven_db.save_document(CODES_DOC_ID, {"codes": all_codes})
    print(f"[CodeSeeder] Seeded {len(new_entries)} new codes. Total: {len(all_codes)}")
