"""
Music bot commands - play, pause, unpause, skip, stop
Supports YouTube URLs, search queries, and Spotify playlists
"""
import discord
from discord.ext import commands
from discord import app_commands
try:
    import yt_dlp
    HAS_YTDL = True
except ImportError:
    HAS_YTDL = False

import logging
import asyncio
import os
import shutil
import site
import sys
from dotenv import load_dotenv

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    HAS_SPOTIPY = True
except ImportError:
    HAS_SPOTIPY = False
from .music_panel_view import MusicControlPanel

load_dotenv()

logger = logging.getLogger('Lilith.Music')

# ---------------------------------------------------------------------------
# Cookies helper
# ---------------------------------------------------------------------------
COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'cookies.txt')
COOKIES_FILE = os.path.normpath(COOKIES_FILE)

def _cookies_opts() -> dict:
    """Return cookiefile option only when the file actually exists."""
    if os.path.isfile(COOKIES_FILE):
        logger.info(f"Using cookies file: {COOKIES_FILE}")
        return {'cookiefile': COOKIES_FILE}
    return {}

# ---------------------------------------------------------------------------
# Cookies helper
# ---------------------------------------------------------------------------
import os
COOKIES_FILE = os.path.join(os.path.dirname(__file__), '..', '..', 'cookies.txt')
COOKIES_FILE = os.path.normpath(COOKIES_FILE)

def _cookies_opts() -> dict:
    """Return cookiefile option only when the file actually exists."""
    if os.path.isfile(COOKIES_FILE):
        return {'cookiefile': COOKIES_FILE}
    return {}

# ---------------------------------------------------------------------------
# yt-dlp options (Primary Strategy: Cookies + TV Client)
# ---------------------------------------------------------------------------
_extractor_args_youtube = {
    'player_client': ['tv', 'android', 'ios', 'mweb', 'web'],
}

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioquality': 0,
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'default_search': 'ytsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': _extractor_args_youtube,
        'youtubetab': {
            'skip': ['authcheck'],
        },
    },
    'retries': 3,
    'fragment_retries': 3,
    'skip_unavailable_fragments': True,
    **_cookies_opts(),
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn -b:a 192k -ar 48000'
}

# ---------------------------------------------------------------------------
# FFmpeg path resolution (works on Render and local Windows dev)
# ---------------------------------------------------------------------------
def _find_ffmpeg() -> str:
    if shutil.which('ffmpeg'):
        return 'ffmpeg'
    candidates = [
        r"C:\Users\Samuel\AppData\Local\Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.0-full_build\bin\ffmpeg.exe",
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return 'ffmpeg'  # last resort – will fail with a clear error

FFMPEG_EXECUTABLE = _find_ffmpeg()

if HAS_YTDL:
    ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)
else:
    ytdl = No
# ---------------------------------------------------------------------------
# Invidious instances – used for stream URL extraction only
# ---------------------------------------------------------------------------
import random as _random
import re as _re

# ---------------------------------------------------------------------------
# SoundCloud Fallback Helper
# ---------------------------------------------------------------------------
import urllib.request as _urllib_request
import json as _json

def _extract_yt_id(query: str) -> str | None:
    """Extract a YouTube video ID from a URL. Returns None for search queries."""
    match = _re.search(r'(?:v=|youtu\.be/|/v/|/embed/)([a-zA-Z0-9_-]{11})', query)
    return match.group(1) if match else None

