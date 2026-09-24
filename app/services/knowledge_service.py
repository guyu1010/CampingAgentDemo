import logging

from openai import AsyncOpenAI

from app.core.config import settings
from app.core.qdrant import get_qdrant_client

COLLECTION_NAME = "camping_knowledge"
TOP_K = 5

logger = logging.getLogger(__name__)

class KnowledgeService:
    def __init__(self, client: AsyncOpenAI):
        self.client = client
        self.qdrant = get_qdrant_client()

    async def search(self, query: str) -> list[dict]:
        embedding = await self._embed(query)

        results = self.qdrant.query_points(
            collection_name=COLLECTION_NAME,
            query=embedding,
            limit=TOP_K,
        ).points

        logger.info("知識庫檢索「%s」找到: %s", query, [(r.payload["section_title"], round(r.score, 3)) for r in results])

        output = []
        for r in results:
            output.append({
                "title": r.payload["title"],
                "section_title": r.payload["section_title"],
                "content": r.payload["content"],
            })
        return output

    async def _embed(self, text: str) -> list[float]:
        resp = await self.client.embeddings.create(model=settings.openai_embedding_model, input=[text])
        return resp.data[0].embedding
