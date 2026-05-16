import discord
from discord.ext import commands
import logging
from discord import app_commands

logger = logging.getLogger('Lilith.Avatar')


class Avatar(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="avatar", description="Get a user's full HD avatar")
    @app_commands.describe(user="The user whose avatar you want to see (leave empty for yourself)")
    async def avatar(self, interaction: discord.Interaction, user: discord.Member = None):
        """Get a user's avatar in full HD"""
        target = user or interaction.user
        
        # Get avatar URLs
        avatar_url = target.display_avatar.url
        avatar_url_large = target.display_avatar.with_size(4096).url
        
        embed = discord.Embed(
            title=f"{target.display_name}'s Avatar",
            color=target.color if target.color != discord.Color.default() else discord.Color.blue()
        )
        embed.set_image(url=avatar_url_large)
        embed.add_field(name="User", value=target.mention, inline=True)
        embed.add_field(name="User ID", value=f"`{target.id}`", inline=True)
        
        # Add download links
        formats = []
        if target.avatar:
            formats.append(f"[PNG]({target.avatar.with_size(4096).with_format('png').url})")
            formats.append(f"[JPG]({target.avatar.with_size(4096).with_format('jpg').url})")
            formats.append(f"[WEBP]({target.avatar.with_size(4096).with_format('webp').url})")
            
            if target.avatar.is_animated():
                formats.append(f"[GIF]({target.avatar.with_size(4096).with_format('gif').url})")
        
        if formats:
            embed.add_field(name="Download", value=" • ".join(formats), inline=False)
        
        embed.set_footer(text="Full HD 4096x4096")
        
        await interaction.response.defer()
        await interaction.followup.send(embed=embed)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in avatar command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Avatar(bot))
