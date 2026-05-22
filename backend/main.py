import sys
import os

# ==========================================================
# FIX: Agar Python bisa menemukan package 'backend'
# ==========================================================
_project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import discord
from discord.ext import commands, tasks
import time
import threading
from dotenv import load_dotenv
import wavelink
import asyncio

load_dotenv()

# ==========================================================
# KUMPULKAN SEMUA IMPOR PENTING DI ATAS
# ==========================================================
from backend.cogs.firebase_setup import initialize_firestore
from backend.web.web_app import app, set_stats, set_guild_channels, set_bot_instance, set_db_instance
from backend.utils.constants import LAVALINK_NODES

# ==========================================================
# INISIALISASI DATABASE & PEMBERIAN INSTANCE
# ==========================================================
# 1. Buat koneksi database SATU KALI
db = initialize_firestore()

# 2. Berikan instance DB ke web app
if db:
    set_db_instance(db)
    print("[MAIN] ✅ Instance Firestore berhasil diberikan ke Web App.")
else:
    print("[MAIN] ⚠️ Koneksi Firestore gagal, beberapa fitur web mungkin tidak berfungsi.")

# ==========================================================
# SETUP BOT DISCORD
# ==========================================================
intents = discord.Intents.default()
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 3. Berikan instance DB ke bot
bot.db = db

start_time = time.time()

# Berikan instance bot ke web app
set_bot_instance(bot)

# ==========================================================
# FLASK (WEB DASHBOARD) THREAD
# ==========================================================
def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

flask_thread = threading.Thread(target=run_flask, daemon=True)
flask_thread.start()

# ==========================================================
# BOT SETUP HOOK (Async Initialization)
# ==========================================================
@bot.event
async def setup_hook():
    # --- LAVALINK NODES ---
    nodes = [
        wavelink.Node(uri=node["uri"], password=node["password"])
        for node in LAVALINK_NODES
    ]
    await wavelink.Pool.connect(nodes=nodes, client=bot, cache_capacity=100)

    # --- LOAD COGS ---
    cogs_dir = os.path.join(_project_root, "backend", "cogs")
    cog_count = 0
    exclude_files = ("__init__.py", "firebase_setup.py", "spotify_down.py")

    print("\n" + "=" * 50)
    for filename in os.listdir(cogs_dir):
        if filename.endswith(".py") and filename not in exclude_files:
            cog_name = filename[:-3]
            try:
                await bot.load_extension(f"backend.cogs.{cog_name}")
                print(f"[COG] 📦 Loaded: {filename}")
                cog_count += 1
            except Exception as e:
                print(f"[COG] ❌ Failed to load {filename}: {e}")
    print(f"[COG] ✅ Total {cog_count} cogs loaded!")
    print("=" * 50)

# ==========================================================
# BOT EVENTS (on_ready, etc.)
# ==========================================================
@bot.event
async def on_ready():
    print(f"[STATUS] 🤖 {bot.user.name} SEKARANG SUDAH ONLINE!")
    print(f"[STATUS] Terhubung ke {len(bot.guilds)} server Discord.")

    try:
        synced = await bot.tree.sync()
        print(f"[SYNC] ✅ {len(synced)} slash command(s) berhasil di-sync!")
    except Exception as e:
        print(f"[SYNC] ❌ Gagal sync commands: {e}")

    # Jalankan background tasks setelah semua siap
    if not lavalink_healthcheck.is_running():
        lavalink_healthcheck.start()
        print("[TASKS] 🔄 Lavalink health check loop aktif (60s).")

    if not update_stats.is_running():
        update_stats.start()
        print("[TASKS] 📊 Dashboard stats updater aktif (30s).")

    print("=" * 50)

# ==========================================================
# BACKGROUND TASKS (Loops)
# ==========================================================
@tasks.loop(seconds=60)
async def lavalink_healthcheck():
    # Simplified check from your original code
    if not wavelink.Pool.nodes:
        print("[LAVALINK] ⚠️ Node tidak terdeteksi, mencoba reconnect...")
        # Add reconnect logic if needed, for now, it just reports.

@lavalink_healthcheck.before_loop
async def before_healthcheck():
    await bot.wait_until_ready()

@tasks.loop(seconds=30)
async def update_stats():
    try:
        # This entire block is from your original code
        nodes = wavelink.Pool.nodes
        lavalink_ok = bool(nodes)
        node_uri = list(nodes.values())[0].uri if nodes else "N/A"

        players = []
        for guild in bot.guilds:
            vc = guild.voice_client
            if vc and getattr(vc, "current", None):
                ch = getattr(vc, "channel", None)
                listeners = len([m for m in ch.members if not m.bot]) if ch else 0
                players.append({
                    "guild": guild.name,
                    "track": vc.current.title,
                    "author": vc.current.author or "Unknown",
                    "duration": vc.current.length or 0,
                    "position": getattr(vc, "position", 0) or 0,
                    "queue": len(vc.queue) if hasattr(vc, "queue") else 0,
                    "listeners": listeners,
                    "paused": getattr(vc, "paused", False),
                    "artwork": vc.current.artwork or ""
                })

        for guild in bot.guilds:
            text_channels = [
                {"id": str(ch.id), "name": ch.name}
                for ch in guild.text_channels
                if ch.permissions_for(guild.me).send_messages
            ]
            set_guild_channels(str(guild.id), text_channels)

        guilds_list = [
            {"id": str(g.id), "name": g.name, "member_count": g.member_count or 0}
            for g in bot.guilds
        ]

        set_stats(
            online=bot.is_ready(),
            username=bot.user.name if bot.user else "Hidden Hamlet",
            uptime=int(time.time() - start_time),
            guilds=len(bot.guilds),
            members=sum(g.member_count or 0 for g in bot.guilds),
            lavalink_connected=lavalink_ok,
            lavalink_node=node_uri,
            players=players,
            guilds_list=guilds_list
        )

    except Exception as e:
        print(f"[DASHBOARD STATS ERROR] {e}")

@update_stats.before_loop
async def before_update_stats():
    await bot.wait_until_ready()

# ==========================================================
# RUN THE BOT
# ==========================================================
TOKEN = os.getenv("TOKEN_BOT")
if not TOKEN:
    print("[ERROR] TOKEN_BOT tidak ditemukan di .env!")
    exit(1)

bot.run(TOKEN)
