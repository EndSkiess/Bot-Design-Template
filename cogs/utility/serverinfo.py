import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone

logger = logging.getLogger('Lilith.ServerInfo')


class ServerInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="serverinfo", description="Get detailed information about the server")
    async def serverinfo(self, interaction: discord.Interaction):
        """Display detailed server information"""
        guild = interaction.guild
        
        embed = discord.Embed(
            title=f"Server Information: {guild.name}",
            color=discord.Color.gold()
        )
        
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)
        
        # Basic Info
        embed.add_field(
            name="📊 Basic Info",
            value=f"**Name:** {guild.name}\n"
                  f"**ID:** `{guild.id}`\n"
                  f"**Owner:** {guild.owner.mention}\n"
                  f"**Created:** {discord.utils.format_dt(guild.created_at, 'R')}",
            inline=False
        )
        
        # Member Stats
        total_members = guild.member_count
        bots = sum(1 for member in guild.members if member.bot)
        humans = total_members - bots
        online = sum(1 for member in guild.members if member.status != discord.Status.offline)
        
        embed.add_field(
            name="👥 Members",
            value=f"**Total:** {total_members}\n"
                  f"**Humans:** {humans}\n"
                  f"**Bots:** {bots}\n"
                  f"**Online:** {online}",
            inline=True
        )
        
        # Channel Stats
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        categories = len(guild.categories)
        
        embed.add_field(
            name="💬 Channels",
            value=f"**Text:** {text_channels}\n"
                  f"**Voice:** {voice_channels}\n"
                  f"**Categories:** {categories}\n"
                  f"**Total:** {text_channels + voice_channels}",
            inline=True
        )
        
        # Role Stats
        embed.add_field(
            name="🎭 Roles",
            value=f"**Count:** {len(guild.roles)}\n"
                  f"**Highest:** {guild.roles[-1].mention}",
            inline=True
        )
        
        # Boost Stats
        boost_level = guild.premium_tier
        boost_count = guild.premium_subscription_count or 0
        
        boost_emoji = {
            0: "📊",
            1: "🥉",
            2: "🥈",
            3: "🥇"
        }
        
        embed.add_field(
            name="💎 Boost Status",
            value=f"{boost_emoji.get(boost_level, '📊')} **Level {boost_level}**\n"
                  f"**Boosts:** {boost_count}\n"
                  f"**Boosters:** {len(guild.premium_subscribers)}",
            inline=True
        )
        
        # Server Features
        features = []
        feature_map = {
            'COMMUNITY': '✅ Community',
            'VERIFIED': '✅ Verified',
            'PARTNERED': '✅ Partnered',
            'VANITY_URL': '✅ Vanity URL',
            'BANNER': '✅ Banner',
            'ANIMATED_ICON': '✅ Animated Icon',
            'WELCOME_SCREEN_ENABLED': '✅ Welcome Screen',
            'DISCOVERABLE': '✅ Discoverable',
            'MEMBER_VERIFICATION_GATE_ENABLED': '✅ Membership Screening',
        }
        
        for feature in guild.features:
            if feature in feature_map:
                features.append(feature_map[feature])
        
        if features:
            embed.add_field(
                name="⭐ Features",
                value="\n".join(features[:8]),
                inline=True
            )
        
        # Emoji Stats
        static_emojis = sum(1 for e in guild.emojis if not e.animated)
        animated_emojis = sum(1 for e in guild.emojis if e.animated)
        
        embed.add_field(
            name="😀 Emojis",
            value=f"**Static:** {static_emojis}/{guild.emoji_limit}\n"
                  f"**Animated:** {animated_emojis}/{guild.emoji_limit}\n"
                  f"**Total:** {len(guild.emojis)}",
            inline=True
        )
        
        # Verification Level
        verification_levels = {
            discord.VerificationLevel.none: "None",
            discord.VerificationLevel.low: "Low",
            discord.VerificationLevel.medium: "Medium",
            discord.VerificationLevel.high: "High",
            discord.VerificationLevel.highest: "Highest"
        }
        
        embed.add_field(
            name="🔒 Security",
            value=f"**Verification:** {verification_levels.get(guild.verification_level, 'Unknown')}\n"
                  f"**2FA Required:** {'Yes' if guild.mfa_level else 'No'}",
            inline=True
        )
        
        # Server Banner
        if guild.banner:
            embed.set_image(url=guild.banner.url)
        
        embed.set_footer(text=f"Requested by {interaction.user}", icon_url=interaction.user.display_avatar.url)
        embed.timestamp = datetime.utcnow()
        
        await interaction.response.send_message(embed=embed)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in serverinfo command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ServerInfo(bot))
