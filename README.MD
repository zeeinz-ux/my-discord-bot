# Hidden Hamlet — Discord Bot v4.7

A multifunctional Discord bot with a web dashboard, AI chat, music player, moderation, leveling, and server management tools.

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.11 |
| Bot Library | discord.py 2.7.1 (with voice) |
| Web Server | Flask 3.1.3 + Gunicorn |
| Database | Firebase Firestore (free tier) |
| Music | yt-dlp 2026.6+ + FFmpeg (direct stream extraction, no Lavalink) |
| YouTube auth | bgutil-ytdlp-pot-provider + Deno JS runtime (PO token generation) |
| AI Chat | Google Gemini → Groq (Llama 3.3) → OpenRouter (fallback chain) |
| Sessions | Flask-Session (server-side file) |
| Deployment | Docker → Railway + UptimeRobot |

## Features

### Discord Cogs

| Cog | Description |
|-----|-------------|
| **Music** | YouTube/Spotify/SoundCloud playback via yt-dlp + FFmpeg. Spotify URL resolver with triple fallback (SpotifyDown → oEmbed → page scrape → yt-dlp extractor). Local audio cache. PO token auto-generation to bypass YouTube bot detection. Triple-API YouTube search (yt-dlp → YouTube Data API v3 → web scrape). |
| **AI Chat** | Triple API fallback (Gemini → Groq → OpenRouter), personality, temperature, channel restriction, circuit breaker, personalized mentions. |
| **Welcome** | Dual-style embed/banner auto-welcome with drag-drop image upload (Firestore base64). |
| **Leave** | Auto-leave announcement (embed/banner). |
| **Ban** | Auto-ban announcement (embed/banner). |
| **Boost Announce** | Auto-boost announcement (embed/banner). |
| **Boost Tracker** | Track boost/unboost history. |
| **Donation** | Track donation transactions. |
| **Moderation** | Spam detection with 3-strike system (timeout → kick → ban). |
| **Leveling** | XP system with rank & leaderboard. |
| **Auto-Responder** | Keyword-triggered replies with regex, cooldown, channel filters. |
| **General** | Ping, stats, help commands. |

### Music Player Highlights

- **Play URL or search query** — YouTube, Spotify (track/playlist/album/artist), SoundCloud
- **Spotify playlist resolution** — extracts metadata via SpotifyDown API → falls back to oEmbed → page JSON scrape → yt-dlp extractor
- **Background playlist loading** — first track plays immediately, rest resolve in background
- **Local audio cache** — `/tmp/discord_audio_cache/` (ephemeral on Railway)
- **Session owner** — first `/play` caller controls the session until `/stop`
- **Auto-advance** — `_on_track_end_wrapper` chains to next track in queue
- **Voice connection recovery** — auto-reconnect on disconnect, resume from state file
- **Watchdog** — trip on stuck playback (configurable timeout)
- **Sequential pre-load** — pre-download next 3 tracks for seamless transition

### Web Dashboard

| Page | Description |
|------|-------------|
| `/` | Landing page with bot stats, sakura petals animation |
| `/dashboard/<guild>/` | Server overview — real-time stats, music player status |
| `/dashboard/<guild>/welcome` | Welcome settings with live preview |
| `/dashboard/<guild>/welcome/leave` | Leave announcement config |
| `/dashboard/<guild>/welcome/ban` | Ban announcement config |
| `/dashboard/<guild>/welcome/boost` | Boost announce config |
| `/dashboard/<guild>/ai-chat` | AI Chat settings |
| `/dashboard/<guild>/auto-responders` | Auto-responder manager |

### Auth & Permissions

- Discord OAuth2 login (`identify` + `guilds` scopes)
- Guild sidebar filtered to servers where user has **ADMINISTRATOR** or **MANAGE_GUILD** and the bot is present
- Per-request guild access guard
- Feature-level per-guild settings in Firestore
- Guild lifecycle: auto-create settings on join, clean up on remove

## Project Structure

