import discord
from discord.ext import commands
import datetime
import asyncio
from ...utils.spam_engine import SpamEngine
from ..database.firebase_setup import db

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.engine = SpamEngine()
        # 🌟 GANTI ID INI DENGAN ID CHANNEL #report-spam LU
        self.report_channel_id = 1517948052537868449 

    @commands.Cog.listener()
    async def on_message(self, message):
        # Abaikan bot & admin
        if message.author.bot or message.author.guild_permissions.administrator:
            await self.bot.process_commands(message)
            return

        # 1. Filter Heuristic
        if self.engine.is_spam_heuristic(message):
            await self.handle_spam(message, "Filter Dasar: Terdeteksi kata kunci/link mencurigakan")
            return

        # 2. Filter Akun Baru
        if self.engine.is_new_account(message) and len(message.content) > 30:
            await self.handle_spam(message, "Filter Keamanan: Akun baru mengirim pesan panjang")
            return

        # 3. Filter AI
        current_score = self.engine.get_risk_score(message)
        if 0 < current_score < 5 and len(message.content) > 10:
            ai_cog = self.bot.get_cog('AIChat')
            if ai_cog:
                is_ai_spam = await ai_cog.analyze_spam(message.content)
                if is_ai_spam:
                    await self.handle_spam(message, "Filter AI: Terdeteksi konten mencurigakan oleh LLM")
                    return

        await self.bot.process_commands(message)

    async def handle_spam(self, message, reason):
        try:
            # 1. Hapus pesan spam
            await message.delete()

            # 2. Update data strike di Firestore
            user_id = str(message.author.id)
            doc_ref = db.collection("strikes").document(user_id)
            doc = await asyncio.to_thread(doc_ref.get)
            strikes = doc.to_dict().get("count", 0) if doc.exists else 0
            
            strikes += 1
            await asyncio.to_thread(doc_ref.set, {"count": strikes})

            # 3. Logika Eskalasi Hukuman
            punishment_msg = ""
            if strikes >= 3:
                await message.author.ban(reason=f"Auto-Ban: {reason}")
                punishment_msg = "BAN permanen"
            elif strikes == 2:
                await message.author.kick(reason=f"Auto-Kick: {reason}")
                punishment_msg = "KICK"
            else:
                duration = datetime.timedelta(hours=1)
                await message.author.timeout(duration, reason=f"Spam: {reason}")
                punishment_msg = "TIMEOUT 1 jam"

            # 4. Kirim Laporan Terpusat ke #report-spam (TIDAK ADA PESAN KE CHANNEL UMUM)
            report_channel = self.bot.get_channel(self.report_channel_id)
            if report_channel:
                embed = discord.Embed(
                    title="🚫 Laporan Spam",
                    color=discord.Color.red(),
                    description=f"User **{message.author.name}** ({message.author.id}) dihukum: **{punishment_msg}**"
                )
                embed.add_field(name="Alasan", value=reason, inline=False)
                embed.add_field(name="Channel", value=message.channel.mention, inline=True)
                embed.add_field(name="Peringatan Ke", value=strikes, inline=True)
                embed.add_field(name="Isi Pesan", value=f"||{message.content[:500]}||", inline=False)
                
                await report_channel.send(embed=embed)

            # 5. Kirim DM ke User
            try:
                await message.author.send(f"⚠️ **Peringatan!** Kamu telah di-{punishment_msg} dari server {message.guild.name} karena melakukan spam. Ini adalah peringatan ke-{strikes}.")
            except discord.Forbidden:
                print(f"[MODERATION] Gagal kirim DM ke {message.author}, DM ditutup.")

            print(f"[MODERATION] {message.author} Strike {strikes}: {reason}")
        
        except Exception as e:
            print(f"[ERROR] Gagal moderasi: {e}")

async def setup(bot):
    await bot.add_cog(Moderation(bot))
