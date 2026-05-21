"""
================================================================================
COG: AI Chat Module v4.3 — Hidden Hamlet Discord Bot
================================================================================
File        : backend/cogs/ai_chat.py
Deskripsi   : Integrasi Google Gemini AI via REST API (aiohttp).
              • Tidak pakai google-generativeai package (deprecated)
              • Slash command pakai @app_commands.command()
              • Mention handler (@bot)
              • Channel restriction (bisa pilih channel via dashboard)
              • Anti-spam cooldown manual (5 detik/user)
              • Rate limit handling (429/ResourceExhausted)
              • Chat history Firestore (max 5 pasang, slice otomatis)
Model       : gemini-2.0-flash (FREE tier via REST API)
API Docs    : https://ai.google.dev/api/generate-content
================================================================================
"""

import os
import asyncio
import traceback
from datetime import datetime, timezone
from typing import List, Dict, Any

import discord
from discord import app_commands
from discord.ext import commands

# ── HTTP Client ──
import aiohttp

# ── Firebase ──
from .firebase_setup import db

# ── Konstanta ──
MAX_HISTORY_PAIRS = 5          # 5 Q&A = 10 pesan total di Firestore
COOLDOWN_SECONDS = 5           # Anti-spam per user
DEFAULT_PERSONALITY = "friendly"

# ── Gemini API Config ──
GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
GEMINI_MODEL = "gemini-2.0-flash"

# ── System Prompt Template ──
SYSTEM_PROMPT_TEMPLATE = """Kamu adalah AI Resmi dari bot Discord "Hidden Hamlet". 
Personality saat ini: {personality}

Gaya bahasa:
• Default: Gaul, keren, santai, pakai Bahasa Indonesia kasual (lu-gue/kamu-aku sesuai konteks).
• Bisa berubah formal jika pertanyaan terdeteksi serius/teknikal.
• WAJIB merespons dalam bahasa yang sama dengan pertanyaan user (multilingual support).

Aturan:
• Jawab singkat, padat, relevan. Maksimal 4 kalimat kecuali diminta panjang.
• Jangan berikan informasi pribadi atau data sensitif.
• Jika ditanya hal terkait server, gunakan [CONTEXT SERVER] di bawah ini sebagai referensi UTAMA.

{server_context}
"""


