import discord
from discord.ext import commands
import datetime
# Import SpamEngine dari folder utils
from ...utils.spam_engine import SpamEngine 

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Inisialisasi engine di sini
        self.engine = SpamEngine()

    @commands.Cog.listener()
    async def on_message(self, message):
        # Abaikan bot & admin agar tidak terkena ban sendiri
        if message.author.bot or message.author.guild_permissions.administrator:
            return

        # 1. Filter Heuristic (Cepat & Lokal)
        # Menggantikan list manual, sekarang menggunakan logic dari SpamEngine
        if self.engine.is_spam_heuristic(message):
            await self.handle_spam(message, "Filter Dasar: Terdeteksi kata kunci atau link mencurigakan")
            return

        # 2. Filter Akun Baru (Opsional - Sangat efektif cegah spammer baru)
        if self.engine.is_new_account(message) and len(message.content) > 30:
            await self.handle_spam(message, "Filter Keamanan: Akun baru mengirim pesan panjang")
            return

        # 3. Filter AI (Lapis Terakhir)
        # Hanya dijalankan jika lolos filter lokal (menghemat biaya API)
        if len(message.content) > 10:
            ai_cog = self.bot.get_cog('AIChat')
            if ai_cog:
                is_ai_spam = await ai_cog.analyze_spam(message.content)
                if is_ai_spam:
                    await self.handle_spam(message, "Filter AI: Terdeteksi konten mencurigakan oleh LLM")

    async def handle_spam(self, message, reason):
        try:
            # Hapus pesan
            await message.delete()
            
            # Timeout 1 jam
            duration = datetime.timedelta(hours=1)
            await message.author.timeout(duration, reason=f"Spam: {reason}")
            
            print(f"[MODERATION] {message.author} terkena moderasi: {reason}")
        except Exception as e:
            print(f"[ERROR] Gagal moderasi: {e}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
