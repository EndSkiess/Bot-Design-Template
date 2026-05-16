"""
Fun commands - IQ test, waifu rater, anime matcher, smash or pass, spin wheel, animal facts, overrate
"""
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio


class FunCommands(commands.Cog):
    """Fun and entertaining commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Anime characters for what_anime command
        self.anime_characters = [
            {"name": "Naruto Uzumaki", "anime": "Naruto", "trait": "energetic and determined"},
            {"name": "Luffy", "anime": "One Piece", "trait": "adventurous and carefree"},
            {"name": "Light Yagami", "anime": "Death Note", "trait": "intelligent and strategic"},
            {"name": "Goku", "anime": "Dragon Ball", "trait": "strong and pure-hearted"},
            {"name": "Levi Ackerman", "anime": "Attack on Titan", "trait": "serious and skilled"},
            {"name": "Edward Elric", "anime": "Fullmetal Alchemist", "trait": "determined and clever"},
            {"name": "Spike Spiegel", "anime": "Cowboy Bebop", "trait": "cool and laid-back"},
            {"name": "Eren Yeager", "anime": "Attack on Titan", "trait": "passionate and driven"},
            {"name": "Saitama", "anime": "One Punch Man", "trait": "overpowered and chill"},
            {"name": "L", "anime": "Death Note", "trait": "genius and eccentric"},
            {"name": "Ichigo Kurosaki", "anime": "Bleach", "trait": "brave and protective"},
            {"name": "Vegeta", "anime": "Dragon Ball", "trait": "prideful and powerful"},
            {"name": "Kakashi Hatake", "anime": "Naruto", "trait": "mysterious and wise"},
            {"name": "Killua Zoldyck", "anime": "Hunter x Hunter", "trait": "quick and loyal"},
            {"name": "Tanjiro Kamado", "anime": "Demon Slayer", "trait": "kind and hardworking"},
            {"name": "Mikasa Ackerman", "anime": "Attack on Titan", "trait": "strong and devoted"},
            {"name": "Zero Two", "anime": "Darling in the Franxx", "trait": "bold and unique"},
            {"name": "Rem", "anime": "Re:Zero", "trait": "loyal and caring"},
            {"name": "Asuna", "anime": "Sword Art Online", "trait": "skilled and compassionate"},
            {"name": "Hinata Hyuga", "anime": "Naruto", "trait": "shy and determined"},
            {"name": "Nezuko Kamado", "anime": "Demon Slayer", "trait": "cute and protective"},
            {"name": "Megumin", "anime": "KonoSuba", "trait": "explosive and dramatic"},
            {"name": "Mai Sakurajima", "anime": "Bunny Girl Senpai", "trait": "mature and caring"},
            {"name": "Yor Forger", "anime": "Spy x Family", "trait": "deadly and sweet"},
        ]
        
        # Characters for smash or pass
        self.smash_pass_characters = [
            {"name": "Gojo Satoru", "anime": "Jujutsu Kaisen"},
            {"name": "Makima", "anime": "Chainsaw Man"},
            {"name": "Loid Forger", "anime": "Spy x Family"},
            {"name": "Yor Forger", "anime": "Spy x Family"},
            {"name": "Power", "anime": "Chainsaw Man"},
            {"name": "Marin Kitagawa", "anime": "My Dress-Up Darling"},
            {"name": "Anya Forger", "anime": "Spy x Family"},
            {"name": "Nezuko", "anime": "Demon Slayer"},
            {"name": "Zenitsu", "anime": "Demon Slayer"},
            {"name": "Inosuke", "anime": "Demon Slayer"},
            {"name": "Tanjiro", "anime": "Demon Slayer"},
            {"name": "Shinobu Kocho", "anime": "Demon Slayer"},
            {"name": "Mitsuri Kanroji", "anime": "Demon Slayer"},
            {"name": "Rengoku", "anime": "Demon Slayer"},
            {"name": "Aki Hayakawa", "anime": "Chainsaw Man"},
            {"name": "Denji", "anime": "Chainsaw Man"},
            {"name": "Sukuna", "anime": "Jujutsu Kaisen"},
            {"name": "Megumi Fushiguro", "anime": "Jujutsu Kaisen"},
            {"name": "Nobara Kugisaki", "anime": "Jujutsu Kaisen"},
            {"name": "Yuji Itadori", "anime": "Jujutsu Kaisen"},
        ]
        
        # Animal facts
        self.animal_facts = {
            "cat": [
                "Cats spend 70% of their lives sleeping, which means a 9-year-old cat has been awake for only three years!",
                "A group of cats is called a 'clowder' and a group of kittens is called a 'kindle'.",
                "Cats can rotate their ears 180 degrees and can hear sounds up to 64 kHz!",
                "A cat's purr vibrates at a frequency of 25-150 Hz, which can help heal bones and reduce pain.",
                "Cats have over 20 different vocalizations, including the meow which they only use to communicate with humans!",
            ],
            "dog": [
                "Dogs' noses are wet to help absorb scent chemicals - their sense of smell is 10,000 to 100,000 times better than humans!",
                "A dog's sense of time is evidenced by their ability to predict future events, like regular walk times.",
                "Dogs can understand up to 250 words and gestures, count up to five, and perform simple math!",
                "The Basenji is the only dog breed that doesn't bark, but they can yodel!",
                "Dogs' nose prints are as unique as human fingerprints and can be used to identify them.",
            ],
            "fox": [
                "Foxes use Earth's magnetic field to hunt - they can sense it and use it to pounce on prey hidden under snow!",
                "A group of foxes is called a 'skulk' or a 'leash'.",
                "Foxes have whiskers on their legs to help them navigate in the dark!",
                "Arctic foxes can survive temperatures as low as -70°C (-94°F)!",
                "Foxes make over 40 different sounds, including screams, barks, and gekkering (a stuttering chatter).",
            ],
            "frog": [
                "Some frogs can freeze solid during winter and thaw out alive in spring!",
                "The golden poison dart frog has enough toxin to kill 10 grown men!",
                "Frogs don't drink water - they absorb it through their skin!",
                "A group of frogs is called an 'army'.",
                "The wood frog can hold its pee for up to 8 months during hibernation!",
            ],
            "bird": [
                "Crows can recognize human faces and hold grudges for years!",
                "Hummingbirds are the only birds that can fly backwards!",
                "Owls can't move their eyes - they have to turn their entire head, which can rotate 270 degrees!",
                "Penguins propose to their mates with a pebble!",
                "The Arctic Tern has the longest migration of any animal, traveling about 44,000 miles per year!",
            ],
            "panda": [
                "Pandas spend 12-16 hours a day eating bamboo and can consume up to 84 pounds of it daily!",
                "Baby pandas are born pink, blind, and about the size of a stick of butter (100g)!",
                "Pandas have an extra 'thumb' (actually an enlarged wrist bone) to help them grip bamboo!",
                "Despite being bears, pandas do somersaults for fun!",
                "A panda's paw has six digits - five fingers and a thumb!",
            ],
        }
    
    
    
    @app_commands.command(name="whatanime", description="Find out what anime character you are!")
    @app_commands.describe(user="User to analyze (leave empty for yourself)")
    async def what_anime(self, interaction: discord.Interaction, user: discord.Member = None):
        """Guess what anime character the user resembles"""
        target = user or interaction.user
        character = random.choice(self.anime_characters)
        
        embed = discord.Embed(
            title="🎭 Anime Character Analysis",
            description=f"**{target.mention}** gives off **{character['name']}** vibes!",
            color=discord.Color.purple()
        )
        embed.add_field(name="Anime", value=character['anime'], inline=True)
        embed.add_field(name="Personality", value=f"You seem {character['trait']}!", inline=True)
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.set_footer(text="✨ This is randomly generated for fun!")
        
        await interaction.response.send_message(embed=embed)
    
    @app_commands.command(name="smashorpass", description="Smash or pass on a random anime character")
    async def smash_or_pass(self, interaction: discord.Interaction):
        """Present a random character for smash or pass"""
        character = random.choice(self.smash_pass_characters)
        
        embed = discord.Embed(
            title="💘 Smash or Pass?",
            description=f"**{character['name']}**\nfrom *{character['anime']}*",
            color=discord.Color.red()
        )
        embed.set_footer(text="React with 💚 for Smash or 💔 for Pass!")
        
        message = await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        
        # Add reactions
        await msg.add_reaction("💚")
        await msg.add_reaction("💔")
    
    @app_commands.command(name="spinwheel", description="Spin the wheel of fate!")
    @app_commands.describe(question="Optional question to ask the wheel")
    async def spinwheel(self, interaction: discord.Interaction, question: str = None):
        """Spin a decision wheel"""
        outcomes = [
            ("<a:flowers:1442767348091322389> Yes!", discord.Color.green()),
            ("<a:kitty:1442058935619158157> No!", discord.Color.red()),
            ("<a:55402slap:1449718642773069874> Maybe...", discord.Color.gold()),
            ("<a:6014cuddle:1449718630068785172> Try Again!", discord.Color.blue()),
            ("<a:8070bitchassslap:1449718633327755395> Ask Later!", discord.Color.purple()),
            ("<:769812sayswear:1449718667880169482> Why not thing for ur self", discord.Color.pink()),
        ]
        
        # Create spinning animation
        initial_desc = "🎯 ━━━━━━━━━━"
        if question:
            initial_desc = f"**Question:** {question}\n\n{initial_desc}"
            
        embed = discord.Embed(
            title="🎡 Spinning the Wheel...",
            description=initial_desc,
            color=discord.Color.blurple()
        )
        
        await interaction.response.send_message(embed=embed)
        msg = await interaction.original_response()
        
        # Simulate spinning
        for i in range(3):
            await asyncio.sleep(0.5)
            dots = "." * ((i % 3) + 1)
            desc_text = f"🎯 Spinning{dots}"
            if question:
                desc_text = f"**Question:** {question}\n\n{desc_text}"
            
            embed.description = desc_text
            await msg.edit(embed=embed)
        
        # Final result
        result, color = random.choice(outcomes)
        embed.title = "🎡 Wheel Result"
        
        if question:
            embed.description = f"**Question:** {question}\n\n# {result}"
        else:
            embed.description = f"# {result}"
            
        embed.color = color
        
        await msg.edit(embed=embed)
    
    @app_commands.command(name="animalfact", description="Get a random animal fact!")
    async def animalfact(self, interaction: discord.Interaction):
        """Share a random animal fact"""
        animal = random.choice(list(self.animal_facts.keys()))
        fact = random.choice(self.animal_facts[animal])
        
        # Animal emojis
        emojis = {
            "cat": "🐱",
            "dog": "🐶",
            "fox": "🦊",
            "frog": "🐸",
            "bird": "🐦",
            "panda": "🐼"
        }
        
        embed = discord.Embed(
            title=f"{emojis[animal]} {animal.title()} Fact",
            description=fact,
            color=discord.Color.green()
        )
        embed.set_footer(text="🌟 The more you know!")
        
        await interaction.response.send_message(embed=embed)
    



async def setup(bot):
    await bot.add_cog(FunCommands(bot))
