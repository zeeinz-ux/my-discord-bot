"""
Spotify Resolver — Embed Scraper Edition (No Premium Required)
===============================================================
Fallback: SpotifyDown → Embed Scraper → oEmbed → HTML scrape
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple

import aiohttp

logger = logging.getLogger(__name__)

SPOTIFYDOWN_BASE = "https://api.spotifydown.com"
REQUEST_TIMEOUT = 15
MAX_RETRIES = 2

SPOTIFY_URL_PATTERNS = [
    r"open\.spotify\.com/(?P<type>track|playlist|album)/(?P<id>[a-zA-Z0-9]+)",
    r"spotify:(?P<type>track|playlist|album):(?P<id>[a-zA-Z0-9]+)",
]

@dataclass
class ResolvedTrack:
    name: str
    artists: str
    album: Optional[str]
    duration_ms: Optional[int]
    artwork: Optional[str]
    spotify_id: str
    youtube_id: Optional[str]
    query: str
    source: str

class SpotifyDownClient:
    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/json",
            "Origin": "https://spotifydown.com",
            "Referer": "https://spotifydown.com/",
        }

    async def _request(self, method: str, endpoint: str, **kwargs) -> Optional[Dict]:
        url = f"{SPOTIFYDOWN_BASE}{endpoint}"
        for attempt in range(MAX_RETRIES):
            try:
                async with self.session.request(
                    method, url, headers=self.headers,
                    timeout=aiohttp.ClientTimeout(total=REQUEST_TIMEOUT), **kwargs,
                ) as resp:
                    if resp.status == 200:
                        return await resp.json()
                    elif resp.status in (429, 502, 503):
                        wait = 2 ** attempt
                        logger.warning("SpotifyDown %s pada %s, retry dalam %ss...", resp.status, endpoint, wait)
                        await asyncio.sleep(wait)
                    else:
                        logger.error("SpotifyDown error %s pada %s", resp.status, endpoint)
                        return None
            except asyncio.TimeoutError:
                logger.warning("SpotifyDown timeout (attempt %s/%s) pada %s", attempt + 1, MAX_RETRIES, endpoint)
                if attempt < MAX_RETRIES - 1:
                    await asyncio.sleep(2 ** attempt)
            except Exception as e:
                logger.error("SpotifyDown exception: %s", e)
                return None
        return None

    async def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        tracks: List[Dict] = []
        offset = 0
        while True:
            params = {"offset": offset} if offset else {}
            data = await self._request("GET", f"/trackList/playlist/{playlist_id}", params=params)
            if not data or "trackList" not in data:
                break
            batch = data["trackList"]
            if not batch:
                break
            tracks.extend(batch)
            next_offset = data.get("nextOffset")
            if next_offset is None or next_offset == offset:
                break
            offset = next_offset
        return tracks

    async def get_album_tracks(self, album_id: str) -> List[Dict]:
        tracks: List[Dict] = []
        offset = 0
        while True:
            params = {"offset": offset} if offset else {}
            data = await self._request("GET", f"/trackList/album/{album_id}", params=params)
            if not data or "trackList" not in data:
                break
            batch = data["trackList"]
            if not batch:
                break
            tracks.extend(batch)
            next_offset = data.get("nextOffset")
            if next_offset is None or next_offset == offset:
                break
            offset = next_offset
        return tracks

    async def get_youtube_id(self, spotify_track_id: str) -> Optional[str]:
        data = await self._request("GET", f"/getId/{spotify_track_id}")
        if data and "id" in data:
            return data["id"]
        return None

class SpotifyEmbedScraper:
    """Scrapes open.spotify.com/embed/... pages for track data."""

    def __init__(self, session: aiohttp.ClientSession):
        self.session = session
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://open.spotify.com/",
        }

    @staticmethod
    def _extract_json(html: str) -> Optional[Dict]:
        patterns = [
            r'<script[^>]*id=["']initial-state["'][^>]*>(.*?)</script>',
            r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});?\s*</script>',
            r'window\.__data\s*=\s*(\{.*?\});?\s*</script>',
            r'<script[^>]*id=["']embed_state["'][^>]*>(.*?)</script>',
        ]
        for pattern in patterns:
            match = re.search(pattern, html, re.DOTALL)
            if match:
                raw = match.group(1)
                try:
                    return json.loads(raw)
                except json.JSONDecodeError:
                    try:
                        raw = raw.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
                        return json.loads(raw)
                    except json.JSONDecodeError:
                        continue
        return None

    async def get_playlist_tracks(self, playlist_id: str) -> List[Dict]:
        logger.warning("[SPOTIFY EMBED] Scraping playlist %s...", playlist_id)
        url = f"https://open.spotify.com/embed/playlist/{playlist_id}"
        try:
            async with self.session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    logger.error("[SPOTIFY EMBED] HTTP %s", resp.status)
                    return []
                html = await resp.text()
        except Exception as e:
            logger.error("[SPOTIFY EMBED] Request failed: %s", e)
            return []

        data = self._extract_json(html)
        if not data:
            logger.error("[SPOTIFY EMBED] No JSON found in page.")
            return []

        # Try multiple JSON paths
        raw_items = []
        paths = [
            lambda d: d.get("data", {}).get("playlist", {}).get("tracks", {}).get("items", []),
            lambda d: d.get("data", {}).get("playlist", {}).get("contents", {}).get("items", []),
            lambda d: d.get("embedState", {}).get("playlist", {}).get("tracks", []),
            lambda d: d.get("state", {}).get("playlist", {}).get("tracks", []),
            lambda d: d.get("tracks", []),
            lambda d: d.get("data", {}).get("playlist", {}).get("trackList", []),
        ]
        for fn in paths:
            try:
                candidate = fn(data)
                if candidate and isinstance(candidate, list) and len(candidate) > 0:
                    raw_items = candidate
                    logger.warning("[SPOTIFY EMBED] Found %s items", len(candidate))
                    break
            except Exception:
                continue

        if not raw_items:
            logger.error("[SPOTIFY EMBED] No tracks in JSON.")
            return []

        tracks = []
        for item in raw_items:
            track = item.get("track") if isinstance(item, dict) else item
            if not track or not isinstance(track, dict):
                continue
            name = track.get("name", "")
            if not name:
                continue
            artists = []
            artist_objs = track.get("artists", track.get("artistsV2", []))
            if isinstance(artist_objs, list):
                for a in artist_objs:
                    if isinstance(a, dict):
                        artists.append(a.get("name", ""))
            artists_str = ", ".join(filter(None, artists)) or "Unknown"
            album = None
            album_obj = track.get("album")
            if isinstance(album_obj, dict):
                album = album_obj.get("name")
            duration = track.get("durationMs") or track.get("duration_ms")
            if not duration and isinstance(track.get("duration"), dict):
                duration = track["duration"].get("totalMilliseconds")
            tid = track.get("id", "")
            uri = track.get("uri", "")
            if not tid and uri and ":" in uri:
                tid = uri.split(":")[-1]
            artwork = None
            img = track.get("coverArt") or track.get("images") or (album_obj.get("images") if album_obj else None)
            if isinstance(img, list) and img:
                artwork = img[0].get("url", img[0]) if isinstance(img[0], dict) else img[0]
            elif isinstance(img, dict):
                artwork = img.get("url") or img.get("sources", [{}])[0].get("url")
            tracks.append({"name": name, "artists": artists_str, "album": album, "duration_ms": duration, "artwork": artwork, "id": tid, "uri": uri})
        logger.warning("[SPOTIFY EMBED] Parsed %s tracks", len(tracks))
        return tracks

    async def get_album_tracks(self, album_id: str) -> List[Dict]:
        url = f"https://open.spotify.com/embed/album/{album_id}"
        try:
            async with self.session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=15)) as resp:
                if resp.status != 200:
                    return []
                html = await resp.text()
        except Exception:
            return []
        data = self._extract_json(html)
        if not data:
            return []
        raw_items = []
        paths = [
            lambda d: d.get("data", {}).get("album", {}).get("tracks", {}).get("items", []),
            lambda d: d.get("data", {}).get("album", {}).get("contents", {}).get("items", []),
            lambda d: d.get("embedState", {}).get("album", {}).get("tracks", []),
            lambda d: d.get("state", {}).get("album", {}).get("tracks", []),
            lambda d: d.get("tracks", []),
        ]
        for fn in paths:
            try:
                candidate = fn(data)
                if candidate and isinstance(candidate, list) and len(candidate) > 0:
                    raw_items = candidate
                    break
            except Exception:
                continue
        tracks = []
        for item in raw_items:
            track = item if isinstance(item, dict) else item.get("track")
            if not track or not isinstance(track, dict):
                continue
            name = track.get("name", "")
            if not name:
                continue
            artists = []
            for a in track.get("artists", []):
                if isinstance(a, dict):
                    artists.append(a.get("name", ""))
            artists_str = ", ".join(filter(None, artists)) or "Unknown"
            duration = track.get("durationMs") or track.get("duration_ms")
            tid = track.get("id", "")
            uri = track.get("uri", "")
            if not tid and uri and ":" in uri:
                tid = uri.split(":")[-1]
            tracks.append({"name": name, "artists": artists_str, "album": None, "duration_ms": duration, "artwork": None, "id": tid, "uri": uri})
        return tracks

    async def get_track(self, track_id: str) -> Optional[Dict]:
        url = f"https://open.spotify.com/embed/track/{track_id}"
        try:
            async with self.session.get(url, headers=self.headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status != 200:
                    return None
                html = await resp.text()
        except Exception:
            return None
        data = self._extract_json(html)
        if not data:
            return None
        track = None
        for fn in [
            lambda d: d.get("data", {}).get("entity", {}),
            lambda d: d.get("data", {}).get("track", {}),
            lambda d: d.get("embedState", {}).get("track", {}),
        ]:
            try:
                candidate = fn(data)
                if candidate and candidate.get("name"):
                    track = candidate
                    break
            except Exception:
                continue
        if not track:
            return None
        artists = []
        for a in track.get("artists", []):
            if isinstance(a, dict):
                artists.append(a.get("name", ""))
        artists_str = ", ".join(filter(None, artists)) or "Unknown"
        album = None
        album_obj = track.get("album")
        if isinstance(album_obj, dict):
            album = album_obj.get("name")
        return {"name": track["name"], "artists": artists_str, "album": album, "duration_ms": track.get("durationMs"), "id": track.get("id", track_id)}

class SpotifyOfficialClient(SpotifyEmbedScraper):
    """Backward-compatible name; internally uses embed scraper."""
    pass

async def _get_spotify_metadata_oembed(session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
    try:
        encoded_url = url.replace(" ", "%20").replace("&", "%26")
        oembed_url = f"https://open.spotify.com/oembed?url={encoded_url}"
        async with session.get(oembed_url, timeout=aiohttp.ClientTimeout(total=10), headers={"User-Agent": "Mozilla/5.0"}) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            return {"name": data.get("title", ""), "artists": data.get("author_name", ""), "artwork": data.get("thumbnail_url", ""), "album": None, "duration_ms": None}
    except Exception as e:
        logger.error("[SPOTIFY OEMBED ERROR] %s", e)
        return None

async def _get_spotify_metadata_html(session: aiohttp.ClientSession, url: str) -> Optional[Dict]:
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10), headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36", "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8", "Accept-Language": "en-US,en;q=0.9"}) as resp:
            if resp.status != 200:
                return None
            html = await resp.text()
        title_match = re.search(r'<meta[^>]*property="og:title"[^>]*content="([^"]*)"', html)
        title = title_match.group(1) if title_match else ""
        desc_match = re.search(r'<meta[^>]*property="og:description"[^>]*content="([^"]*)"', html)
        description = desc_match.group(1) if desc_match else ""
        image_match = re.search(r'<meta[^>]*property="og:image"[^>]*content="([^"]*)"', html)
        image = image_match.group(1) if image_match else ""
        artist = ""
        if " · " in description:
            parts = description.split(" · ")
            if len(parts) >= 1:
                artist = parts[0].replace("Listen to ", "").replace(" on Spotify", "").strip()
        elif " - " in description:
            artist = description.split(" - ")[0].strip()
        if not artist and title:
            if " - " in title:
                artist = title.split(" - ")[-1].strip()
                title = title.split(" - ")[0].strip()
            elif " — " in title:
                artist = title.split(" — ")[-1].strip()
                title = title.split(" — ")[0].strip()
        return {"name": title, "artists": artist, "artwork": image, "album": None, "duration_ms": None}
    except Exception as e:
        logger.error("[SPOTIFY HTML SCRAPE ERROR] %s", e)
        return None

class SpotifyResolver:
    def __init__(self, fallback_client_id: Optional[str] = None, fallback_client_secret: Optional[str] = None):
        self.embed = None
        self.official = None  # backward compat
        logger.warning("[SPOTIFY RESOLVER] Embed scraper ready (no credentials needed).")

    @staticmethod
    def parse_spotify_url(url: str) -> Optional[Tuple[str, str]]:
        for pattern in SPOTIFY_URL_PATTERNS:
            match = re.search(pattern, url)
            if match:
                return match.group("type"), match.group("id")
        return None

    async def resolve(self, url: str, session: aiohttp.ClientSession) -> Tuple[List[ResolvedTrack], str]:
        parsed = self.parse_spotify_url(url)
        if not parsed:
            return [], "invalid"
        spotify_type, spotify_id = parsed
        sd = SpotifyDownClient(session)
        self.embed = SpotifyEmbedScraper(session)
        if spotify_type == "track":
            return await self._resolve_track(spotify_id, sd, session, url)
        elif spotify_type == "playlist":
            return await self._resolve_playlist(spotify_id, sd, session, url)
        elif spotify_type == "album":
            return await self._resolve_album(spotify_id, sd, session, url)
        return [], "invalid"

    async def _resolve_track(self, track_id: str, sd: SpotifyDownClient, session: aiohttp.ClientSession, original_url: str) -> Tuple[List[ResolvedTrack], str]:
        yt_id = await sd.get_youtube_id(track_id)
        if yt_id:
            return [ResolvedTrack(name="Unknown", artists="Unknown", album=None, duration_ms=None, artwork=None, spotify_id=track_id, youtube_id=yt_id, query=f"https://youtube.com/watch?v={yt_id}", source="spotifydown")], "spotifydown"
        track_data = await self.embed.get_track(track_id)
        if track_data:
            return [ResolvedTrack(name=track_data["name"], artists=track_data["artists"], album=track_data.get("album"), duration_ms=track_data.get("duration_ms"), artwork=None, spotify_id=track_id, youtube_id=None, query=f"ytsearch:{track_data['name']} {track_data['artists']}", source="spotify_embed")], "spotify_embed"
        meta = await _get_spotify_metadata_oembed(session, original_url)
        if meta and meta.get("name"):
            return [ResolvedTrack(name=meta["name"], artists=meta["artists"], album=meta.get("album"), duration_ms=meta.get("duration_ms"), artwork=meta.get("artwork"), spotify_id=track_id, youtube_id=None, query=f"ytsearch:{meta['name']} {meta['artists']}", source="oembed")], "oembed"
        meta = await _get_spotify_metadata_html(session, original_url)
        if meta and meta.get("name"):
            return [ResolvedTrack(name=meta["name"], artists=meta["artists"], album=meta.get("album"), duration_ms=meta.get("duration_ms"), artwork=meta.get("artwork"), spotify_id=track_id, youtube_id=None, query=f"ytsearch:{meta['name']} {meta['artists']}", source="html_scrape")], "html_scrape"
        return [ResolvedTrack(name=f"Spotify Track {track_id}", artists="Unknown", album=None, duration_ms=None, artwork=None, spotify_id=track_id, youtube_id=None, query=f"ytsearch:spotify:{track_id}", source="ytsearch")], "ytsearch"

    async def _resolve_playlist(self, playlist_id: str, sd: SpotifyDownClient, session: aiohttp.ClientSession, original_url: str) -> Tuple[List[ResolvedTrack], str]:
        logger.warning("[RESOLVE PLAYLIST] Step 1: SpotifyDown API...")
        raw = await sd.get_playlist_tracks(playlist_id)
        if raw:
            logger.warning("[RESOLVE PLAYLIST] SpotifyDown OK: %d tracks", len(raw))
            return self._convert_sd_tracks(raw), "spotifydown"
        logger.warning("[RESOLVE PLAYLIST] SpotifyDown FAIL.")
        logger.warning("[RESOLVE PLAYLIST] Step 2: Embed Scraper...")
        raw = await self.embed.get_playlist_tracks(playlist_id)
        if raw:
            logger.warning("[RESOLVE PLAYLIST] Embed OK: %d tracks", len(raw))
            return [ResolvedTrack(name=t["name"], artists=t["artists"], album=t.get("album"), duration_ms=t.get("duration_ms"), artwork=t.get("artwork"), spotify_id=t["id"], youtube_id=None, query=f"ytsearch:{t['name']} {t['artists']}", source="spotify_embed") for t in raw], "spotify_embed"
        logger.warning("[RESOLVE PLAYLIST] Embed FAIL.")
        logger.warning("[RESOLVE PLAYLIST] Step 3: oEmbed...")
        meta = await _get_spotify_metadata_oembed(session, original_url)
        if meta and meta.get("name"):
            return [ResolvedTrack(name=meta["name"], artists=meta["artists"], album=None, duration_ms=None, artwork=meta.get("artwork"), spotify_id=playlist_id, youtube_id=None, query=f"ytsearch:{meta['name']} {meta['artists']} playlist", source="oembed")], "oembed"
        logger.warning("[RESOLVE PLAYLIST] Step 4: HTML scrape...")
        meta = await _get_spotify_metadata_html(session, original_url)
        if meta and meta.get("name"):
            return [ResolvedTrack(name=meta["name"], artists=meta["artists"], album=None, duration_ms=None, artwork=meta.get("artwork"), spotify_id=playlist_id, youtube_id=None, query=f"ytsearch:{meta['name']} {meta['artists']} playlist", source="html_scrape")], "html_scrape"
        return [], "failed"

    async def _resolve_album(self, album_id: str, sd: SpotifyDownClient, session: aiohttp.ClientSession, original_url: str) -> Tuple[List[ResolvedTrack], str]:
        raw = await sd.get_album_tracks(album_id)
        if raw:
            return self._convert_sd_tracks(raw), "spotifydown"
        raw = await self.embed.get_album_tracks(album_id)
        if raw:
            return [ResolvedTrack(name=t["name"], artists=t["artists"], album=None, duration_ms=t.get("duration_ms"), artwork=None, spotify_id=t["id"], youtube_id=None, query=f"ytsearch:{t['name']} {t['artists']} album", source="spotify_embed") for t in raw], "spotify_embed"
        meta = await _get_spotify_metadata_oembed(session, original_url)
        if meta and meta.get("name"):
            return [ResolvedTrack(name=meta["name"], artists=meta["artists"], album=meta["name"], duration_ms=None, artwork=meta.get("artwork"), spotify_id=album_id, youtube_id=None, query=f"ytsearch:{meta['name']} {meta['artists']} album", source="oembed")], "oembed"
        meta = await _get_spotify_metadata_html(session, original_url)
        if meta and meta.get("name"):
            return [ResolvedTrack(name=meta["name"], artists=meta["artists"], album=meta["name"], duration_ms=None, artwork=meta.get("artwork"), spotify_id=album_id, youtube_id=None, query=f"ytsearch:{meta['name']} {meta['artists']} album", source="html_scrape")], "html_scrape"
        return [], "failed"

    def _convert_sd_tracks(self, raw_tracks: List[Dict]) -> List[ResolvedTrack]:
        result = []
        for t in raw_tracks:
            name = t.get("title", t.get("name", "Unknown"))
            artists = t.get("artists", t.get("artist", "Unknown"))
            if isinstance(artists, list):
                artists = ", ".join(a.get("name", "") if isinstance(a, dict) else str(a) for a in artists)
            album = t.get("album")
            duration = t.get("duration")
            if duration and isinstance(duration, (int, float)) and duration < 10000:
                duration = int(duration * 1000)
            artwork = t.get("cover", t.get("album_cover", t.get("artwork", "")))
            tid = t.get("id", "")
            yt_id = t.get("youtube_id") or t.get("yt_id")
            query = f"https://youtube.com/watch?v={yt_id}" if yt_id else f"ytsearch:{name} {artists}"
            result.append(ResolvedTrack(name=name, artists=artists, album=album, duration_ms=duration, artwork=artwork, spotify_id=tid, youtube_id=yt_id, query=query, source="spotifydown"))
        return result

    def _track_to_resolved(self, track_data: Dict, track_id: str, source: str) -> ResolvedTrack:
        name = track_data.get("name", "Unknown")
        artists = self._artists_to_string(track_data.get("artists", []))
        album = track_data.get("album", {}).get("name") if isinstance(track_data.get("album"), dict) else None
        duration = track_data.get("duration_ms")
        artwork = None
        album_obj = track_data.get("album")
        if isinstance(album_obj, dict):
            images = album_obj.get("images", [])
            if images:
                artwork = images[0].get("url")
        query = self._build_search_query(track_data)
        return ResolvedTrack(name=name, artists=artists, album=album, duration_ms=duration, artwork=artwork, spotify_id=track_id, youtube_id=None, query=query, source=source)

    @staticmethod
    def _artists_to_string(artists) -> str:
        if isinstance(artists, list):
            names = []
            for a in artists:
                if isinstance(a, dict):
                    names.append(a.get("name", ""))
                elif isinstance(a, str):
                    names.append(a)
            return ", ".join(filter(None, names))
        return str(artists) if artists else "Unknown"

    @staticmethod
    def _build_search_query(track_data: Dict) -> str:
        title = track_data.get("name", "")
        artists = SpotifyResolver._artists_to_string(track_data.get("artists", []))
        query = f"{artists} - {title}".strip(" -")
        return f"ytsearch:{query}"

async def setup(bot):
    pass
