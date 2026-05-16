import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from typing import Dict, Any
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Setup')

class Setup(commands.Cog):
    """Centralized setup commands for all bot features"""
    
    def __init__(self, bot):
        self.bot = bot

    setup_group = app_commands.Group(name="setup", description="Configure bot features")

    # --- SHARED SETTINGS METHODS ---
    async def get_quote_settings(self, guild_id: int) -> Dict[str, Any]:
        return await raven_db.load_document(f"quote/{guild_id}") or {}

    async def save_quote_settings(self, guild_id: int, settings: Dict[str, Any]):
        await raven_db.save_document(f"quote/{guild_id}", settings)

    async def get_uno_settings(self, guild_id: int) -> Dict[str, Any]:
        return await raven_db.load_document(f"uno_setup/{guild_id}") or {}

    async def save_uno_settings(self, guild_id: int, settings: Dict[str, Any]):
        await raven_db.save_document(f"uno_setup/{guild_id}", settings)

    # --- SUBCOMMAND: QUOTE ---
    @setup_group.command(name="quote", description="Configure the quote system settings")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel where quoted messages should go",
        blacklisted_role="An existing role to blacklist from using quotes",
        create_ban_role="Name of a new role to create for banned users (leave empty to skip)"
    )
    async def setup_quote(self, interaction: discord.Interaction, 
                          channel: discord.TextChannel, 
                          blacklisted_role: discord.Role = None,
                          create_ban_role: str = None):
        """Setup quote system settings using slash options"""
        await interaction.response.defer()
        
        guild_id = interaction.guild_id
        settings = await self.get_quote_settings(guild_id)
        
        # 1. Set channel
        settings["channel_id"] = channel.id
        
        # 2. Handle blacklist
        roles = settings.get("blacklisted_roles", [])
        
        if blacklisted_role and blacklisted_role.id not in roles:
            roles.append(blacklisted_role.id)
            
        # 3. Handle new role creation
        new_role_info = ""
        if create_ban_role:
            try:
                new_role = await interaction.guild.create_role(
                    name=create_ban_role, 
                    reason="Quote Ban Role created via setup"
                )
                if new_role.id not in roles:
                    roles.append(new_role.id)
                new_role_info = f"\n✅ Created and added new ban role: **{new_role.name}**"
            except Exception as e:
                new_role_info = f"\n❌ Failed to create role '{create_ban_role}': {e}"
        
        settings["blacklisted_roles"] = roles
        await self.save_quote_settings(guild_id, settings)
        
        embed = discord.Embed(
            title="📜 Quote Setup Updated",
            description=f"✅ **Quote Channel:** {channel.mention}\n"
                        f"✅ **Blacklisted Role:** {blacklisted_role.mention if blacklisted_role else 'None'}"
                        f"{new_role_info}",
            color=discord.Color.green()
        )
        embed.set_footer(text="Settings saved successfully!")
        await interaction.followup.send(embed=embed)

    # --- SUBCOMMAND: UNO ---
    @setup_group.command(name="uno", description="Configure the UNO game settings")
    @app_commands.checks.has_permissions(administrator=True)
    @app_commands.describe(
        channel="The channel where UNO games should be played",
        winner_role="The role to award to the winner",
        role_duration="How long (in minutes) the winner should keep the role"
    )
    async def setup_uno(self, interaction: discord.Interaction, 
                        channel: discord.TextChannel, 
                        winner_role: discord.Role = None,
                        role_duration: int = None):
        """Setup UNO game settings"""
        settings = {
            "channel_id": channel.id,
            "winner_role_id": winner_role.id if winner_role else None,
            "role_duration": role_duration
        }
        await self.save_uno_settings(interaction.guild_id, settings)
        
        embed = discord.Embed(
            title="🎴 UNO Setup Updated",
            description=f"✅ **Game Channel:** {channel.mention}\n"
                        f"✅ **Winner Role:** {winner_role.mention if winner_role else 'None'}\n"
                        f"✅ **Duration:** {role_duration} minutes" if role_duration else "✅ **Duration:** Permanent",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Setup(bot))
