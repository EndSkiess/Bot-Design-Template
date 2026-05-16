# Pets GIF Folder

This folder contains GIF images for each pet type in the bot.

## File Naming Convention

Each GIF file should be named **exactly** as the pet type identifier (lowercase).

### Required GIF Files:

**Common Pets:**
- `dog.gif`
- `cat.gif`
- `rabbit.gif`

**Uncommon Pets:**
- `fox.gif`
- `panda.gif`
- `raccoon.gif`

**Rare Pets:**
- `lion.gif`
- `wolf.gif`
- `eagle.gif`

**Epic Pets:**
- `dragon.gif`
- `unicorn.gif`
- `shark.gif`

**Legendary Pets:**
- `ancient_dragon.gif`
- `trex.gif`

**Mythical Pets:**
- `phoenix.gif`

## Usage

1. Place your GIF files in this folder
2. Make sure the filename matches the pet type exactly (case-sensitive)
3. The bot will automatically display these GIFs as thumbnails when:
   - A pet spawns in a channel
   - A user catches a pet
   - A user views their pet with `/pet <pet_name>`

## Notes

- If a GIF file is missing, the embed will still display but without a thumbnail
- GIF files should be reasonably sized (recommended: under 5MB)
- Supported format: `.gif` only
