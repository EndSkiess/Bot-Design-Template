import discord
from discord.ext import commands
import logging
from discord import app_commands

logger = logging.getLogger('Lilith.Purge')


class Purge(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="purge", description="Delete multiple messages")
    @app_commands.describe(
        amount="Number of messages to check/delete (1-5000)",
        user="Only delete messages from this user (optional)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def purge(self, interaction: discord.Interaction, amount: int, user: discord.Member = None):
        """Delete multiple messages from a channel"""
        try:
            if amount <= 0 or amount > 5000:
                await interaction.response.send_message("❌ Amount must be between 1 and 5000!", ephemeral=True)
                return
            
            try:
                await interaction.response.defer(ephemeral=True)
            except discord.errors.NotFound:
                # Interaction already acknowledged or expired
                pass
            
            if user:
                check_func = lambda m: m.author.id == user.id
                deleted = await interaction.channel.purge(limit=amount, check=check_func)
            else:
                deleted = await interaction.channel.purge(limit=amount)
            
            description = f"Successfully deleted {len(deleted)} message(s)."
            if user:
                description += f"\nFiltered for user: {user.mention}"
            
            embed = discord.Embed(
                title="🧹 Messages Purged",
                description=description,
                color=discord.Color.green()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Channel", value=interaction.channel.mention, inline=True)
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
            # Store purge info for annoying feature
            self.bot.last_purge = {
                'moderator': interaction.user,
                'amount': len(deleted),
                'channel': interaction.channel
            }
            
        except discord.Forbidden:
            await interaction.followup.send("❌ I don't have permission to delete messages!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error purging messages: {e}", exc_info=True)
            await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

    @purge.error
    async def purge_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to manage messages!", ephemeral=True)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in purge command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Purge(bot))
