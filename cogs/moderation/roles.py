import discord
from discord.ext import commands
import logging
from discord import app_commands

logger = logging.getLogger('Lilith.Roles')


class Roles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="giverole", description="Give a role to a user")
    @app_commands.describe(
        member="The member to give the role to",
        role="The role to give"
    )
    @app_commands.checks.has_permissions(manage_roles=True)
    async def give_role(self, interaction: discord.Interaction, member: discord.Member, role: discord.Role):
        """Give a role to a member"""
        try:
            # Safely fetch top roles if cache is empty (prevents NoneType TypeError)
            try:
                user_top = getattr(interaction.user, 'top_role', None) 
                bot_top = interaction.guild.me.top_role
            except TypeError:
                try:
                    if interaction.guild and not interaction.guild.roles:
                        await interaction.guild.fetch_roles()
                        user_top = getattr(interaction.user, 'top_role', None)
                        bot_top = interaction.guild.me.top_role
                    else:
                        user_top = bot_top = None
                except discord.HTTPException:
                    user_top = bot_top = None

            if bot_top and role >= bot_top:
                await interaction.response.send_message("❌ I cannot assign a role that is higher than or equal to my highest role!", ephemeral=True)
                return
            
            if user_top and role >= user_top and interaction.user.id != interaction.guild.owner_id:
                await interaction.response.send_message("❌ You cannot assign a role that is higher than or equal to your highest role!", ephemeral=True)
                return
            
            if role in member.roles:
                await interaction.response.send_message(f"❌ {member.mention} already has the {role.mention} role!", ephemeral=True)
                return
            
            await member.add_roles(role, reason=f"Role given by {interaction.user}")
            
            embed = discord.Embed(
                title="✅ Role Given",
                description=f"{role.mention} has been given to {member.mention}.",
                color=discord.Color.green()
            )
            embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
            embed.add_field(name="Member", value=member.mention, inline=True)
            embed.set_thumbnail(url=member.display_avatar.url)
            
            await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage roles!", ephemeral=True)
        except discord.NotFound:
            await interaction.response.send_message("❌ I cannot perform this action here. Make sure I am invited to this server!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error giving role: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @give_role.error
    async def give_role_error(self, interaction: discord.Interaction, error):
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to manage roles!", ephemeral=True)



    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in roles command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Roles(bot))