def _get_yt_title_oembed(video_id: str) -> str | None:
    """Uses YouTube's official unblocked oEmbed API to reliably fetch a video title."""
    try:
        url = f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        req = _urllib_request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with _urllib_request.urlopen(req, timeout=5) as resp:
            data = _json.loads(resp.read())
            return data.get('title')
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Extraction – Hybrid Strategy
#   Stage 1: Primary YouTube extraction (Cookies + TV client spoofing)
#   Stage 2: Invidious proxy fallback
# ---------------------------------------------------------------------------
async def extract_info_with_retry(loop, query: str, *, download=False, retries: int = 3):
    import datetime

    def _log_error(label: str, exc: Exception):
        try:
            with open('ytdl_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"\n--- {label} at {datetime.datetime.now()} ---\n")
                f.write(f"Query: {query}\n")
                f.write(f"Error: {exc}\n")
        except OSError:
            pass

    def _is_bot_blocked(err: str) -> bool:
        return any(k in err for k in (
            '429', 'sign in to confirm', 'bot', 'http error 403',
            'cookies are no longer valid', 'rotated in the browser'
        ))

    # ── Stage 1: Native YouTube (Cookies + Spoofing) ──────────────────────
    logger.info(f"[Music] Attempting native extraction for: {query}")
    stage1_exc = None
    for attempt in range(1, retries + 1):
        try:
            opts = YTDL_OPTIONS.copy()
            opts['verbose'] = True
            with yt_dlp.YoutubeDL(opts) as ydl:
                return await loop.run_in_executor(
                    None, lambda q=query: ydl.extract_info(q, download=download)
                )
        except Exception as exc:
            stage1_exc = exc
            _log_error(f'Native/Attempt{attempt}', exc)
            err = str(exc).lower()
            if _is_bot_blocked(err):
                wait = 1.5 * attempt
                logger.warning(f"[yt-dlp] Stage 1 attempt {attempt} blocked. Retrying in {wait}s…")
                await asyncio.sleep(wait)
            else:
                break # Hard failure, fallback to Stage 2

    # ── Stage 2: SoundCloud Fallback ──────────────────────────────────────
    logger.warning("[Music] Native YouTube extraction blocked. Initiating SoundCloud fallback…")
    
    video_title = None
    video_id = _extract_yt_id(query)
    
    if video_id:
        logger.info(f"[SoundCloud] Resolving title for blocked YouTube ID: {video_id} via oEmbed API")
        video_title = await loop.run_in_executor(None, _get_yt_title_oembed, video_id)
        if not video_title:
            raise RuntimeError(
                f"❌ Stage 1 failed & SoundCloud fallback could not resolve the video title.\n"
                f"Original Error: {stage1_exc}"
            )
    else:
        # It's a raw search query
        video_title = query.replace('ytsearch:', '').replace('ytsearch1:', '').strip()

    logger.info(f"[SoundCloud] Searching for: '{video_title}'")
    try:
        sc_opts = YTDL_OPTIONS.copy()
        sc_opts.pop('cookiefile', None)
        sc_opts.pop('extractor_args', None)
        sc_opts['default_search'] = 'scsearch'
        
        with yt_dlp.YoutubeDL(sc_opts) as ydl:
            # specifically force scsearch1 to only fetch the top result
            result = await loop.run_in_executor(
                None, lambda: ydl.extract_info(f"scsearch1:{video_title}", download=download)
            )
            logger.info("[SoundCloud] ✅ Fallback extraction succeeded!")
            return result
    except Exception as exc:
        _log_error('SoundCloudFallback', exc)
        raise RuntimeError(
            f"❌ Soundcloud fallback failed for '{video_title}'.\n"
            f"Original YouTube error was: {stage1_exc}\n"
            f"SoundCloud error: {exc}"
        )



class YTDLSource(discord.PCMVolumeTransformer):
    """Audio source for YouTube"""
    def __init__(self, source, *, data, volume=1.0):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')
        self.duration = data.get('duration')
        self.thumbnail = data.get('thumbnail')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        """Create audio source from URL with retry logic."""
        if not HAS_YTDL:
            raise RuntimeError("yt-dlp is not installed. Music features are disabled.")
        loop = loop or asyncio.get_event_loop()

        data = await extract_info_with_retry(loop, url, download=not stream)

        if 'entries' in data:
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(
            discord.FFmpegPCMAudio(filename, executable=FFMPEG_EXECUTABLE, **FFMPEG_OPTIONS),
            data=data,
        )


class MusicQueue:
    """Queue system for music tracks"""
    def __init__(self):
        self.queue = []
        self.current = None

    def add(self, track):
        self.queue.append(track)

    def next(self):
        if self.queue:
            self.current = self.queue.pop(0)
            return self.current
        self.current = None
        return None

    def clear(self):
        self.queue.clear()
        self.current = None

    def is_empty(self):
        return len(self.queue) == 0


class Music(commands.Cog):
    """Music playback commands"""

    def __init__(self, bot):
        self.bot = bot
        self.queues = {}
        self.panel_messages = {}
        self.autoplay_enabled = {}

        spotify_id = os.getenv('SPOTIFY_CLIENT_ID')
        spotify_secret = os.getenv('SPOTIFY_CLIENT_SECRET')

        if HAS_SPOTIPY and spotify_id and spotify_secret:
            try:
                self.spotify = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=spotify_id,
                    client_secret=spotify_secret
                ))
            except Exception as e:
                logger.error(f"Failed to initialize Spotify: {e}")
                self.spotify = None
        else:
            self.spotify = None

    def get_queue(self, guild_id):
        if guild_id not in self.queues:
            self.queues[guild_id] = MusicQueue()
        return self.queues[guild_id]

    async def play_next(self, ctx):
        """Play next song in queue"""
        queue = self.get_queue(ctx.guild.id)

        if queue.is_empty():
            if self.autoplay_enabled.get(ctx.guild.id, False):
                if queue.current and queue.current.get('title'):
                    logger.info("AutoPlay: Queue empty, getting recommendations…")
                    recommendations = await self.get_spotify_recommendations(queue.current['title'])
                    if recommendations:
                        for track_name in recommendations:
                            queue.add({
                                'url': f"ytsearch:{track_name}",
                                'title': track_name,
                                'requester': queue.current.get('requester'),
                            })
                        logger.info(f"AutoPlay: Added {len(recommendations)} recommendations")
                    else:
                        logger.warning("AutoPlay: No recommendations, waiting to disconnect…")
                        await asyncio.sleep(300)
                        if ctx.voice_client and not ctx.voice_client.is_playing():
                            await ctx.voice_client.disconnect()
                        return
                else:
                    await asyncio.sleep(300)
                    if ctx.voice_client and not ctx.voice_client.is_playing():
                        await ctx.voice_client.disconnect()
                    return
            else:
                await asyncio.sleep(300)
                if ctx.voice_client and not ctx.voice_client.is_playing():
                    await ctx.voice_client.disconnect()
                return

        track_info = queue.next()

        try:
            player = await YTDLSource.from_url(track_info['url'], loop=self.bot.loop, stream=True)
            ctx.voice_client.play(
                player,
                after=lambda e: asyncio.run_coroutine_threadsafe(
                    self.play_next(ctx), self.bot.loop
                ),
            )

            if ctx.guild.id in self.panel_messages:
                panel_msg, panel_view = self.panel_messages[ctx.guild.id]
                try:
                    await panel_msg.edit(embed=panel_view.create_embed(), view=panel_view)
                except discord.errors.NotFound:
                    del self.panel_messages[ctx.guild.id]
                except discord.errors.HTTPException as e:
                    if e.code in (50027,) or e.status == 401:
                        del self.panel_messages[ctx.guild.id]
                    else:
                        logger.error(f"Failed to update panel: {e}")
                except Exception as e:
                    logger.error(f"Failed to update panel: {e}")

        except Exception as e:
            logger.error(f"Error playing track '{track_info.get('title')}': {e}")
            await ctx.send(f"❌ Error playing track: {str(e)}")
            await self.play_next(ctx)

    async def get_spotify_tracks(self, url):
        try:
            if HAS_SPOTIPY and self.spotify:
                if 'playlist' in url:
                    results = self.spotify.playlist_tracks(url)
                    tracks = []
                    for item in results['items']:
                        track = item['track']
                        tracks.append(f"{track['artists'][0]['name']} - {track['name']}")
                    return tracks
                elif 'track' in url:
                    track = self.spotify.track(url)
                    return [f"{track['artists'][0]['name']} - {track['name']}"]
        except Exception as e:
            if 'premium subscription required' in str(e).lower() or '403' in str(e):
                logger.warning(f"Spotify account restriction detected (Premium required), falling back to web scraper...")
            else:
                logger.warning(f"Spotify API failed ({e}), falling back to web scraper...")

        # Fallback to web scraping the <title> tag if the API 403s or isn't configured
        try:
            import aiohttp
            import re
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers={'User-Agent': 'Mozilla/5.0'}) as resp:
                    if resp.status == 200:
                        html = await resp.text()
                        match = re.search(r'<title>(.*?)</title>', html)
                        if match:
                            title = match.group(1).split('|')[0]
                            title = title.replace('- song and lyrics by', '')
                            title = title.replace('- song by', '')
                            return [title.strip()]
        except Exception as fallback_err:
            logger.error(f"Spotify fallback scraper failed: {fallback_err}")

        return None

    async def get_spotify_recommendations(self, track_title):
        if not self.spotify:
            return None
        try:
            search = self.spotify.search(q=track_title, type='track', limit=1)
            if not search['tracks']['items']:
                simplified = track_title.split('-')[0].strip() if '-' in track_title else track_title
                search = self.spotify.search(q=simplified, type='track', limit=1)
                if not search['tracks']['items']:
                    return None

            track = search['tracks']['items'][0]
            artist_id = track['artists'][0]['id']
            artist_name = track['artists'][0]['name']
            logger.info(f"AutoPlay: Using artist '{artist_name}' for recommendations")

            top_tracks = self.spotify.artist_top_tracks(artist_id, country='US')
            if not top_tracks or 'tracks' not in top_tracks:
                return None

            recommended = [
                f"{t['artists'][0]['name']} - {t['name']}"
                for t in top_tracks['tracks'][:10]
            ]

            if len(recommended) < 5:
                try:
                    related = self.spotify.artist_related_artists(artist_id)
                    for ra in (related or {}).get('artists', [])[:3]:
                        for t in self.spotify.artist_top_tracks(ra['id'], country='US')['tracks'][:3]:
                            name = f"{t['artists'][0]['name']} - {t['name']}"
                            if name not in recommended:
                                recommended.append(name)
                        if len(recommended) >= 10:
                            break
                except Exception:
                    pass

            return recommended or None
        except Exception as e:
            if 'premium subscription required' not in str(e).lower():
                logger.error(f"Error getting recommendations: {e}")
            return None

    def set_autoplay(self, guild_id, enabled):
        self.autoplay_enabled[guild_id] = enabled
        logger.info(f"AutoPlay {'enabled' if enabled else 'disabled'} for guild {guild_id}")

    @app_commands.command(name="musiclogs", description="Get the latest music diagnostic logs (Owner only)")
    async def musiclogs(self, interaction: discord.Interaction):
        """Upload the ytdl_debug.log file to Discord"""
        if not os.path.exists('ytdl_debug.log'):
            await interaction.response.send_message("❌ No log file found yet. Try playing a song first!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)
        try:
            file = discord.File('ytdl_debug.log')
            await interaction.followup.send("📑 Here are the latest music diagnostic logs:", file=file, ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Failed to send logs: {e}", ephemeral=True)

    @app_commands.command(name="music", description="Play music from YouTube or Spotify")
    @app_commands.describe(query="YouTube URL, search query, or Spotify link")
    async def music(self, interaction: discord.Interaction, query: str):
        """Play music and show control panel"""
        try:
            await interaction.response.defer()
        except (discord.errors.NotFound, discord.errors.HTTPException):
            return

        if not HAS_YTDL:
            await interaction.followup.send(
                "❌ Music features are disabled – `yt-dlp` is not installed.", ephemeral=True
            )
            return

        if not interaction.user.voice:
            await interaction.followup.send("❌ You need to be in a voice channel!", ephemeral=True)
            return

        if not interaction.guild.voice_client:
            try:
                await interaction.user.voice.channel.connect()
            except Exception as e:
                await interaction.followup.send(f"❌ Failed to join voice channel: {e}", ephemeral=True)
                return
        elif interaction.user.voice.channel != interaction.guild.voice_client.channel:
            await interaction.followup.send(
                f"❌ You must be in {interaction.guild.voice_client.channel.mention}!", ephemeral=True
            )
            return

        queue = self.get_queue(interaction.guild.id)

        if 'spotify.com' in query:
            if not self.spotify:
                await interaction.followup.send(
                    "❌ Spotify not configured! Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to .env",
                    ephemeral=True,
                )
                return
            tracks = await self.get_spotify_tracks(query)
            if not tracks:
                await interaction.followup.send("❌ Failed to extract Spotify tracks!", ephemeral=True)
                return
            for track_name in tracks:
                queue.add({'url': f"ytsearch:{track_name}", 'title': track_name, 'requester': interaction.user})
        else:
            if not query.startswith('http'):
                query = f"ytsearch:{query}"
            try:
                info = await extract_info_with_retry(self.bot.loop, query, download=False)
                if 'entries' in info:
                    info = info['entries'][0]
                queue.add({'url': info['webpage_url'], 'title': info['title'], 'requester': interaction.user})
            except Exception as e:
                err = str(e)
                msg = "❌ An error occurred while adding that track."
                if any(k in err.lower() for k in ('sign in', 'bot', '403', '429', 'rate')):
                    msg = (
                        "❌ YouTube is rate-limiting the bot. "
                        "Add a `cookies.txt` to the bot root, or wait a few minutes and try again."
                    )
                await interaction.followup.send(msg, ephemeral=True)
                return

        class FakeContext:
            def __init__(self, interaction):
                self.guild = interaction.guild
                self.voice_client = interaction.guild.voice_client
                self.send = interaction.channel.send

        fake_ctx = FakeContext(interaction)

        if not interaction.guild.voice_client.is_playing():
            await self.play_next(fake_ctx)

        if interaction.guild.id in self.panel_messages:
            panel_msg, panel_view = self.panel_messages[interaction.guild.id]
            try:
                await panel_msg.edit(embed=panel_view.create_embed(), view=panel_view)
                await interaction.followup.send("✅ Song added to queue!", ephemeral=True)
                return
            except Exception:
                pass  # Panel gone – fall through to create a new one

        view = MusicControlPanel(self.bot, fake_ctx, timeout=None)
        embed = view.create_embed()
        panel_msg = await interaction.followup.send(embed=embed, view=view)
        view.panel_message = panel_msg
        self.panel_messages[interaction.guild.id] = (panel_msg, view)

    async def cog_app_command_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.CommandOnCooldown):
            msg = f"⏳ Cooldown – retry in {error.retry_after:.2f}s."
        elif isinstance(error, app_commands.MissingPermissions):
            msg = "❌ You don't have permission to use this command."
        else:
            logger.error(f"Error in music command: {error}", exc_info=True)
            err_str = str(error)
            if any(k in err_str.lower() for k in ('sign in', 'bot', '403', '429')):
                msg = "❌ YouTube is blocking the bot. Upload a valid `cookies.txt` to the bot root."
            else:
                msg = "❌ An error occurred while processing this command."

        try:
            if not interaction.response.is_done():
                await interaction.response.send_message(msg, ephemeral=True)
            else:
                await interaction.followup.send(msg, ephemeral=True)
        except Exception:
            pass


async def setup(bot):
    await bot.add_cog(Music(bot))