class AIChat(commands.Cog):
    """
    Cog AI Chat — mengelola interaksi Gemini AI di Discord via REST API.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self._cooldowns: Dict[tuple, float] = {}
        self.api_key = os.getenv("GEMINI_API_KEY", "")

        if not self.api_key:
            print("[AI CHAT] ⚠️ GEMINI_API_KEY tidak ditemukan di environment!")
        else:
            print(f"[AI CHAT] ✅ API Key loaded: ...{self.api_key[-4:]}")

        self.session: aiohttp.ClientSession | None = None
        print(f"[AI CHAT] ✅ Cog loaded. Model: {GEMINI_MODEL} (REST API)")

    async def cog_load(self):
        """Initialize aiohttp session when cog loads."""
        timeout = aiohttp.ClientTimeout(total=30, connect=10)
        self.session = aiohttp.ClientSession(timeout=timeout)
        print("[AI CHAT] ✅ HTTP session initialized")

    async def cog_unload(self):
        """Close aiohttp session when cog unloads."""
        if self.session:
            await self.session.close()
            print("[AI CHAT] ✅ HTTP session closed")

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Ambil AI Chat settings dari Firestore (ASYNC)
    # ═══════════════════════════════════════════════════════════════════════
    async def _get_guild_ai_settings(self, guild_id: str) -> dict:
        try:
            doc_ref = db.collection("guild_settings").document(str(guild_id))
            doc = await asyncio.to_thread(doc_ref.get)
            if not doc.exists:
                return {"enabled": False, "channel_id": ""}
            data = doc.to_dict()
            ai_chat = data.get("ai_chat", {})
            return {
                "enabled": data.get("ai_chat_enabled", False),
                "channel_id": ai_chat.get("channel_id", ""),
                "personality": ai_chat.get("personality", DEFAULT_PERSONALITY),
                "temperature": ai_chat.get("temperature", 0.75),
            }
        except Exception as e:
            print(f"[AI CHAT] ⚠️ Error ambil settings: {e}")
            traceback.print_exc()
            return {"enabled": False, "channel_id": ""}

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Cek channel restriction
    # ═══════════════════════════════════════════════════════════════════════
    def _is_channel_allowed(self, settings: dict, channel_id: str) -> bool:
        allowed_channel = settings.get("channel_id", "")
        if not allowed_channel:
            return True
        return str(channel_id) == str(allowed_channel)

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Ambil chat history user dari Firestore (ASYNC)
    # ═══════════════════════════════════════════════════════════════════════
    async def _get_chat_history(self, guild_id: str, user_id: str) -> List[Dict[str, Any]]:
        try:
            doc_ref = (
                db.collection("guild_settings")
                .document(str(guild_id))
                .collection("ai_chat")
                .document(str(user_id))
            )
            doc = await asyncio.to_thread(doc_ref.get)
            if not doc.exists:
                return []
            data = doc.to_dict()
            history = data.get("history", [])
            valid_history = []
            for item in history:
                if isinstance(item, dict) and "role" in item and "content" in item:
                    valid_history.append(item)
            return valid_history
        except Exception as e:
            print(f"[AI CHAT] ⚠️ Error ambil history: {e}")
            return []

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Simpan chat history (ASYNC)
    # ═══════════════════════════════════════════════════════════════════════
    async def _save_chat_history(
        self,
        guild_id: str,
        user_id: str,
        user_msg: str,
        assistant_msg: str,
        personality: str = DEFAULT_PERSONALITY,
    ) -> None:
        try:
            old_history = await self._get_chat_history(guild_id, user_id)
            now = datetime.now(timezone.utc).isoformat()
            new_history = old_history + [
                {"role": "user", "content": user_msg, "timestamp": now},
                {"role": "assistant", "content": assistant_msg, "timestamp": now},
            ]

            if len(new_history) > 10:
                new_history = new_history[-10:]

            doc_ref = (
                db.collection("guild_settings")
                .document(str(guild_id))
                .collection("ai_chat")
                .document(str(user_id))
            )
            await asyncio.to_thread(
                doc_ref.set,
                {
                    "history": new_history,
                    "personality": personality,
                    "updated_at": datetime.now(timezone.utc),
                },
                merge=True,
            )
        except Exception as e:
            print(f"[AI CHAT] ⚠️ Error simpan history: {e}")
            traceback.print_exc()

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Bangun konteks server (lightweight)
    # ═══════════════════════════════════════════════════════════════════════
    def _build_server_context(self, guild: discord.Guild) -> str:
        if not guild:
            return ""
        try:
            member_count = guild.member_count or 0
            return f"""[CONTEXT SERVER]
