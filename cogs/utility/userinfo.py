import discord
from discord.ext import commands
from discord import app_commands
import logging
from datetime import datetime, timezone

logger = logging.getLogger('Lilith.UserInfo')


class UserInfo(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="userinfo", description="Get detailed information about a user")
    @app_commands.describe(user="The user to get information about (leave empty for yourself)")
    async def userinfo(self, interaction: discord.Interaction, user: discord.Member = None):
        """Display detailed user information"""
        target = user or interaction.user
        
        # Calculate account age (use timezone-aware datetime)
        account_created = target.created_at
        now = datetime.now(timezone.utc)
        account_age = (now - account_created).days
        
        # Calculate server join time
        joined_server = target.joined_at
        if joined_server:
            server_age = (now - joined_server).days
        else:
            server_age = 0
        
        embed = discord.Embed(
            title=f"User Information: {target}",
            color=target.color if target.color != discord.Color.default() else discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        
        # Basic Info
        embed.add_field(
            name="👤 Basic Info",
            value=f"**Username:** {target.name}\n"
                  f"**Display Name:** {target.display_name}\n"
                  f"**ID:** `{target.id}`\n"
                  f"**Bot:** {'Yes' if target.bot else 'No'}",
            inline=False
        )
        
        # Account Dates
        embed.add_field(
            name="📅 Account Created",
            value=f"{discord.utils.format_dt(account_created, 'F')}\n"
                  f"({discord.utils.format_dt(account_created, 'R')})\n"
                  f"**Age:** {account_age} days old",
            inline=True
        )
        
        if joined_server:
            embed.add_field(
                name="📥 Joined Server",
                value=f"{discord.utils.format_dt(joined_server, 'F')}\n"
                      f"({discord.utils.format_dt(joined_server, 'R')})\n"
                      f"**Member for:** {server_age} days",
                inline=True
            )
        
        # Roles
        roles = [role.mention for role in target.roles[1:]]  # Skip @everyone
        if roles:
            roles_text = ", ".join(roles[:20])  # Limit to 20 roles
            if len(target.roles) > 21:
                roles_text += f" *+{len(target.roles) - 21} more*"
        else:
            roles_text = "No roles"
        
        embed.add_field(
            name=f"🎭 Roles [{len(target.roles) - 1}]",
            value=roles_text,
            inline=False
        )
        
        # Status and Activity
        status_emoji = {
            discord.Status.online: "🟢 Online",
            discord.Status.idle: "🟡 Idle",
            discord.Status.dnd: "🔴 Do Not Disturb",
            discord.Status.offline: "⚫ Offline"
        }
        
        embed.add_field(
            name="💫 Status",
            value=status_emoji.get(target.status, "⚫ Unknown"),
            inline=True
        )
        
        # Permissions
        key_perms = []
        if target.guild_permissions.administrator:
            key_perms.append("Administrator")
        if target.guild_permissions.manage_guild:
            key_perms.append("Manage Server")
        if target.guild_permissions.manage_roles:
            key_perms.append("Manage Roles")
        if target.guild_permissions.manage_channels:
            key_perms.append("Manage Channels")
        if target.guild_permissions.kick_members:
            key_perms.append("Kick Members")
        if target.guild_permissions.ban_members:
            key_perms.append("Ban Members")
        
        if key_perms:
            embed.add_field(
                name="🔑 Key Permissions",
                value=", ".join(key_perms[:5]),
                inline=True
            )
        
        # Boost Status
        if target.premium_since:
            embed.add_field(
                name="💎 Server Booster",
                value=f"Since {discord.utils.format_dt(target.premium_since, 'R')}",
                inline=True
            )
        
        # Avatar
        embed.add_field(
            name="🖼️ Avatar",
            value=f"[View Full Size]({target.display_avatar.with_size(4096).url})",
            inline=True
        )
        
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
            logger.error(f"Error in userinfo command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(UserInfo(bot))
