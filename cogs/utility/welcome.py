"""
Welcome and Goodbye system - Send messages when members join or leave
Refactored to use MongoDB for data persistence
"""
import discord
from discord.ext import commands
from discord import app_commands, ui
import re
import logging
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Welcome')

WELCOME_PREFIX = "welcome"

class WelcomeEmbedModal(ui.Modal):
    """Modal for custom welcome/goodbye embed configuration"""
    
    def __init__(self, title_text, config_type, channel_id, current_data=None):
        super().__init__(title=title_text)
        self.config_type = config_type
        self.channel_id = channel_id
        
        # Populate with current data if available
        current = current_data or {}
        
        self.embed_title = ui.TextInput(
            label="Embed Title",
            placeholder="Welcome to our server!",
            default=current.get("title", ""),
            required=False,
            max_length=256
        )
        self.description = ui.TextInput(
            label="Embed Description",
            style=discord.TextStyle.paragraph,
            placeholder="Welcome {user-mention} to {guild}! You are member #{member-count}.",
            default=current.get("description", ""),
            required=True,
            max_length=4000
        )
        self.color = ui.TextInput(
            label="Embed Color (Hex Code)",
            placeholder="#00FF00",
            default=current.get("color", "#5865F2"),
            required=False,
            max_length=7
        )
        self.image_url = ui.TextInput(
            label="Image/GIF URL",
            placeholder="https://example.com/welcome.gif",
            default=current.get("image", ""),
            required=False
        )
        self.footer = ui.TextInput(
            label="Footer Text",
            placeholder="We hope you enjoy your stay!",
            default=current.get("footer", ""),
            required=False,
            max_length=2048
        )
        
        self.add_item(self.embed_title)
        self.add_item(self.description)
        self.add_item(self.color)
        self.add_item(self.image_url)
        self.add_item(self.footer)

    async def on_submit(self, interaction: discord.Interaction):
        # Validate color
        color_hex = self.color.value.lstrip('#')
        try:
            if color_hex:
                int(color_hex, 16)
            else:
                color_hex = "5865F2" # Default Discord Blue
        except ValueError:
            await interaction.response.send_message("❌ Invalid hex color code! Use format like #FF0000", ephemeral=True)
            return

        cog = interaction.client.get_cog("Welcome")
        if not cog:
            await interaction.response.send_message("❌ System error: Cog not found.", ephemeral=True)
            return

        guild_id_str = str(interaction.guild.id)
        doc_id = f"{WELCOME_PREFIX}/{guild_id_str}"
        
        # Load existing config to merge
        guild_config = await raven_db.load_document(doc_id) or {}
        
        # Update specific config type for the guild
        guild_config[self.config_type] = {
            'channel_id': self.channel_id,
            'is_embed': True,
            'embed_data': {
                'title': self.embed_title.value,
                'description': self.description.value,
                'color': f"#{color_hex}",
                'image': self.image_url.value,
                'footer': self.footer.value
            }
        }
        
        await raven_db.save_document(doc_id, guild_config)
        
        embed = discord.Embed(
            title=f"✅ {self.config_type.capitalize()} Embed Set!",
            description=f"Welcome messages in <#{self.channel_id}> will now use your custom embed.",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class Welcome(commands.Cog):
    """Welcome and goodbye message system"""
    
    def __init__(self, bot):
        self.bot = bot
    
    async def load_guild_config(self, guild_id):
        """Load welcome/goodbye configuration for a specific guild"""
        return await raven_db.load_document(f"{WELCOME_PREFIX}/{guild_id}") or {}
    
    def replace_tags(self, message: str, member: discord.Member, guild: discord.Guild, allow_mentions: bool = True) -> str:
        """Replace tags in message with actual values"""
        if not message:
            return ""
            
        message = message.replace("{user}", member.display_name)
        
        if allow_mentions:
            message = message.replace("{user-mention}", member.mention)
        else:
            # In titles/footers, mentions don't render, so use display name
            message = message.replace("{user-mention}", member.display_name)
            
        message = message.replace("{user-id}", str(member.id))
        message = message.replace("{guild}", guild.name)
        message = message.replace("{member-count}", str(guild.member_count))
        
        channel_pattern = r'\{channel-(\d+)\}'
        matches = re.finditer(channel_pattern, message)
        
        for match in matches:
            channel_id = int(match.group(1))
            channel = guild.get_channel(channel_id)
            if channel:
                message = message.replace(match.group(0), channel.mention)
        
        return message
    
    @app_commands.command(name="setwelcome", description="Set welcome message for new members")
    @app_commands.describe(
        channel="Channel to send welcome messages",
        use_embed="Whether to use a fancy embed or plain text"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setwelcome(self, interaction: discord.Interaction, channel: discord.TextChannel, use_embed: bool = True):
        """Set welcome message"""
        if use_embed:
            config = await self.load_guild_config(interaction.guild.id)
            current = config.get("welcome", {}).get("embed_data", {})
            modal = WelcomeEmbedModal("Welcome Embed Setup", "welcome", channel.id, current)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ Plain text mode is being deprecated in favor of embeds. Please use `use_embed: True`", ephemeral=True)

    @app_commands.command(name="setgoodbye", description="Set goodbye message for leaving members")
    @app_commands.describe(
        channel="Channel to send goodbye messages",
        use_embed="Whether to use a fancy embed or plain text"
    )
    @app_commands.checks.has_permissions(manage_guild=True)
    async def setgoodbye(self, interaction: discord.Interaction, channel: discord.TextChannel, use_embed: bool = True):
        """Set goodbye message"""
        if use_embed:
            config = await self.load_guild_config(interaction.guild.id)
            current = config.get("goodbye", {}).get("embed_data", {})
            modal = WelcomeEmbedModal("Goodbye Embed Setup", "goodbye", channel.id, current)
            await interaction.response.send_modal(modal)
        else:
            await interaction.response.send_message("❌ Plain text mode is being deprecated in favor of embeds. Please use `use_embed: True`", ephemeral=True)

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        """Send welcome message when member joins"""
        await self._send_notification(member, member.guild, 'welcome')

    @commands.Cog.listener()
    async def on_raw_member_remove(self, payload: discord.RawMemberRemoveEvent):
        """Send goodbye message when member leaves (Raw listener for cache-less reliability)"""
        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            try: guild = await self.bot.fetch_guild(payload.guild_id)
            except: return
            
        await self._send_notification(payload.user, guild, 'goodbye')

    async def _send_notification(self, member, guild, config_type):
        """Generic handler for welcome/goodbye notifications"""
        config = await self.load_guild_config(guild.id)
        if not config or config_type not in config:
            return
            
        data = config[config_type]
        channel = guild.get_channel(data['channel_id'])
        
        # Fallback if channel is not in cache
        if not channel:
            try:
                channel = await guild.fetch_channel(data['channel_id'])
            except Exception:
                pass
        
        if not channel:
            logger.warning(f"Could not find channel for {config_type} in {guild.name}")
            return

        try:
            if data.get('is_embed'):
                embed_data = data['embed_data']
                embed = discord.Embed(
                    # Disable mentions in title as they don't render
                    title=self.replace_tags(embed_data.get('title', ''), member, guild, allow_mentions=False),
                    description=self.replace_tags(embed_data.get('description', ''), member, guild),
                )
                
                color_str = embed_data.get('color', '#5865F2').lstrip('#')
                try:
                    embed.color = discord.Color(int(color_str, 16))
                except:
                    embed.color = discord.Color.blue()
                
                if embed_data.get('image'):
                    embed.set_image(url=embed_data['image'])
                
                if embed_data.get('footer'):
                    # Disable mentions in footer as they don't render
                    embed.set_footer(text=self.replace_tags(embed_data['footer'], member, guild, allow_mentions=False))
                
                avatar_url = member.display_avatar.url if hasattr(member, 'display_avatar') else member.avatar.url if member.avatar else None
                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)
                    
                await channel.send(embed=embed)
            else:
                message = self.replace_tags(data.get('message', ''), member, guild)
                if message:
                    await channel.send(message)
        except discord.Forbidden:
            logger.warning(f"Forbidden to send {config_type} message in {guild.name}")
        except Exception as e:
            logger.error(f"Error sending {config_type} message: {e}")

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"⏳ This command is on cooldown. Try again in {error.retry_after:.2f}s.", ephemeral=True)
        elif isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have permission to use this command.", ephemeral=True)
        else:
            logger.error(f"Error in welcome/goodbye command '{interaction.command.name}': {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Welcome(bot))
