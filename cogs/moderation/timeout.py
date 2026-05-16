import discord
from discord.ext import commands
import logging
from datetime import timedelta
from discord import app_commands

logger = logging.getLogger('Lilith.Timeout')


class Timeout(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="timeout", description="Timeout a user")
    @app_commands.describe(
        member="The member to timeout",
        duration="Duration in minutes",
        reason="Reason for the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def timeout(self, interaction: discord.Interaction, member: discord.Member, duration: int, reason: str = "No reason provided"):
        """Timeout a member"""
        try:
            if member.id == interaction.user.id:
                await interaction.response.send_message("❌ You cannot timeout yourself!", ephemeral=True)
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
                await interaction.response.send_message("❌ You cannot timeout someone with a higher or equal role!", ephemeral=True)
                return
            
            if member_top and bot_top and member_top >= bot_top:
                await interaction.response.send_message("❌ I cannot timeout someone with a higher or equal role than me!", ephemeral=True)
                return
            
            if duration <= 0 or duration > 40320:  # Max 28 days
                await interaction.response.send_message("❌ Duration must be between 1 and 40320 minutes (28 days)!", ephemeral=True)
                return
            
            timeout_until = timedelta(minutes=duration)
            await member.timeout(timeout_until, reason=f"{reason} | Timed out by {interaction.user}")
            
            embed = discord.Embed(
                title="⏰ Member Timed Out",
                description=f"{member.mention} has been timed out.",
                color=discord.Color.yellow()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Duration", value=f"{duration} minutes", inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to timeout this user!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ I cannot perform this action here. Make sure I am invited to this server!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error executing timeout: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @timeout.error
    async def timeout_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to timeout members!", ephemeral=True)

    @app_commands.command(name="removetimeout", description="Remove timeout from a user")
    @app_commands.describe(
        member="The member to remove timeout from",
        reason="Reason for removing the timeout"
    )
    @app_commands.checks.has_permissions(moderate_members=True)
    async def removetimeout(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No reason provided"):
        """Remove timeout from a member"""
        try:
            if not member.is_timed_out():
                await interaction.response.send_message(f"❌ {member.mention} is not currently timed out!", ephemeral=True)
                return
            
            await member.timeout(None, reason=f"{reason} | Timeout removed by {interaction.user}")
            
            embed = discord.Embed(
                title="✅ Timeout Removed",
                description=f"{member.mention}'s timeout has been removed.",
                color=discord.Color.green()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Reason", value=reason, inline=False)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to remove timeout from this user!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ I cannot perform this action here. Make sure I am invited to this server!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error removing timeout: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @removetimeout.error
    async def removetimeout_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to remove timeouts from members!", ephemeral=True)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in timeout command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Timeout(bot))
