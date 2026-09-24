from urllib.parse import urlparse

from qdrant_client import QdrantClient

from app.core.config import settings


def get_qdrant_client() -> QdrantClient:
    """建立 Qdrant client。

    本機開發用 Railway 對外的 https 網址(沒有明確 port,預設要用 443),
    正式環境用 Railway 內部網址(網址裡已經帶 port,例如 :6333),
    所以 port 要照網址本身判斷,不能寫死。
    """
    parsed = urlparse(settings.qdrant_url)
    port = parsed.port or (443 if parsed.scheme == "https" else 80)

    return QdrantClient(url=settings.qdrant_url, api_key=settings.qdrant_api_key, port=port)
