"""
Anime interaction commands - kiss, hug, slap, punch, kill
Uses custom GIF URL lists
"""
import discord
from discord.ext import commands
from discord import app_commands
import random
import logging

logger = logging.getLogger('Lilith.Interactions')

class Interactions(commands.Cog):
    """Anime-themed interaction commands"""
    
    def __init__(self, bot):
        self.bot = bot
        
        # Emoji names that match the names you uploaded to your bot application
        self.emoji_names = {
            "kiss": "catlove",
            "lick": "catlick", 
            "hug": "diavoloheart",
            "slap": "slap",
            "punch": "bitchassslap",
            "kill": "garrisonsniper",
            "pat": "eeveeheadpats",
            "poke": "hellokitty",
            "bite": "ellenbite",
            "cuddle": "cuddle",
            "wave": "wonyoungwave",
            "dance": "feelingit2",
            "cry": "cryingghost",
            "laugh": "sayswear",
        }
        
        # Define custom GIF URL lists for each interaction
        # Add your own GIF URLs here!
        self.gif_urls = {
            "kiss": [
                # Add your kiss GIF URLs here
                "https://c.tenor.com/kmxEaVuW8AoAAAAC/tenor.gif",
                "https://c.tenor.com/SJhcVWsxgEkAAAAC/tenor.gif",
                "https://c.tenor.com/xDCr6DNYcZEAAAAC/tenor.gif",
                "https://c.tenor.com/_8oadF3hZwIAAAAC/tenor.gif",
                "https://c.tenor.com/lJPu85pBQLEAAAAC/tenor.gif",
                "https://c.tenor.com/sbMBW4a-VN4AAAAC/tenor.gif",
                "https://c.tenor.com/g8AeFZoe7dsAAAAC/tenor.gif",
                "https://c.tenor.com/g8AeFZoe7dsAAAAC/tenor.gif",
                "https://c.tenor.com/WeRg5GfJ54IAAAAC/tenor.gif",
                "https://c.tenor.com/YhGc7aQAI4oAAAAC/tenor.gif",
                "https://c.tenor.com/ZDqsYLDQzIUAAAAd/tenor.gif",
                "https://c.tenor.com/YHxJ9NvLYKsAAAAC/tenor.gif",
                "https://c.tenor.com/BZyWzw2d5tAAAAAC/tenor.gif"
            ],
            "lick": [
                # Add your lick GIF URLs here
                "https://c.tenor.com/HaFDVtk05hIAAAAC/tenor.gif",
                "https://c.tenor.com/gtyeOa6SBKAAAAAC/tenor.gif",
                "https://c.tenor.com/d0CunrDQsJ4AAAAC/tenor.gif",
                "https://c.tenor.com/iPI6QifO4UYAAAAC/tenor.gif",
                "https://c.tenor.com/S5I9g4dPRn4AAAAC/tenor.gif",
                "https://c.tenor.com/IjyMLNNbNA8AAAAC/tenor.gif",
                "https://c.tenor.com/Ja6awViaQkUAAAAC/tenor.gif",
                "https://c.tenor.com/5mLXTXTj6nEAAAAC/tenor.gif",
            ],
            "hug": [
                # Add your hug GIF URLs here
                "https://c.tenor.com/HBTbcCNvLRIAAAAC/tenor.gif",
                "https://c.tenor.com/J7eGDvGeP9IAAAAC/tenor.gif",
                "https://c.tenor.com/IpGw3LOZi2wAAAAC/tenor.gif",
                "https://c.tenor.com/2HxamDEy7XAAAAAC/tenor.gif",
                "https://c.tenor.com/7f9CqFtd4SsAAAAC/tenor.gif",
                "https://c.tenor.com/wWFm70VeC7YAAAAC/tenor.gif",
                "https://c.tenor.com/7oCaSR-q1kkAAAAC/tenor.gif",
                "https://c.tenor.com/YF-rFMgHgDEAAAAd/tenor.gif",
                "https://c.tenor.com/P-8xYwXoGX0AAAAC/tenor.gif",
                "https://c.tenor.com/PlenvFTbCcAAAAAC/tenor.gif",
                "https://c.tenor.com/nwxXREHNog0AAAAd/tenor.gif",
                "https://c.tenor.com/JzxgF3aebL0AAAAC/tenor.gif",
                "https://c.tenor.com/BFmsQg9J1ZMAAAAC/tenor.gif",
                "https://c.tenor.com/c2SMIhi33DMAAAAC/tenor.gif",
                "https://c.tenor.com/sJATVEhZ_VMAAAAC/tenor.gif",
                "https://c.tenor.com/6gA7NA3LpwMAAAAC/tenor.gif",
            ],
            "slap": [
                # Add your slap GIF URLs here
                "https://c.tenor.com/Ws6Dm1ZW_vMAAAAC/tenor.gif",
                "https://c.tenor.com/Sv8LQZAoQmgAAAAC/tenor.gif",
                "https://c.tenor.com/XiYuU9h44-AAAAAC/tenor.gif",
                "https://c.tenor.com/eU5H6GbVjrcAAAAC/tenor.gif",
                "https://c.tenor.com/7xFcP1KWjY0AAAAC/tenor.gif",
                "https://c.tenor.com/mTmYJx-mIa0AAAAC/tenor.gif",
                "https://c.tenor.com/cpWuWnOU64MAAAAC/tenor.gif",
                "https://c.tenor.com/8bSm0lI4_FUAAAAC/tenor.gif",
                "https://c.tenor.com/E3OW-MYYum0AAAAC/tenor.gif",
                "https://c.tenor.com/Xwe3ku5WF-YAAAAC/tenor.gif",
                "https://c.tenor.com/cfobWWgjG8wAAAAC/tenor.gif",
                "https://c.tenor.com/nVvUhW4FBxcAAAAd/tenor.gif",
                "https://c.tenor.com/ZozZrvtEdAkAAAAC/tenor.gif",
                "https://c.tenor.com/NPKC-nRM1lcAAAAC/tenor.gif",
                "https://c.tenor.com/Up9LqtY-AuIAAAAC/tenor.gif",
                "https://c.tenor.com/yJmrNruFNtEAAAAC/tenor.gif"
            ],
            "punch": [
                # Add your punch GIF URLs here
                "https://c.tenor.com/BoYBoopIkBcAAAAC/tenor.gif",
                "https://c.tenor.com/qDDsivB4UEkAAAAC/tenor.gif",
                "https://c.tenor.com/YGKPpkNN6g0AAAAC/tenor.gif",
                "https://media.tenor.com/yA_KtmPI1EMAAAAM/hxh-hunter-x-hunter.gif",
                "https://c.tenor.com/p_mMicg1pgUAAAAC/tenor.gif",
                "https://c.tenor.com/pNmajM4wmtkAAAAC/tenor.gif",
                "https://c.tenor.com/0ssFlowQEUQAAAAC/tenor.gif",
                "https://c.tenor.com/Kbit6lroRFUAAAAC/tenor.gif",
                "https://c.tenor.com/gmvdv-e1EhcAAAAC/tenor.gif",
                "https://c.tenor.com/ObgxhbfdVCAAAAAd/tenor.gif",
                "https://c.tenor.com/UH8Jnl1W3CYAAAAC/tenor.gif",
                "https://c.tenor.com/vv1mgp7IQn8AAAAC/tenor.gif",
                "https://c.tenor.com/jVeoj7B-OxEAAAAC/tenor.gif",
                "https://c.tenor.com/SwMgGqBirvcAAAAC/tenor.gif",
                "https://c.tenor.com/R5krSZcKo_kAAAAC/tenor.gif",
                "https://media.tenor.com/wYyB8BBA8fIAAAAM/some-guy-getting-punch-anime-punching-some-guy-anime.gif",
                "https://c.tenor.com/hu9e3k1zr0IAAAAC/tenor.gif",
            ],
            "kill": [
                # Add your kill/wasted GIF URLs here
                "https://c.tenor.com/hDFU7nFDFhcAAAAd/tenor.gif",
                "https://c.tenor.com/tmt1kX9T5_MAAAAd/tenor.gif",
                "https://c.tenor.com/Re9dglY0sCwAAAAC/tenor.gif",
                "https://c.tenor.com/RU_RjYoHDusAAAAC/tenor.gif",
                "https://c.tenor.com/I_msiNVliZ4AAAAC/tenor.gif",
                "https://c.tenor.com/NbBCakbfZnkAAAAC/tenor.gif",
                "https://c.tenor.com/b7UhYIWfmXEAAAAC/tenor.gif",
                "https://c.tenor.com/Hy9M1bvSEAEAAAAC/tenor.gif",
                "https://c.tenor.com/NMncXUo_xZ8AAAAC/tenor.gif",
                "https://c.tenor.com/whNqgdRpxCAAAAAd/tenor.gif",
                "https://c.tenor.com/1Ygfg3W4V2cAAAAd/tenor.gif",
            ],
            "pat": [
                # Add your pat GIF URLs here
                "https://c.tenor.com/PkWttKcH1xMAAAAC/tenor.gif",
                "https://c.tenor.com/kIh2QZ7MhBMAAAAC/tenor.gif",
                "https://c.tenor.com/wLqFGYigJuIAAAAC/tenor.gif",
                "https://c.tenor.com/1vt_6_y0nQsAAAAC/tenor.gif",
                "https://c.tenor.com/8FOQORmaLNoAAAAC/tenor.gif",
                "https://c.tenor.com/CIF_Pa3yepwAAAAC/tenor.gif",
                "https://c.tenor.com/MDc4TSck5PQAAAAC/tenor.gif",
                "https://c.tenor.com/AhXwHCLEBkkAAAAC/tenor.gif",
                "https://c.tenor.com/N41zKEDABuUAAAAC/tenor.gif",
                "https://c.tenor.com/Zm71HaIh7wwAAAAC/tenor.gif",
                "https://c.tenor.com/f1Ppi3xBHSwAAAAC/tenor.gif",
                "https://c.tenor.com/fro6pl7src0AAAAC/tenor.gif",
                "https://c.tenor.com/7xrOS-GaGAIAAAAC/tenor.gif",
                "https://c.tenor.com/oUS1jdJBkIwAAAAC/tenor.gif",
                "https://c.tenor.com/E7Ll04_an30AAAAC/tenor.gif",
                "https://c.tenor.com/mecnd_qE8p8AAAAd/tenor.gif",
            ],
            "poke": [
                # Add your poke GIF URLs here
                "https://c.tenor.com/iu_Lnd86GxAAAAAC/tenor.gif",
                "https://tenor.com/view/vn-visual-novel-visual-novel-anime-gif-98841764096487184730",
                "https://c.tenor.com/B-E9cSUwhw8AAAAC/tenor.gif",
                "https://c.tenor.com/7iV_gBGrRAUAAAAC/tenor.gif",
                "https://c.tenor.com/gMqsQ1wwbhgAAAAC/tenor.gif",
                "https://c.tenor.com/3dOqO4vVlr8AAAAC/tenor.gif",
                "https://c.tenor.com/0wPms8tS0eoAAAAC/tenor.gif",
                "https://c.tenor.com/y4R6rexNEJIAAAAC/tenor.gif",
                "https://c.tenor.com/APqauOtznp4AAAAC/tenor.gif",
                "https://c.tenor.com/1YMrMsCtxLQAAAAC/tenor.gif",
                "https://c.tenor.com/D5VvK6Ud-nAAAAAC/tenor.gif",
                "https://c.tenor.com/vVtDnV6IEGYAAAAC/tenor.gif",
                "https://c.tenor.com/HJa3EjH0iNMAAAAC/tenor.gif",
                "https://media.tenor.com/eB2I8N_7JR8AAAAM/haganeska-demon-slayer.gif",
            ],
            "bite": [
                # Add your bite GIF URLs here
                "https://c.tenor.com/5mVQ3ffWUTgAAAAC/tenor.gif",
                "https://c.tenor.com/IKDf1NMrzsIAAAAC/tenor.gif",
                "https://c.tenor.com/DoS4-kBg8VMAAAAC/tenor.gif",
                "https://c.tenor.com/ifbb8c3S4u8AAAAC/tenor.gif",
                "https://c.tenor.com/_AkeqheWU-4AAAAC/tenor.gif",
                # Invalid search URL removed - add a proper GIF URL here
                "https://c.tenor.com/0neaBmDilHsAAAAC/tenor.gif",
                "https://c.tenor.com/ECCpi63jZlUAAAAC/tenor.gif",
                "https://c.tenor.com/n__KGrZPlQEAAAAC/tenor.gif",
                "https://c.tenor.com/1LtA9dSoAIQAAAAC/tenor.gif",
                "https://c.tenor.com/mXc2f5NeOpgAAAAC/tenor.gif",
                # Invalid search URL removed - add a proper GIF URL here
                "https://c.tenor.com/diRQGFt9T1EAAAAC/tenor.gif",
                "https://c.tenor.com/MGuHaYdPUJ4AAAAd/tenor.gif",
                "https://c.tenor.com/1AxqGIb7VP8AAAAC/tenor.gif",
            ],
            "cuddle": [
                # Add your cuddle GIF URLs here
                "https://c.tenor.com/P54lVoy1FxkAAAAd/tenor.gif",
                "https://c.tenor.com/BcWUnXsPU_oAAAAC/tenor.gif",
                "https://c.tenor.com/SAL_XAuyuJAAAAAC/tenor.gif",
                "https://c.tenor.com/i2Mwr7Xk__YAAAAC/tenor.gif",
                "https://c.tenor.com/RR4YJdzCJRMAAAAC/tenor.gif",
                "https://c.tenor.com/bLttPccI_I4AAAAC/tenor.gif",
                "https://c.tenor.com/wnc03mLfwy0AAAAC/tenor.gif",
                "https://c.tenor.com/bZzrhkxcs6cAAAAC/tenor.gif",
                "https://c.tenor.com/CBJKhz9QvnMAAAAC/tenor.gif",
                "https://c.tenor.com/sGrFJCNL1_8AAAAC/tenor.gif",
                "https://c.tenor.com/H7i6GIP-YBwAAAAC/tenor.gif",
            ],
            "wave": [
                # Add your wave GIF URLs here
                "https://c.tenor.com/x8Vc_4yrQuoAAAAC/tenor.gif",
                "https://c.tenor.com/xsICn9T81LcAAAAC/tenor.gif",
                "https://c.tenor.com/1MfQk9vFF7MAAAAC/tenor.gif",
                "https://c.tenor.com/SaZJysRklQcAAAAC/tenor.gif",
                "https://c.tenor.com/EcAlsge9saMAAAAC/tenor.gif",
                "https://c.tenor.com/dxwWkT10bmoAAAAd/tenor.gif",
                "https://c.tenor.com/nQOSTbcTKZcAAAAC/tenor.gif",
                "https://c.tenor.com/FMpLzF4UJhwAAAAC/tenor.gif",
                "https://c.tenor.com/TFChym-vC7oAAAAC/tenor.gif",
                "https://c.tenor.com/_9W9bVa4AHgAAAAC/tenor.gif",
                "https://c.tenor.com/H4xLf6epW-wAAAAC/tenor.gif",
                "https://c.tenor.com/tzbVcnK8iGsAAAAC/tenor.gif",
                "https://c.tenor.com/9aXyxmnYW7oAAAAC/tenor.gif",
                "https://c.tenor.com/wBumfyondqsAAAAC/tenor.gif",
                "https://c.tenor.com/f4X5_86ebU8AAAAC/tenor.gif",
                "https://c.tenor.com/_c57eQ30AVoAAAAC/tenor.gif",
            ],
            "dance": [
                # Add your dance GIF URLs here
                "https://c.tenor.com/TxflfpxQNgcAAAAC/tenor.gif",
                "https://c.tenor.com/M7-Ftr7tsz8AAAAC/tenor.gif",
                "https://c.tenor.com/GOYRQva4UeoAAAAC/tenor.gif",
                "https://c.tenor.com/3wX8AyxMBfIAAAAC/tenor.gif",
                "https://c.tenor.com/H6VeJuNhLJkAAAAC/tenor.gif",
                "https://c.tenor.com/d-lz7Nu6X2oAAAAC/tenor.gif",
                "https://c.tenor.com/Ynm40n9fwNMAAAAd/tenor.gif",
                "https://c.tenor.com/LNVNahJyrI0AAAAC/tenor.gif",
                "https://c.tenor.com/m21RwoBHceEAAAAd/tenor.gif",
                "https://c.tenor.com/db0yF9G7qn4AAAAC/tenor.gif",
                "https://c.tenor.com/9hSEFOrYc8cAAAAC/tenor.gif",
            ],
            "cry": [
                # Add your cry GIF URLs here
                "https://c.tenor.com/pWQsUP6AtNgAAAAC/tenor.gif",
                "https://c.tenor.com/35S_M89zT3sAAAAC/tenor.gif",
                "https://c.tenor.com/DifoWwjRvOcAAAAC/tenor.gif",
                "https://c.tenor.com/fmB1LPfUc5AAAAAC/tenor.gif",
                "https://c.tenor.com/ZURDvrz5D38AAAAC/tenor.gif",
                "https://c.tenor.com/0qj0aqZ0nucAAAAC/tenor.gif",
                "https://c.tenor.com/VO2in_SxlvAAAAAC/tenor.gif",
                "https://c.tenor.com/DiFQ_Rl3dCQAAAAd/tenor.gif",
                "https://c.tenor.com/PhUSf6rVeyAAAAAd/tenor.gif",
                "https://c.tenor.com/gK-GwW8KEmEAAAAC/tenor.gif",
                "https://c.tenor.com/IV2kNBcN3r0AAAAC/tenor.gif",
                "https://c.tenor.com/7E7ZvsLgcfAAAAAC/tenor.gif",
                "https://c.tenor.com/IHVd7sXB66YAAAAC/tenor.gif",
                "https://c.tenor.com/3mscVoYlvOcAAAAd/tenor.gif",
                "https://c.tenor.com/A0g9Rrx4aNsAAAAC/tenor.gif",
            ],
            "laugh": [
                # Add your laugh GIF URLs here
                "https://c.tenor.com/Hqi4J6__E9kAAAAC/tenor.gif",
                "https://c.tenor.com/RqKEPJqkI0wAAAAC/tenor.gif",
                "https://c.tenor.com/CXsIEWMlv6kAAAAC/tenor.gif",
                "https://c.tenor.com/CCTYyxh2OXoAAAAC/tenor.gif",
                "https://c.tenor.com/BP9vMzwRSZwAAAAC/tenor.gif",
                "https://c.tenor.com/jz9aJI4fys4AAAAC/tenor.gif",
                # Invalid search URL removed - add a proper GIF URL here
                "https://c.tenor.com/dKhJiGhPeeEAAAAC/tenor.gif",
                "https://c.tenor.com/nqTDeAS9sL8AAAAC/tenor.gif",
                "https://c.tenor.com/RQayAFoMNJEAAAAC/tenor.gif",
                "https://c.tenor.com/V3KSIt0QNRkAAAAC/tenor.gif",
                "https://c.tenor.com/CAJWKDzTbFEAAAAC/tenor.gif",
                "https://c.tenor.com/ETvEeDnbX7AAAAAC/tenor.gif",
                "https://c.tenor.com/Zk5FmAidtwQAAAAC/tenor.gif",
                "https://c.tenor.com/fhSH7hGtytUAAAAd/tenor.gif",
            ],
        }
    
    def get_random_gif(self, interaction_type):
        """Get a random GIF URL from the predefined lists"""
        gif_list = self.gif_urls.get(interaction_type, [])
        if gif_list:
            return random.choice(gif_list)
        return None
    
    async def get_emoji(self, emoji_name):
        """Get custom emoji by name from bot application emojis"""
        emoji_display_name = self.emoji_names.get(emoji_name)
        if not emoji_display_name:
            return "❓"
        
        # Try to get from application emojis first
        if self.bot.application:
            try:
                # Fetch application info if not already loaded
                emojis = await self.bot.fetch_application_emojis()
                
                # Search through application emojis
                for emoji in emojis:
                    if emoji.name.lower() == emoji_display_name.lower():
                        return str(emoji)
            except Exception as e:
                logger.error(f"Error fetching application emojis: {e}")
        
        # Fallback to searching in guilds
        for guild in self.bot.guilds:
            emoji = discord.utils.get(guild.emojis, name=emoji_display_name)
            if emoji:
                return str(emoji)
        
        # Fallback to Unicode emoji
        fallback = {
            "kiss": "💋",
            "lick": "👅",
            "hug": "🤗",
            "slap": "👋",
            "punch": "👊",
            "kill": "💀",
            "pat": "👋",
            "poke": "👉",
            "bite": "🦷",
            "cuddle": "🤗",
            "wave": "👋",
            "dance": "💃",
            "cry": "😢",
            "laugh": "😂",
        }
        return fallback.get(emoji_name, "❓")
    
    @app_commands.command(name="kiss", description="Kiss someone with an anime GIF")
    @app_commands.describe(user="User to kiss")
    async def kiss(self, interaction: discord.Interaction, user: discord.Member):
        """Kiss someone"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't kiss yourself! That's just sad...", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("kiss")
        emoji = await self.get_emoji("kiss")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is kissing {user.mention}",
            color=discord.Color.pink()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="lick", description="Lick someone with an anime GIF")
    @app_commands.describe(user="User to lick")
    async def lick(self, interaction: discord.Interaction, user: discord.Member):
        """Lick someone"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ You can't lick yourself!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("lick")
        emoji = await self.get_emoji("lick")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is licking {user.mention}",
            color=discord.Color.purple()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="hug", description="Hug someone with an anime GIF")
    @app_commands.describe(user="User to hug")
    async def hug(self, interaction: discord.Interaction, user: discord.Member):
        """Hug someone"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ Hugging yourself? Here's a virtual hug instead! 🤗", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("hug")
        emoji = await self.get_emoji("hug")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is hugging {user.mention}",
            color=discord.Color.green()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="slap", description="Slap someone with an anime GIF")
    @app_commands.describe(user="User to slap")
    async def slap(self, interaction: discord.Interaction, user: discord.Member):
        """Slap someone"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ Why would you slap yourself?!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("slap")
        emoji = await self.get_emoji("slap")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is slapping {user.mention}",
            color=discord.Color.orange()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="punch", description="Punch someone with an anime GIF")
    @app_commands.describe(user="User to punch")
    async def punch(self, interaction: discord.Interaction, user: discord.Member):
        """Punch someone"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ Don't hurt yourself!", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("punch")
        emoji = await self.get_emoji("punch")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} punched {user.mention}",
            color=discord.Color.red()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="kill", description="Kill someone with a wasted GIF")
    @app_commands.describe(user="User to kill")
    async def kill(self, interaction: discord.Interaction, user: discord.Member):
        """Kill someone (with wasted effect)"""
        if user.id == interaction.user.id:
            await interaction.response.send_message("❌ Suicide is not the answer! Call a helpline if you need help.", ephemeral=True)
            return
        
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("kill")
        emoji = await self.get_emoji("kill")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} sniped {user.mention} ass and killed him LMAO",
            color=discord.Color.dark_red()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="pat", description="Pat someone")
    @app_commands.describe(user="User to pat")
    async def pat(self, interaction: discord.Interaction, user: discord.Member):
        """Pat someone"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("pat")
        emoji = await self.get_emoji("pat")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is patting {user.mention}",
            color=discord.Color.pink()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="poke", description="Poke someone")
    @app_commands.describe(user="User to poke")
    async def poke(self, interaction: discord.Interaction, user: discord.Member):
        """Poke someone"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("poke")
        emoji = await self.get_emoji("poke")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} poked {user.mention}",
            color=discord.Color.blue()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="bite", description="Bite someone")
    @app_commands.describe(user="User to bite")
    async def bite(self, interaction: discord.Interaction, user: discord.Member):
        """Bite someone"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("bite")
        emoji = await self.get_emoji("bite")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} bit {user.mention}",
            color=discord.Color.red()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="cuddle", description="Cuddle someone")
    @app_commands.describe(user="User to cuddle")
    async def cuddle(self, interaction: discord.Interaction, user: discord.Member):
        """Cuddle someone"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("cuddle")
        emoji = await self.get_emoji("cuddle")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is cuddling {user.mention}",
            color=discord.Color.pink()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="wave", description="Wave at someone")
    @app_commands.describe(user="User to wave at")
    async def wave(self, interaction: discord.Interaction, user: discord.Member):
        """Wave at someone"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("wave")
        emoji = await self.get_emoji("wave")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is waving at {user.mention}",
            color=discord.Color.blue()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="dance", description="Dance to a good tune")
    async def dance(self, interaction: discord.Interaction):
        """Dance to a good tune"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("dance")
        emoji = await self.get_emoji("dance")
        
        embed = discord.Embed(
            description=f"{emoji} {interaction.user.mention} is dancing to a good tune",
            color=discord.Color.purple()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="cry", description="Cry (optionally about someone)")
    @app_commands.describe(user="User you're crying about (optional)")
    async def cry(self, interaction: discord.Interaction, user: discord.Member = None):
        """Cry"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("cry")
        emoji = await self.get_emoji("cry")
        
        if user:
            description = f"{emoji} {interaction.user.mention} is crying cause of {user.mention}"
        else:
            description = f"{emoji} {interaction.user.mention} is crying cause they sad"
        
        embed = discord.Embed(
            description=description,
            color=discord.Color.blue()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    
    @app_commands.command(name="laugh", description="Laugh (optionally at someone)")
    @app_commands.describe(user="User you're laughing at (optional)")
    async def laugh(self, interaction: discord.Interaction, user: discord.Member = None):
        """Laugh"""
        await interaction.response.defer()
        
        gif_url = self.get_random_gif("laugh")
        emoji = await self.get_emoji("laugh")
        
        if user:
            description = f"{emoji} {interaction.user.mention} is laughing at {user.mention} cause they stupid"
        else:
            description = f"{emoji} {interaction.user.mention} is laughing"
        
        embed = discord.Embed(
            description=description,
            color=discord.Color.gold()
        )
        
        if gif_url:
            embed.set_image(url=gif_url)
        
        await interaction.followup.send(embed=embed)
    


    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in interactions command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Interactions(bot))
