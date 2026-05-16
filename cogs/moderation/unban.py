import discord
from discord.ext import commands
import logging
from discord import app_commands

logger = logging.getLogger('Lilith.Unban')


class Unban(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="unban", description="Unban a user from the server")
    @app_commands.describe(
        user_id="The ID of the user to unban"
    )
    @app_commands.checks.has_permissions(ban_members=True)
    async def unban(self, interaction: discord.Interaction, user_id: str):
        """Unban a user from the server"""
        try:
            # Convert user_id to int
            try:
                user_id_int = int(user_id)
            except ValueError:
                await interaction.response.send_message("❌ Invalid user ID! Please provide a valid numeric user ID.", ephemeral=True)
                return
            
            # Fetch the user
            try:
                user = await self.bot.fetch_user(user_id_int)
            except discord.NotFound:
                await interaction.response.send_message("❌ User not found! Please check the user ID.", ephemeral=True)
                return
            
            # Check if user is actually banned
            try:
                await interaction.guild.fetch_ban(user)
            except discord.NotFound:
                await interaction.response.send_message(f"❌ {user.mention} is not banned!", ephemeral=True)
                return
            
            # Unban the user
            await interaction.guild.unban(user, reason=f"Unbanned by {interaction.user}")
            
            embed = discord.Embed(
                title="✅ Member Unbanned",
                description=f"**{user}** has been unbanned from the server.",
                color=discord.Color.green()
            )
            embed.add_field(name="User ID", value=str(user.id), inline=True)
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to unban users!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error unbanning user: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @unban.error
    async def unban_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to unban members!", ephemeral=True)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in unban command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Unban(bot))
