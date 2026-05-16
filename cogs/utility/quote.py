"""
Quote System
Refactored to use MongoDB for data persistence
"""
import discord
from discord.ext import commands
from discord import app_commands
import io
import os
import aiohttp
from PIL import Image, ImageDraw, ImageFont, ImageOps
import logging
from ..utils.ravendb_manager import raven_db

logger = logging.getLogger('Lilith.Quote')

QUOTE_PREFIX = "quote"
FONT_PATH_CACHE = None

class DeleteQuoteButton(discord.ui.View):
    """View with a delete button for quotes"""
    def __init__(self, quote_creator_id: int, quoted_user_id: int):
        super().__init__(timeout=None)
        self.quote_creator_id = quote_creator_id
        self.quoted_user_id = quoted_user_id
    
    @discord.ui.button(label="Delete Quote", style=discord.ButtonStyle.danger, emoji="🗑️")
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in [self.quote_creator_id, self.quoted_user_id]:
            await interaction.response.send_message("❌ Only the quote creator or quoted user can delete this.", ephemeral=True)
            return
        
        try:
            await interaction.message.delete()
            await interaction.response.send_message("✅ Quote deleted!", ephemeral=True)
        except:
            await interaction.response.send_message("❌ Failed to delete quote.", ephemeral=True)


