"""
Moderation - Temporary Bans
Refactored to use MongoDB for data persistence
"""
import discord
from discord.ext import commands, tasks
from discord import app_commands
import logging
from datetime import datetime, UTC, timedelta
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.TempBan')

TEMPBANS_PREFIX = "tempbans"

class TempBan(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_tempbans.start()

    async def get_all_tempbans(self):
        """Load all tempbans from RavenDB"""
        docs = await raven_db.get_all_in_collection(TEMPBANS_PREFIX, limit=1000)
        tempbans = {}
        for doc in docs:
            # Reconstruct key as used in original DB if needed, 
            # but RavenDB ID is unique enough.
            doc_id = doc['@metadata']['@id'].split('/')[-1]
            tempbans[doc_id] = doc
        return tempbans

    async def save_tempban(self, guild_id, user_id, data):
        """Save a tempban to RavenDB"""
        key = f"{guild_id}_{user_id}"
        await raven_db.save_document(f"{TEMPBANS_PREFIX}/{key}", data)

    async def delete_tempban(self, key):
        """Delete a tempban from RavenDB"""
        await raven_db.delete_document(f"{TEMPBANS_PREFIX}/{key}")

    @app_commands.command(name="tempban", description="Temporarily ban a user")
    @app_commands.describe(
        member="The member to temporarily ban",
        duration="Duration in hours",
        reason="Reason for the ban"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def tempban(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
        """Temporarily ban a member"""
        try:
            if member.id == interaction.user.id:
                await interaction.response.send_message("❌ You cannot tempban yourself!", ephemeral=True)
                return
            
            # Safely fetch top roles if cache is empty (prevents NoneType TypeError)
            try:
                member_top = member.top_role
                user_top = getattr(interaction.user, 'top_role', None) 
                bot_top = interaction.guild.me.top_role
            except TypeError:
                try:
                    if interaction.guild and not interaction.guild.roles:
                        await interaction.guild.fetch_roles()
                        member_top = member.top_role
                        user_top = getattr(interaction.user, 'top_role', None)
                        bot_top = interaction.guild.me.top_role
                    else:
                        member_top = user_top = bot_top = None
                except discord.HTTPException:
                    member_top = user_top = bot_top = None

            if member_top and user_top and member_top >= user_top:
                await interaction.response.send_message("❌ You cannot tempban someone with a higher or equal role!", ephemeral=True)
                return
            
            if member_top and bot_top and member_top >= bot_top:
                await interaction.response.send_message("❌ I cannot tempban someone with a higher or equal role than me!", ephemeral=True)
                return
            
            if duration <= 0:
                await interaction.response.send_message("❌ Duration must be greater than 0!", ephemeral=True)
                return
            
            unban_time = (datetime.now(UTC) + timedelta(hours=duration)).isoformat()
            
            await member.ban(reason=f"[TEMPBAN] {reason} | Banned by {interaction.user}")
            
            data = {
                'guild_id': interaction.guild.id,
                'user_id': member.id,
                'unban_time': unban_time,
                'reason': reason,
                'moderator': str(interaction.user)
            }
            await self.save_tempban(interaction.guild.id, member.id, data)
            
            embed = discord.Embed(
                title="⏱️ Member Temporarily Banned",
                description=f"{member.mention} has been temporarily banned.",
                color=discord.Color.red()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Duration", value=f"{duration} hours", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to ban this user!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ I cannot perform this action here. Make sure I am invited to this server!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error tempbanning member: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @tasks.loop(minutes=5)
    async def check_tempbans(self):
        """Check for expired tempbans and unban users"""
        tempbans = await self.get_all_tempbans()
        if not tempbans:
            return

        now = datetime.now(UTC)
        for key, data in tempbans.items():
            unban_time = datetime.fromisoformat(data['unban_time'])
            if unban_time.tzinfo is None: unban_time = unban_time.replace(tzinfo=UTC)
            
            if now >= unban_time:
                guild = self.bot.get_guild(data['guild_id'])
                if guild:
                    try:
                        user = await self.bot.fetch_user(data['user_id'])
                        await guild.unban(user, reason="Tempban expired")
                        await self.delete_tempban(key)
                    except Exception as e:
                        logger.error(f"Failed to unban {data['user_id']}: {e}", exc_info=True)

    @check_tempbans.before_loop
    async def before_check_tempbans(self):
        await self.bot.wait_until_ready()

    def cog_unload(self):
        self.check_tempbans.cancel()

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in tempban command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TempBan(bot))
