import os

def _get_lavalink_nodes():
    url = os.getenv("LAVALINK_URL", "").strip()
    password = os.getenv("LAVALINK_PASSWORD", "").strip()

    if url and password:
        if not url.startswith("http"):
            url = "https://" + url
        return [{"uri": url.rstrip("/"), "password": password}]

    host = os.getenv("lavalink_host", "127.0.0.1")
    port = os.getenv("lavalink_port", "2333")
    password = os.getenv("lavalink_password", "youshallnotpass")
    secure = os.getenv("lavalink_secure", "false").lower() == "true"

    scheme = "https" if secure else "http"
    uri = f"{scheme}://{host}:{port}"

    return [{"uri": uri, "password": password}]

LAVALINK_NODES = _get_lavalink_nodes()