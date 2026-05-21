import discord
from discord.ext import commands
import wavelink
import asyncio

from backend.utils.formatters import format_duration

class NowPlaying(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._music_cog = None
        print("[NOW_PLAYING_COG] Cog is initializing...")

    @commands.Cog.listener()
    async def on_ready(self):
        """Tunggu bot siap, lalu ambil referensi ke Music cog."""
        # Memberi sedikit jeda untuk memastikan semua cog lain telah dimuat sepenuhnya
        await asyncio.sleep(2) 
        self._music_cog = self.bot.get_cog('Music')
        if self._music_cog:
            print("[NOW_PLAYING_COG] Successfully linked with Music Cog.")
        else:
            print("[NOW_PLAYING_COG] CRITICAL: Music Cog not found after startup!")

    def get_player_state(self, guild_id: int) -> dict | None:
        """
        Fungsi utama yang akan dipanggil oleh web server.
        Mengembalikan state lengkap dari music player untuk sebuah guild.
        """
        if not self._music_cog:
            print("[NOW_PLAYING_COG] Music cog not ready yet.")
            return {"error": "Music cog not initialized"}

        # Dapatkan player dari Wavelink.
        # Wavelink mengelola player sebagai voice client di guild.
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return {"connected": False, "error": "Guild not found"}
            
        player: wavelink.Player = guild.voice_client
        if not player or not player.is_connected():
            return {"connected": False}

        # Dapatkan custom player state (loop, autoplay) dari Music Cog
        music_player = self._music_cog.get_player(guild_id)
        
        # Siapkan data untuk track yang sedang diputar
        current_track_data = None
        if player.current:
            track = player.current
            current_track_data = {
                "title": track.title,
                "author": track.author,
                "uri": track.uri,
                # Gunakan placeholder jika artwork tidak tersedia
                "artwork": track.artwork or "/static/img/default-artwork.png",
                "duration_ms": track.length,
                "duration_fmt": format_duration(track.length),
            }

        # Siapkan data untuk antrian (misal, 15 lagu berikutnya)
        queue_data = []
        for i, track in enumerate(list(player.queue)[:15]):
            queue_data.append({
                "position": i + 1,
                "title": track.title,
                "author": track.author,
                "duration_fmt": format_duration(track.length),
            })
            
        # Gabungkan semua data menjadi satu dictionary yang akan di-serialize ke JSON
        state = {
            "connected": True,
            "playing": player.is_playing(),
            "paused": player.is_paused(),
            "volume": player.volume,
            "position_ms": player.position,
            "position_fmt": format_duration(player.position),
            "loop_mode": music_player.loop_mode,
            "autoplay": music_player.autoplay,
            "current_track": current_track_data,
            "queue": queue_data,
            "queue_count": len(player.queue),
        }
        return state

async def setup(bot: commands.Bot):
    # Pastikan cog ini dimuat setelah Music cog, atau tangani dependensinya
    await bot.add_cog(NowPlaying(bot))
