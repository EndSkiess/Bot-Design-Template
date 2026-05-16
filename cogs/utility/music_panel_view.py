"""
Music Panel View - Interactive music control panel with buttons
"""
import discord
from discord import ui
import asyncio
import random
import logging

logger = logging.getLogger('Lilith.MusicPanel')


class AddSongModal(ui.Modal, title="Add Song to Queue"):
    """Modal for adding songs to the queue"""

    song_input = ui.TextInput(
        label="Song Name or URL",
        placeholder="Enter a song name or paste a YouTube/Spotify link...",
        required=True,
        max_length=500,
        style=discord.TextStyle.paragraph,
    )

    def __init__(self, music_cog, guild, panel_message, panel_view):
        super().__init__()
        self.music_cog = music_cog
        self.guild = guild
        self.panel_message = panel_message
        self.panel_view = panel_view

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        query = self.song_input.value.strip()
        if not query:
            await interaction.followup.send("❌ Please enter a song name or URL!", ephemeral=True)
            return

        queue = self.music_cog.get_queue(self.guild.id)

        if 'spotify.com' in query:
            if not self.music_cog.spotify:
                await interaction.followup.send("❌ Spotify integration not configured!", ephemeral=True)
                return
            tracks = await self.music_cog.get_spotify_tracks(query)
            if not tracks:
                await interaction.followup.send("❌ Failed to extract Spotify tracks!", ephemeral=True)
                return
            for track_name in tracks:
                queue.add({'url': f"ytsearch:{track_name}", 'title': track_name, 'requester': interaction.user})
            await interaction.followup.send(f"✅ Added **{len(tracks)}** tracks to queue!", ephemeral=True)

        else:
            if not query.startswith('http'):
                query = f"ytsearch:{query}"
            try:
                # Re-use the shared ytdl instance + retry wrapper from music.py
                from .music import extract_info_with_retry
                info = await extract_info_with_retry(interaction.client.loop, query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                queue.add({'url': info['webpage_url'], 'title': info['title'], 'requester': interaction.user})
                await interaction.followup.send(f"✅ Added to queue: **{info['title']}**", ephemeral=True)
            except Exception as e:
                err = str(e)
                msg = f"❌ Error: {err}"
                if any(k in err.lower() for k in ('sign in', 'bot', '403', '429', 'rate')):
                    msg = (
                        "❌ YouTube is rate-limiting the bot. "
                        "Add a `cookies.txt` to the bot root, or try again later."
                    )
                await interaction.followup.send(msg, ephemeral=True)
                return

        # Start playing if idle
        if not self.guild.voice_client or not self.guild.voice_client.is_playing():
            class FakeContext:
                def __init__(self, guild, channel):
                    self.guild = guild
                    self.voice_client = guild.voice_client
                    self.send = channel.send

            if self.guild.voice_client:
                await self.music_cog.play_next(FakeContext(self.guild, interaction.channel))


class MusicControlPanel(ui.View):
    """Interactive music control panel with buttons"""

    def __init__(self, bot, ctx, panel_message=None, timeout=None):
        super().__init__(timeout=timeout)
        self.bot = bot
        self.ctx = ctx
        self.music_cog = bot.get_cog('Music')
        self.loop_mode = False
        self.panel_message = panel_message

    async def on_error(self, interaction: discord.Interaction, error: Exception, item: ui.Item):
        logger.error(f"Error in music panel interaction: {error}", exc_info=True)
        try:
            if not interaction.response.is_done():
                await interaction.response.send_message("❌ An error occurred.", ephemeral=True)
            else:
                await interaction.followup.send("❌ An error occurred.", ephemeral=True)
        except Exception:
            pass

    def get_current_info(self):
        if not self.music_cog:
            return None
        return self.music_cog.get_queue(self.ctx.guild.id).current

    async def check_voice(self, interaction: discord.Interaction) -> bool:
        if not interaction.user.voice or not interaction.guild.voice_client:
            await interaction.response.send_message(
                "❌ You (or the bot) must be in a voice channel!", ephemeral=True
            )
            return False
        if interaction.user.voice.channel != interaction.guild.voice_client.channel:
            await interaction.response.send_message(
                f"❌ You must be in {interaction.guild.voice_client.channel.mention} to use this!",
                ephemeral=True,
            )
            return False
        return True

    def create_embed(self):
        current = self.get_current_info()
        embed = discord.Embed(title="🎵 MUSIC PANEL", color=0x2b2d31)

        if current:
            title = current.get('title', 'Unknown')
            requester = current.get('requester')

            embed.add_field(name="🎵 Now Playing", value=f"**{title}**", inline=False)
            embed.add_field(
                name="👤 Requested By",
                value=requester.mention if requester else "Unknown",
                inline=True,
            )

            vc = self.ctx.guild.voice_client
            if vc and hasattr(vc, 'source') and vc.source:
                src = vc.source
                if hasattr(src, 'duration') and src.duration:
                    mins, secs = divmod(int(src.duration), 60)
                    embed.add_field(name="⏱️ Duration", value=f"{mins}m {secs}s", inline=True)

                author = "Unknown"
                if hasattr(src, 'data'):
                    data = src.data
                    author = data.get('uploader') or data.get('channel') or data.get('artist') or "Unknown"
                embed.add_field(name="🎤 Author", value=author, inline=True)
        else:
            embed.description = "No music currently playing"

        status = []
        if self.loop_mode:
            status.append("🔁 Loop: ON")
        if self.music_cog and self.music_cog.autoplay_enabled.get(self.ctx.guild.id, False):
            status.append("🎲 AutoPlay: ON")
        if status:
            embed.set_footer(text=" | ".join(status))

        return embed

    # ── Row 0 – Playback controls ──────────────────────────────────────────

    @ui.button(label="Down", style=discord.ButtonStyle.secondary, emoji="🔉", row=0)
    async def volume_down(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        vc = interaction.guild.voice_client
        if not vc.source:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
            return
        new_vol = max(0.0, vc.source.volume - 0.1)
        vc.source.volume = new_vol
        await interaction.response.send_message(f"🔉 Volume: {int(new_vol * 100)}%", ephemeral=True)

    @ui.button(label="Back", style=discord.ButtonStyle.secondary, emoji="⏮️", row=0)
    async def previous(self, interaction: discord.Interaction, button: ui.Button):
        await interaction.response.send_message("⏮️ Previous track – coming soon!", ephemeral=True)

    @ui.button(label="Pause", style=discord.ButtonStyle.primary, emoji="⏸️", row=0)
    async def pause_resume(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        vc = interaction.guild.voice_client
        if vc.is_playing():
            vc.pause()
            button.label = "Resume"
            button.emoji = "▶️"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("⏸️ Paused", ephemeral=True)
        elif vc.is_paused():
            vc.resume()
            button.label = "Pause"
            button.emoji = "⏸️"
            await interaction.response.edit_message(view=self)
            await interaction.followup.send("▶️ Resumed", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)

    @ui.button(label="Skip", style=discord.ButtonStyle.secondary, emoji="⏭️", row=0)
    async def skip(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        if not interaction.guild.voice_client.is_playing():
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
            return
        interaction.guild.voice_client.stop()
        await interaction.response.send_message("⏭️ Skipped!", ephemeral=True)
        await asyncio.sleep(0.5)
        try:
            await interaction.message.edit(embed=self.create_embed())
        except Exception:
            pass

    @ui.button(label="Up", style=discord.ButtonStyle.secondary, emoji="🔊", row=0)
    async def volume_up(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        vc = interaction.guild.voice_client
        if not vc.source:
            await interaction.response.send_message("❌ Nothing is playing!", ephemeral=True)
            return
        new_vol = min(2.0, vc.source.volume + 0.1)
        vc.source.volume = new_vol
        await interaction.response.send_message(f"🔊 Volume: {int(new_vol * 100)}%", ephemeral=True)

    # ── Row 1 – Extra controls ─────────────────────────────────────────────

    @ui.button(label="Shuffle", style=discord.ButtonStyle.secondary, emoji="🔀", row=1)
    async def shuffle(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        if not self.music_cog:
            await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
            return
        queue = self.music_cog.get_queue(interaction.guild.id)
        if queue.is_empty():
            await interaction.response.send_message("❌ Queue is empty!", ephemeral=True)
            return
        random.shuffle(queue.queue)
        await interaction.response.send_message("🔀 Queue shuffled!", ephemeral=True)

    @ui.button(label="Loop", style=discord.ButtonStyle.secondary, emoji="🔁", row=1)
    async def loop(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        self.loop_mode = not self.loop_mode
        button.style = discord.ButtonStyle.success if self.loop_mode else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        state = "enabled" if self.loop_mode else "disabled"
        await interaction.followup.send(f"🔁 Loop {state}!", ephemeral=True)

    @ui.button(label="Stop", style=discord.ButtonStyle.danger, emoji="⏹️", row=1)
    async def stop(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        if not self.music_cog:
            await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
            return
        self.music_cog.get_queue(interaction.guild.id).clear()
        if interaction.guild.voice_client:
            await interaction.guild.voice_client.disconnect()
        await interaction.response.send_message("⏹️ Stopped and disconnected!", ephemeral=True)
        for item in self.children:
            item.disabled = True
        await interaction.message.edit(view=self)

    @ui.button(label="AutoPlay", style=discord.ButtonStyle.secondary, emoji="🎲", row=1)
    async def autoplay(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        if not self.music_cog:
            await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
            return
        if not self.music_cog.spotify:
            await interaction.response.send_message(
                "❌ AutoPlay requires Spotify – add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env",
                ephemeral=True,
            )
            return
        current = not self.music_cog.autoplay_enabled.get(interaction.guild.id, False)
        self.music_cog.set_autoplay(interaction.guild.id, current)
        button.style = discord.ButtonStyle.success if current else discord.ButtonStyle.secondary
        await interaction.response.edit_message(embed=self.create_embed(), view=self)
        state = "enabled" if current else "disabled"
        await interaction.followup.send(f"🎲 AutoPlay {state}!", ephemeral=True)

    @ui.button(label="Playlist", style=discord.ButtonStyle.secondary, emoji="📜", row=1)
    async def playlist(self, interaction: discord.Interaction, button: ui.Button):
        if not self.music_cog:
            await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
            return
        queue = self.music_cog.get_queue(interaction.guild.id)
        if queue.current is None and queue.is_empty():
            await interaction.response.send_message("📭 Queue is empty!", ephemeral=True)
            return

        embed = discord.Embed(title="📜 Current Playlist", color=discord.Color.blue())
        if queue.current:
            embed.add_field(name="🎵 Now Playing", value=f"**{queue.current['title']}**", inline=False)
        if not queue.is_empty():
            upcoming = "\n".join(f"{i+1}. {t['title']}" for i, t in enumerate(queue.queue[:10]))
            if len(queue.queue) > 10:
                upcoming += f"\n… and {len(queue.queue) - 10} more"
            embed.add_field(name=f"⏭️ Up Next ({len(queue.queue)} songs)", value=upcoming, inline=False)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    # ── Row 2 – Add Song ───────────────────────────────────────────────────

    @ui.button(label="Add Song", style=discord.ButtonStyle.success, emoji="➕", row=2)
    async def add_song(self, interaction: discord.Interaction, button: ui.Button):
        if not await self.check_voice(interaction):
            return
        if not self.music_cog:
            await interaction.response.send_message("❌ Music system not available!", ephemeral=True)
            return
        await interaction.response.send_modal(
            AddSongModal(self.music_cog, interaction.guild, self.panel_message, self)
        )