class Quote(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self._recent_quotes = {} # {message_id: timestamp} 
        self.ctx_menu = app_commands.ContextMenu(
            name="Make it a Quote",
            callback=self.quote_context_menu,
        )
        self.bot.tree.add_command(self.ctx_menu)

    async def cog_unload(self):
        self.bot.tree.remove_command(self.ctx_menu.name, type=self.ctx_menu.type)

    async def get_settings(self, guild_id):
        """Load quote settings from RavenDB for a specific guild"""
        return await raven_db.load_document(f"{QUOTE_PREFIX}/{guild_id}") or {}

    async def save_settings(self, guild_id, settings):
        """Save quote settings to RavenDB for a specific guild"""
        await raven_db.save_document(f"{QUOTE_PREFIX}/{guild_id}", settings)

    def is_duplicate(self, message_id: int) -> bool:
        """Check if this message was recently quoted (TTL: 60s)"""
        import time
        now = time.time()
        
        # Cleanup old entries first
        expired = [mid for mid, ts in self._recent_quotes.items() if now - ts > 60]
        for mid in expired: del self._recent_quotes[mid]
        
        if message_id in self._recent_quotes:
            return True
            
        self._recent_quotes[message_id] = now
        return False

    def load_font(self, size):
        """Load the best available font"""
        import pathlib
        global FONT_PATH_CACHE

        # 1. Try Cache
        if FONT_PATH_CACHE and os.path.exists(FONT_PATH_CACHE):
            try: return ImageFont.truetype(FONT_PATH_CACHE, size)
            except: pass

        root = pathlib.Path(__file__).parent.parent.parent
        
        # 2. Try preferred fonts in the fonts folder (FAST)
        preferred = ["OpenSans-VariableFont_wdth,wght.ttf", "Snowman Varsity.ttf", "Richocet Bold.ttf"]
        for font_name in preferred:
            font_path = root / "fonts" / font_name
            if font_path.exists():
                try:
                    FONT_PATH_CACHE = str(font_path)
                    return ImageFont.truetype(str(font_path), size)
                except Exception as e:
                    logger.warning(f"Error loading preferred font {font_name}: {e}")
                    FONT_PATH_CACHE = None
        
        # 3. Fallback to system fonts (slower)
        # Prioritize Monospaced fonts for the "clean Courier" look
        sys_fonts = [
            "cour.ttf", "DejaVuSansMono.ttf", "LiberationMono-Regular.ttf", # Monospaced
            "arial.ttf", "DejaVuSans.ttf", "Verdana.ttf", "LiberationSans-Regular.ttf" # Sans
        ]
        for name in sys_fonts:
            # Windows
            win_p = pathlib.Path("C:/Windows/Fonts") / name
            if win_p.exists():
                try:
                    FONT_PATH_CACHE = str(win_p)
                    return ImageFont.truetype(str(win_p), size)
                except: pass
            # Linux (Render)
            linux_paths = ["/usr/share/fonts", "/usr/local/share/fonts", "/usr/share/fonts/truetype"]
            for lp in linux_paths:
                lp_p = pathlib.Path(lp)
                if lp_p.exists():
                    for sp in lp_p.rglob(name):
                        try:
                            FONT_PATH_CACHE = str(sp)
                            return ImageFont.truetype(str(sp), size)
                        except: pass
        
        # 4. Last resort
        FONT_PATH_CACHE = None
        return ImageFont.load_default()


    async def quote_context_menu(self, interaction: discord.Interaction, message: discord.Message):
        """Context menu to quote a message"""
        if self.is_duplicate(message.id):
            await interaction.response.send_message("⚠️ This message is already being quoted!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        
        try:
            img_buffer, is_gif = await self.generate_quote_image(message)
        except Exception as e:
            logger.error(f"Failed to generate quote image: {e}")
            await interaction.followup.send("❌ Failed to generate quote image.", ephemeral=True)
            return

        target_channel = None
        if interaction.guild_id:
            settings = await self.get_settings(interaction.guild_id)
            if settings:
                if "blacklisted_roles" in settings:
                    member = interaction.guild.get_member(interaction.user.id)
                    if member and any(r.id in settings["blacklisted_roles"] for r in member.roles):
                        await interaction.followup.send("❌ You are banned from using quotes.", ephemeral=True)
                        return
                if "channel_id" in settings:
                    target_channel = self.bot.get_channel(settings["channel_id"])
        
        filename = "quote.gif" if is_gif else "quote.png"
        file = discord.File(fp=img_buffer, filename=filename)
        embed = discord.Embed(description=f"💬 Quote by {interaction.user.mention}", color=discord.Color.blurple())
        embed.set_image(url=f"attachment://{filename}")
        embed.set_footer(text=f"Quoted: {message.author.display_name}", icon_url=message.author.display_avatar.url)
        
        view = DeleteQuoteButton(quote_creator_id=interaction.user.id, quoted_user_id=message.author.id)
        
        if target_channel:
            try:
                await target_channel.send(embed=embed, file=file, view=view)
                await interaction.followup.send(f"✅ Quote sent to {target_channel.mention}!", ephemeral=True)
                return
            except: pass
        
        try:
            await interaction.user.send(embed=embed, file=file, view=view)
            await interaction.followup.send("✅ Quote sent to your DMs!", ephemeral=True)
        except:
            await interaction.followup.send("❌ Could not send quote (Check your DM settings).", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot or not message.guild:
            return
        
        if message.reference and self.bot.user in message.mentions:
            guild_id = str(message.guild.id)
            settings = await self.get_settings(guild_id)
            if not settings: return
                
            roles = settings.get("blacklisted_roles", [])
            if any(r.id in roles for r in message.author.roles):
                await message.reply("❌ You have been banned from quoting.", delete_after=5)
                return

            if self.is_duplicate(message.reference.message_id):
                # Optionally react with something to show we saw it
                await message.add_reaction("⏳")
                return

            try:
                original = await message.channel.fetch_message(message.reference.message_id)
                
                # FIX: Don't quote the bot itself! This prevents accidental quotes during setup/help
                if original.author.id == self.bot.user.id:
                    return

                img_buffer, is_gif = await self.generate_quote_image(original)
                
                output_channel = self.bot.get_channel(settings.get("channel_id"))
                if output_channel:
                    filename = "quote.gif" if is_gif else "quote.png"
                    file = discord.File(fp=img_buffer, filename=filename)
                    embed = discord.Embed(description=f"💬 Quote by {message.author.mention}", color=discord.Color.blurple())
                    embed.set_image(url=f"attachment://{filename}")
                    embed.set_footer(text=f"Quoted: {original.author.display_name}", icon_url=original.author.display_avatar.url)
                    view = DeleteQuoteButton(quote_creator_id=message.author.id, quoted_user_id=original.author.id)
                    await output_channel.send(embed=embed, file=file, view=view)
                    await message.add_reaction("✅")
            except Exception as e:
                logger.error(f"Error in quote on_message: {e}")

    async def generate_quote_image(self, message: discord.Message):
        """
        Generate a quote image with a vertical vertical layout: 
        Avatar (Top) -> Border -> Name -> Date -> Quote (Bottom)
        """
        content = message.clean_content or ("[Image Attachment]" if message.attachments else "[Empty Message]")
        WIDTH, HEIGHT = 900, 500
        TEXT_COLOR = (255, 255, 255)
        NAME_COLOR = (220, 220, 220)
        DATE_COLOR = (180, 180, 180)
        
        try: user = await self.bot.fetch_user(message.author.id)
        except: user = message.author
        
        # Load avatar
        avatar_asset = message.author.display_avatar.with_size(256)
        avatar_buffer = io.BytesIO()
        await avatar_asset.save(avatar_buffer)
        avatar_buffer.seek(0)
        
        avatar_img = Image.open(avatar_buffer)
        is_animated_avatar = getattr(avatar_img, 'is_animated', False)
        
        avatar_frames = []
        max_frames = 5
        if is_animated_avatar:
            try:
                num = min(avatar_img.n_frames, max_frames)
                for i in range(num):
                    avatar_img.seek(i)
                    avatar_frames.append(avatar_img.convert("RGBA").copy())
            except: avatar_frames = [avatar_img.convert("RGBA")]
        else: avatar_frames = [avatar_img.convert("RGBA")]
        
        banner_img = None
        if hasattr(user, 'banner') and user.banner:
            try:
                banner_asset = user.banner.with_size(512)
                bb = io.BytesIO()
                await banner_asset.save(bb)
                bb.seek(0)
                banner_img = Image.open(bb).convert("RGBA")
            except: pass
        
        decoration_frames = []
        try:
            if hasattr(message.author, 'avatar_decoration') and message.author.avatar_decoration:
                dbuf = io.BytesIO()
                await message.author.avatar_decoration.save(dbuf)
                dbuf.seek(0)
                dimg = Image.open(dbuf)
                dec_frames_count = getattr(dimg, 'n_frames', 1)
                for f in range(min(dec_frames_count, max_frames)):
                    dimg.seek(f)
                    decoration_frames.append(dimg.convert("RGBA").copy())
        except: pass
        
        is_gif = is_animated_avatar or len(decoration_frames) > 1
        num_frames = max(len(avatar_frames), len(decoration_frames), 1)

        # Scale fonts
        if len(content) < 30: base_size = 56
        elif len(content) < 80: base_size = 42
        else: base_size = 32
        
        f_main = self.load_font(base_size)
        f_small = self.load_font(int(base_size * 0.85))
        f_name = self.load_font(36)
        f_date = self.load_font(24)
        
        # --- PRE-PROCESS BACKGROUND ---
        if banner_img: 
            base_bg = ImageOps.fit(banner_img.copy(), (WIDTH, HEIGHT), centering=(0.5, 0.5))
        else:
            from PIL import ImageFilter
            base_bg = ImageOps.fit(avatar_frames[0].copy(), (WIDTH, HEIGHT), centering=(0.5, 0.5))
            base_bg = base_bg.filter(ImageFilter.GaussianBlur(radius=15))
        
        overlay = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
        draw_ov = ImageDraw.Draw(overlay)
        for y in range(HEIGHT):
            alpha = int(140 + (100 * (y / HEIGHT)))
            draw_ov.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
        
        static_bg = Image.alpha_composite(base_bg, overlay)
        
        output_frames = []
        for i in range(num_frames):
            av_f = avatar_frames[i % len(avatar_frames)]
            dec_f = decoration_frames[i % len(decoration_frames)] if decoration_frames else None
            
            bg = static_bg.copy()
            draw = ImageDraw.Draw(bg)
            
            # 1. Draw PFP and Decoration (Centered Top)
            dec_size = 230
            pfp_size = 180 # Smaller than decoration to fit borders
            
            # PFP
            av_c = av_f.copy().resize((pfp_size, pfp_size))
            mask = Image.new("L", (pfp_size, pfp_size), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, pfp_size, pfp_size), fill=255)
            av_c.putalpha(mask)
            
            cx, cy = 450, 130 # Center point of avatar section
            ax, ay = cx - (pfp_size // 2), cy - (pfp_size // 2)
            bg.paste(av_c, (ax, ay), av_c)
            
            # Decoration
            if dec_f:
                dr = dec_f.resize((dec_size, dec_size))
                # Decorations are usually offset to wrap the circular PFP
                # We center it relative to the PFP center
                dx, dy = cx - (dec_size // 2), cy - (dec_size // 2)
                bg.paste(dr, (dx, dy), dr)
            
            # 2. Draw Border Line
            line_y = 265
            draw.line([(250, line_y), (650, line_y)], fill=(255, 255, 255, 100), width=2)
            
            # 3. Draw Attribution (Name & Date, Centered)
            attr_y = line_y + 20
            name_text = message.author.display_name.upper()
            date_text = f"@{message.author.name} · {message.created_at.strftime('%b %d, %Y')}"
            
            name_bbox = draw.textbbox((0, 0), name_text, font=f_name)
            name_x = cx - ((name_bbox[2] - name_bbox[0]) // 2)
            draw.text((name_x, attr_y), name_text, font=f_name, fill=NAME_COLOR)
            
            date_bbox = draw.textbbox((0, 0), date_text, font=f_date)
            date_x = cx - ((date_bbox[2] - date_bbox[0]) // 2)
            draw.text((date_x, attr_y + 40), date_text, font=f_date, fill=DATE_COLOR)
            
            # 4. Draw Quote (Centered below attribution)
            tx, mw = cx, 700
            lines, cur = [], []
            a_f = f_small if len(content) > 100 else f_main
            l_h = int(a_f.size * 1.3)
            
            for word in content.split():
                if draw.textbbox((0, 0), ' '.join(cur + [word]), font=a_f)[2] <= mw: 
                    cur.append(word)
                else: 
                    lines.append(' '.join(cur))
                    cur = [word]
            lines.append(' '.join(cur))
            
            lines = lines[:5] # Limit lines to prevent overflow
            total_txt_h = len(lines) * l_h
            qy = attr_y + 100 # Start quote below date
            
            for line in lines:
                l_bbox = draw.textbbox((0, 0), line, font=a_f)
                lx = tx - ((l_bbox[2] - l_bbox[0]) // 2)
                # Shadow
                draw.text((lx + 2, qy + 2), line, font=a_f, fill=(0, 0, 0, 100))
                # Main
                draw.text((lx, qy), line, font=a_f, fill=TEXT_COLOR)
                qy += l_h
            
            output_frames.append(bg)
        
        buf = io.BytesIO()
        if is_gif and len(output_frames) > 1:
            opts = [f.convert('P', palette=Image.ADAPTIVE, colors=256) for f in output_frames]
            opts[0].save(buf, format='GIF', save_all=True, append_images=opts[1:], duration=100, loop=0, optimize=True, disposal=2)
        else: output_frames[0].save(buf, format='PNG', optimize=True)
        buf.seek(0)
        return buf, is_gif

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        """Handle errors in application commands"""
        if isinstance(error, app_commands.MissingPermissions):
            await interaction.response.send_message("❌ You don't have Administrator permissions to use this command!", ephemeral=True)
        else:
            logger.error(f"Error in quote command: {error}", exc_info=True)
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred while processing this command.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Quote(bot))
