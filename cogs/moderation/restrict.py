"""
Moderation - Chat Restrictions and Bot Access Control
Refactored to use MongoDB for data persistence
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Restrict')

RESTRICTIONS_PREFIX = "restrictions"

class Restrict(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_restrictions(self, guild_id):
        """Load chat restrictions from RavenDB for a specific guild"""
        data = await raven_db.load_document(f"{RESTRICTIONS_PREFIX}/{guild_id}")
        return data.get('restrictions', []) if data else []

    async def save_restrictions(self, guild_id, restrictions):
        """Save chat restrictions to RavenDB for a specific guild"""
        await raven_db.save_document(f"{RESTRICTIONS_PREFIX}/{guild_id}", {'restrictions': restrictions})

    async def get_or_create_no_bots_role(self, guild: discord.Guild) -> discord.Role:
        """Get or create the 'No Bots' role with proper permissions"""
        role_name = "No Bots"
        existing_role = discord.utils.get(guild.roles, name=role_name)
        if existing_role:
            return existing_role
        
        try:
            role = await guild.create_role(
                name=role_name,
                color=discord.Color.dark_gray(),
                reason="Auto-created for bot restrictions",
                permissions=discord.Permissions(use_application_commands=False)
            )
            return role
        except discord.Forbidden:
            raise Exception("Bot lacks permission to create roles!")
        except Exception as e:
            logger.error(f"Error creating role: {e}", exc_info=True)
            raise e

    @app_commands.command(name="restrict", description="Restrict a user from all bots or prevent two users from talking")
    @app_commands.describe(
        user1="First user (or the only user to restrict from all bots)",
        user2="Second user (optional - if provided, restricts chat between both users)",
        reason="Reason for the restriction"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def restrict(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member = None, reason: str = "No reason provided"):
        """Restrict a user from all bots or restrict two users from talking to each other"""
        try:
            if user2 is None:
                if user1.id == interaction.user.id:
                    await interaction.response.send_message("❌ You cannot restrict yourself!", ephemeral=True)
                    return
                if user1.guild_permissions.administrator:
                    await interaction.response.send_message("❌ You cannot restrict administrators!", ephemeral=True)
                    return
                
                no_bots_role = await self.get_or_create_no_bots_role(interaction.guild)
                if no_bots_role in user1.roles:
                    await interaction.response.send_message(f"❌ {user1.mention} is already restricted from using bots!", ephemeral=True)
                    return
                
                await user1.add_roles(no_bots_role, reason=f"{reason} | Restricted by {interaction.user}")
                
                embed = discord.Embed(
                    title="🚫 User Restricted from All Bots",
                    description=f"{user1.mention} has been restricted from using all bots in this server.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                embed.set_thumbnail(url=user1.display_avatar.url)
                await interaction.response.send_message(embed=embed)
            
            else:
                if user1.id == user2.id:
                    await interaction.response.send_message("❌ You cannot restrict a user from themselves!", ephemeral=True)
                    return
                
                guild_id = str(interaction.guild.id)
                restrictions = await self.get_restrictions(guild_id)
                
                pair = sorted([user1.id, user2.id])
                pair_key = f"{pair[0]}_{pair[1]}"
                
                if any(r['pair'] == pair_key for r in restrictions):
                    await interaction.response.send_message("❌ These users are already restricted from each other!", ephemeral=True)
                    return
                
                restrictions.append({
                    'pair': pair_key,
                    'user1': user1.id,
                    'user2': user2.id,
                    'reason': reason,
                    'moderator': interaction.user.id
                })
                await self.save_restrictions(guild_id, restrictions)
                
                embed = discord.Embed(
                    title="🚫 Users Restricted from Chatting",
                    description=f"{user1.mention} and {user2.mention} are now restricted from talking to each other.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                embed.add_field(name="Reason", value=reason, inline=False)
                await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage roles for this user!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error restricting user: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        """Check if message violates chat restrictions"""
        if message.author.bot or not message.guild:
            return
        
        guild_id = str(message.guild.id)
        restrictions = await self.get_restrictions(guild_id)
        if not restrictions:
            return
        
        for restriction in restrictions:
            u1, u2 = restriction['user1'], restriction['user2']
            if message.author.id == u1:
                if any(m.id == u2 for m in message.mentions):
                    await message.delete()
                    await message.channel.send(f"❌ {message.author.mention}, you are restricted from interacting with that user!", delete_after=5)
                    return
            elif message.author.id == u2:
                if any(m.id == u1 for m in message.mentions):
                    await message.delete()
                    await message.channel.send(f"❌ {message.author.mention}, you are restricted from interacting with that user!", delete_after=5)
                    return

    @app_commands.command(name="unrestrict", description="Remove restriction from user(s)")
    @app_commands.describe(
        user1="First user (or the only user to unrestrict from bots)",
        user2="Second user (optional - if provided, removes chat restriction between both users)"
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def unrestrict(self, interaction: discord.Interaction, user1: discord.Member, user2: discord.Member = None):
        """Remove restriction from user(s)"""
        try:
            if user2 is None:
                no_bots_role = discord.utils.get(interaction.guild.roles, name="No Bots")
                if not no_bots_role or no_bots_role not in user1.roles:
                    await interaction.response.send_message(f"❌ {user1.mention} is not restricted from using bots!", ephemeral=True)
                    return
                
                await user1.remove_roles(no_bots_role, reason=f"Unrestricted by {interaction.user}")
                embed = discord.Embed(
                    title="✅ Bot Restriction Removed",
                    description=f"{user1.mention} can now use bots again.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                await interaction.response.send_message(embed=embed)
            
            else:
                guild_id = str(interaction.guild.id)
                restrictions = await self.get_restrictions(guild_id)
                pair = sorted([user1.id, user2.id])
                pair_key = f"{pair[0]}_{pair[1]}"
                
                new_restrictions = [r for r in restrictions if r['pair'] != pair_key]
                if len(new_restrictions) == len(restrictions):
                    await interaction.response.send_message("❌ These users are not restricted from each other!", ephemeral=True)
                    return
                
                await self.save_restrictions(guild_id, new_restrictions)
                embed = discord.Embed(
                    title="✅ Chat Restriction Removed",
                    description=f"{user1.mention} and {user2.mention} can now interact with each other.",
                    color=discord.Color.green()
                )
                embed.add_field(name="Moderator", value=interaction.user.mention, inline=True)
                await interaction.response.send_message(embed=embed)
            
        except discord.Forbidden:
            await interaction.response.send_message("❌ I don't have permission to manage roles for this user!", ephemeral=True)
        except Exception as e:
            logger.error(f"Error unrestricting user: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

    @app_commands.command(name="restrictions", description="View all restrictions")
    @app_commands.checks.has_permissions(manage_messages=True)
    async def restrictions(self, interaction: discord.Interaction):
        """View all restrictions in the server"""
        try:
            guild_id = str(interaction.guild.id)
            no_bots_role = discord.utils.get(interaction.guild.roles, name="No Bots")
            bot_members = no_bots_role.members if no_bots_role else []
            chat_restrictions = await self.get_restrictions(guild_id)
            
            if not bot_members and not chat_restrictions:
                await interaction.response.send_message("✅ No restrictions are currently active in this server!", ephemeral=True)
                return
            
            embed = discord.Embed(title="🚫 Active Restrictions", color=discord.Color.red())
            if bot_members:
                embed.add_field(name="🤖 Bot Restrictions", value="\n".join(f"• {m.mention}" for m in bot_members), inline=False)
            if chat_restrictions:
                lines = []
                for r in chat_restrictions:
                    u1 = interaction.guild.get_member(r['user1']) or f"<@{r['user1']}>"
                    u2 = interaction.guild.get_member(r['user2']) or f"<@{r['user2']}>"
                    lines.append(f"• {u1.mention if hasattr(u1, 'mention') else u1} ↔️ {u2.mention if hasattr(u2, 'mention') else u2} - {r['reason']}")
                embed.add_field(name="💬 Chat Restrictions", value="\n".join(lines), inline=False)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        except Exception as e:
            logger.error(f"Error listing restrictions: {e}", exc_info=True)
            await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Restrict(bot))