• Nama Server : {guild.name}
• ID Server   : {guild.id}
• Total Member: {member_count}
• Boost Level : {guild.premium_tier}
• Dibuat Pada : {guild.created_at.strftime('%Y-%m-%d')}
"""
        except Exception:
            return ""

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Call Gemini REST API
    # ═══════════════════════════════════════════════════════════════════════
    async def _call_gemini(
        self,
        user_message: str,
        history: List[Dict[str, Any]],
        system_prompt: str,
    ) -> str:
        if not self.api_key:
            return "❌ GEMINI_API_KEY tidak ditemukan. Hubungi admin bot."

        if not self.session:
            return "❌ HTTP session belum siap. Coba lagi nanti."

        try:
            # Build contents array from history + current message
            contents = []

            # Add system prompt as first user message (Gemini REST API pattern)
            if system_prompt:
                contents.append({
                    "role": "user",
                    "parts": [{"text": f"[SYSTEM INSTRUCTION]\n{system_prompt}\n\nRespond to the following messages based on the system instruction above."}]
                })
                contents.append({
                    "role": "model",
                    "parts": [{"text": "Understood. I will follow the system instruction and respond accordingly."}]
                })

            # Add chat history
            for item in history:
                role = "model" if item["role"] == "assistant" else "user"
                contents.append({
                    "role": role,
                    "parts": [{"text": item["content"]}]
                })

            # Add current user message
            contents.append({
                "role": "user",
                "parts": [{"text": user_message}]
            })

            # Build request payload
            payload = {
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.75,
                    "topP": 0.95,
                    "maxOutputTokens": 1024,
                }
            }

            url = f"{GEMINI_API_BASE}/models/{GEMINI_MODEL}:generateContent?key={self.api_key}"

            headers = {
                "Content-Type": "application/json",
            }

            async with self.session.post(url, headers=headers, json=payload) as resp:
                status = resp.status
                response_data = await resp.json()

                if status == 429:
                    print(f"[AI CHAT] ⛔ Rate limit (429): {response_data}")
                    return (
                        "Waduh, kepala AI-ku lagi pusing nih! 🧠💥\n"
                        "Rate limit dari Google-nya kena. Coba tanya lagi dalam beberapa menit ya, bro!"
                    )

                if status == 400:
                    error_msg = response_data.get("error", {}).get("message", "Unknown error")
                    print(f"[AI CHAT] ❌ Bad Request (400): {error_msg}")
                    return f"❌ Error dari Google API: {error_msg}"

                if status == 403:
                    print(f"[AI CHAT] ❌ Forbidden (403): API key invalid or expired")
                    return "❌ API key tidak valid atau expired. Hubungi admin."

                if status != 200:
                    print(f"[AI CHAT] ❌ HTTP {status}: {response_data}")
                    return f"❌ Error dari Google API (HTTP {status}). Coba lagi nanti."

                # Extract response text
                candidates = response_data.get("candidates", [])
                if not candidates:
                    print(f"[AI CHAT] ⚠️ No candidates in response: {response_data}")
                    return "Hmmm, aku blank sebentar... coba tanya lagi? 🤔"

                content = candidates[0].get("content", {})
                parts = content.get("parts", [])

                if not parts:
                    return "Hmmm, aku blank sebentar... coba tanya lagi? 🤔"

                response_text = parts[0].get("text", "").strip()

                if not response_text:
                    return "Hmmm, aku blank sebentar... coba tanya lagi? 🤔"

                return response_text

        except asyncio.TimeoutError:
            print("[AI CHAT] ⏱️ Timeout: Gemini API tidak merespons dalam 30 detik")
            return "⏱️ Timeout! AI-nya lagi lambat nih, coba tanya lagi ya."

        except aiohttp.ClientError as e:
            print(f"[AI CHAT] ❌ HTTP Client Error: {e}")
            return "❌ Koneksi ke Google API bermasalah. Coba lagi nanti."

        except Exception as e:
            print(f"[AI CHAT] ❌ Error Gemini REST: {e}")
            traceback.print_exc()
            return "Aduh, ada error di otakku... coba lagi nanti ya! 🛠️"

    # ═══════════════════════════════════════════════════════════════════════
    # HELPER: Kirim balasan (handle Interaction vs Message)
    # ═══════════════════════════════════════════════════════════════════════
    async def _send_response(self, ctx, text: str):
        if isinstance(ctx, discord.Interaction):
            if len(text) > 2000:
                chunks = [text[i : i + 1900] for i in range(0, len(text), 1900)]
                await ctx.followup.send(chunks[0])
                for chunk in chunks[1:]:
                    await ctx.followup.send(chunk)
            else:
                await ctx.followup.send(text)
        else:
            if len(text) > 2000:
                chunks = [text[i : i + 1900] for i in range(0, len(text), 1900)]
                for idx, chunk in enumerate(chunks):
                    if idx == 0:
                        await ctx.reply(chunk, mention_author=False)
                    else:
                        await ctx.channel.send(chunk)
            else:
                await ctx.reply(text, mention_author=False)

    # ═══════════════════════════════════════════════════════════════════════
    # CORE: Proses pertanyaan (slash command & mention)
    # ═══════════════════════════════════════════════════════════════════════
    async def _process_ai_chat(self, ctx, user_message: str, guild: discord.Guild, user: discord.User):
        guild_id = str(guild.id)
        user_id = str(user.id)

        # ── 1. Cek apakah fitur aktif ──
        settings = await self._get_guild_ai_settings(guild_id)
        if not settings.get("enabled", False):
            await self._send_response(ctx, "⚠️ AI Chat sedang dimatikan oleh admin server. Hubungi admin untuk mengaktifkannya.")
            return

        # ── 2. Cek channel restriction ──
        channel_id = ""
        typing_ctx = None
        if isinstance(ctx, discord.Interaction):
            channel_id = str(ctx.channel_id)
            typing_ctx = ctx.channel
        else:
            channel_id = str(ctx.channel.id)
            typing_ctx = ctx.channel

        if not self._is_channel_allowed(settings, channel_id):
            await self._send_response(ctx, "⚠️ AI Chat hanya bisa digunakan di channel yang sudah diatur oleh admin.")
            return

        # ── 3. Ambil personality & history ──
        personality = settings.get("personality", DEFAULT_PERSONALITY)
        history = await self._get_chat_history(guild_id, user_id)

        # ── 4. Bangun system prompt ──
        server_ctx = self._build_server_context(guild)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            personality=personality,
            server_context=server_ctx,
        )

        # ── 5. Panggil Gemini dengan typing indicator ──
        try:
            async with typing_ctx.typing():
                response_text = await self._call_gemini(
                    user_message=user_message,
                    history=history,
                    system_prompt=system_prompt,
                )
        except Exception as e:
            print(f"[AI CHAT] ⚠️ Typing indicator error: {e}")
            response_text = await self._call_gemini(
                user_message=user_message,
                history=history,
                system_prompt=system_prompt,
            )

        # ── 6. Simpan ke Firestore ──
        await self._save_chat_history(
            guild_id=guild_id,
            user_id=user_id,
            user_msg=user_message,
            assistant_msg=response_text,
            personality=personality,
        )

        # ── 7. Kirim balasan ──
        await self._send_response(ctx, response_text)

    # ═══════════════════════════════════════════════════════════════════════
    # SLASH COMMAND: /ask
    # ═══════════════════════════════════════════════════════════════════════
    @app_commands.command(name="ask", description="Tanya apa saja ke AI Gemini Hidden Hamlet")
    @app_commands.describe(pertanyaan="Apa yang mau ditanyakan?")
    async def ask(self, interaction: discord.Interaction, pertanyaan: str):
        guild_id = str(interaction.guild_id)
        user_id = str(interaction.user.id)
        now = datetime.now(timezone.utc).timestamp()

        # ── Manual Cooldown Check ──
        key = (guild_id, user_id)
        last_used = self._cooldowns.get(key, 0)
        if now - last_used < COOLDOWN_SECONDS:
            retry_after = COOLDOWN_SECONDS - (now - last_used)
            embed = discord.Embed(
                title="⏳ Cooldown",
                description=f"Sabar bro! Tunggu **{retry_after:.1f} detik** lagi sebelum tanya lagi.",
                color=discord.Color.orange(),
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        self._cooldowns[key] = now

        # ── Defer & Process ──
        await interaction.response.defer(thinking=False)
        try:
            await self._process_ai_chat(
                ctx=interaction,
                user_message=pertanyaan,
                guild=interaction.guild,
                user=interaction.user,
            )
        except Exception as e:
            print(f"[AI CHAT] ❌ Fatal error di /ask: {e}")
            traceback.print_exc()
            try:
                await interaction.followup.send("❌ Terjadi error internal. Coba lagi nanti ya!")
            except Exception:
                pass

    # ═══════════════════════════════════════════════════════════════════════
    # EVENT LISTENER: Mention @HiddenHamlet di text channel
    # ═══════════════════════════════════════════════════════════════════════
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return
        if not message.guild:
            return

        # ── Cek apakah AI Chat aktif untuk guild ini ──
        settings = await self._get_guild_ai_settings(str(message.guild.id))
        if not settings.get("enabled", False):
            return

        # ── Cek mention ──
        bot_mentioned = (
            self.bot.user in message.mentions
            or self.bot.user.id in [m.id for m in message.mentions]
        )
        if not bot_mentioned:
            return

        # ── Cek channel restriction ──
        if not self._is_channel_allowed(settings, str(message.channel.id)):
            return

        # ── Extract text setelah mention ──
        content = message.content.replace(f"<@{self.bot.user.id}>", "").replace(
            f"<@!{self.bot.user.id}>", ""
        ).strip()

        if not content:
            await message.reply(
                "Halo! Ada yang bisa kubantu? 🤖\n"
                "Tanya aku langsung atau pakai `/ask`",
                mention_author=False,
            )
            return

        # ── Manual Cooldown untuk mention ──
        key = (str(message.guild.id), str(message.author.id))
        now = datetime.now(timezone.utc).timestamp()
        last_used = self._cooldowns.get(key, 0)

        if now - last_used < COOLDOWN_SECONDS:
            return  # Silent cooldown

        self._cooldowns[key] = now

        # ── Process ──
        try:
            await self._process_ai_chat(
                ctx=message,
                user_message=content,
                guild=message.guild,
                user=message.author,
            )
        except Exception as e:
            print(f"[AI CHAT] ❌ Fatal error di on_message: {e}")
            traceback.print_exc()
            try:
                await message.reply("❌ Terjadi error internal. Coba lagi nanti ya!", mention_author=False)
            except Exception:
                pass


# ═══════════════════════════════════════════════════════════════════════════
# SETUP: Async setup untuk discord.py v2.x
# ═══════════════════════════════════════════════════════════════════════════
async def setup(bot: commands.Bot):
    cog = AIChat(bot)
    await bot.add_cog(cog)
    await cog.cog_load()  # Initialize HTTP session