```
discord-bot/
├── backend/
│   ├── cogs/                  # Discord bot modules (auto-loaded by setup_hook)
│   │   ├── ai_chat/           # AI Chat with triple API fallback
│   │   ├── auto_response/     # Keyword auto-responder
│   │   ├── ban_settings/      # Ban announcement
│   │   ├── boost/             # Boost tracker
│   │   ├── boost_announce/    # Boost announcement
│   │   ├── database/          # Firebase initialization (firebase_setup)
│   │   ├── donation/          # Donation tracker
│   │   ├── general/           # Ping, stats, help
│   │   ├── leave_settings/    # Leave announcement
│   │   ├── leveling/          # XP/Leveling system
│   │   ├── moderation/        # Spam detection
│   │   ├── music/             # Music player (yt-dlp + FFmpeg)
│   │   │   ├── music.py       # Music cog (slash commands)
│   │   │   ├── ytdlp_source.py # yt-dlp wrapper, MusicController, queue
│   │   │   ├── spotify_down.py # Spotify resolver (SpotifyDown → oEmbed → scrape)
│   │   │   └── queue_manager.py
│   │   └── welcome/           # Welcome cog (embed/banner)
│   ├── utils/                 # Shared helpers (formatters, constants)
│   ├── web/                   # Flask routes (web_app.py)
│   └── main.py                # Bot entrypoint (setup_hook loads cogs)
├── frontend/
│   ├── templates/             # 21 Jinja2 HTML templates
│   └── static/
│       ├── css/               # Page-specific styles
│       └── js/                # Page-specific logic
├── cookies/                   # YouTube cookies (Netscape format, optional)
├── flask_session/             # Flask-Session file storage (gitignored)
├── scripts/                   # Helper scripts (e.g. Spotify OAuth2 token)
├── Dockerfile                 # Production image (FFmpeg + bgutil-pot + Deno)
├── Procfile                   # honcho: web (gunicorn) + worker (bot)
└── railway.json               # Railway deploy config
```

## Deployment

### Local development

```bash
# Install deps
pip install -r requirements.txt

# FFmpeg must be installed and on PATH
ffmpeg -version

# Run bot + web dashboard
honcho start -f Procfile
# or
python backend/main.py
```

### Production (Railway)

- **Build:** `Dockerfile` (Python 3.11-slim + FFmpeg + bgutil-pot + Deno)
- **Start:** `honcho start -f Procfile`
  - `web`: gunicorn `--bind 0.0.0.0:$PORT --workers 2 --timeout 120 backend.web.web_app:app`
  - `worker`: `python backend/main.py`
- **24/7:** UptimeRobot pings every 5 min to prevent sleep
- **YouTube auth:** `bgutil-ytdlp-pot-provider` runs on localhost to auto-generate PO tokens, bypassing YouTube bot detection

### Module path

Bot modules are loaded as `backend.cogs.<name>` (with `backend/` on `sys.path` via `PYTHONPATH=/app` in the Dockerfile + runtime injection in `main.py`).

## Environment Variables

See `backend/.env.example` for the full list. Key variables:

- `DISCORD_TOKEN`, `DISCORD_CLIENT_ID`, `DISCORD_CLIENT_SECRET`, `DISCORD_REDIRECT_URI`
- `FLASK_SECRET_KEY`
- `FIREBASE_KEY` (path to service account JSON, or full JSON in single line)
- `GEMINI_API_KEY`, `GROQ_API_KEY`, `OPENROUTER_API_KEY` (at least one for AI Chat)
- `SPOTIFY_CLIENT_ID`, `SPOTIFY_CLIENT_SECRET` (optional, for Spotify features)
- `SPOTIFY_USER_REFRESH_TOKEN` (optional, bypasses Spotify API sandbox 403s)
- `YOUTUBE_API_KEY` (optional, fallback search when yt-dlp fails)
- `YOUTUBE_COOKIES_TXT` (optional, paste Netscape cookies as env var)
- `YTDLP_PROXY` (optional, override default direct connection)

## License

All Rights Reserved.