import uuid
from pathlib import Path

import yaml
from openai import OpenAI
from qdrant_client.models import (
    FieldCondition,
    Filter,
    MatchValue,
    PointStruct,
)

from app.core.config import settings
from app.core.qdrant import get_qdrant_client

DOCS_DIR = Path(__file__).resolve().parent.parent / "precautions"
COLLECTION_NAME = "camping_knowledge"

# 固定的命名空間，讓同一個 doc_id + 段落順序每次都算出同一組 UUID
POINT_ID_NAMESPACE = uuid.UUID("6f1f9b7e-2b8b-4b6b-9b9e-6b6b6b6b6b6b")


def parse_markdown(path: Path) -> tuple[dict, str]:
    """把檔案切成「YAML frontmatter」跟「內文」兩塊。"""
    text = path.read_text(encoding="utf-8")

    if not text.startswith("---"):
        raise ValueError(f"{path.name} 缺少 --- 開頭的 frontmatter")

    _, frontmatter_raw, body = text.split("---", 2)
    metadata = yaml.safe_load(frontmatter_raw)
    return metadata, body.strip()


def split_sections(body: str) -> list[tuple[str, str]]:
    """依 # 或 ## 標題切段，回傳 [(段落標題, 段落內容), ...]。
    """
    sections = []
    current_title = None
    current_lines = []

    def flush():
        content = "\n".join(current_lines).strip()
        if content:
            sections.append((current_title, content))

    for line in body.split("\n"):
        is_top_heading = line.startswith(("# ", "## "))
        if is_top_heading:
            flush()
            current_title = line.lstrip("#").strip()
            current_lines = []
        else:
            current_lines.append(line)

    flush()
    return sections


def embed_texts(client: OpenAI, texts: list[str]) -> list[list[float]]:
    resp = client.embeddings.create(model=settings.openai_embedding_model, input=texts)
    return [item.embedding for item in resp.data]


def delete_existing_points(qdrant, doc_id: str):
    """重新匯入同一份文件前,先刪掉它舊的 chunk,避免留下過期資料。"""
    qdrant.delete(
        collection_name=COLLECTION_NAME,
        points_selector=Filter(must=[FieldCondition(key="doc_id", match=MatchValue(value=doc_id))]),
    )


def main():
    openai_client = OpenAI(api_key=settings.openai_api_key)
    qdrant = get_qdrant_client()

    total_chunks = 0

    for path in sorted(DOCS_DIR.glob("*.md")):
        metadata, body = parse_markdown(path)
        doc_id = metadata["doc_id"] if "doc_id" in metadata else metadata["id"]
        sections = split_sections(body)

        delete_existing_points(qdrant, doc_id)

        # 每個 chunk 前面加上文件標題，讓 embedding 保留一點上下文
        texts_to_embed = [f"{metadata['title']} - {section_title}\n{content}" for section_title, content in sections]
        vectors = embed_texts(openai_client, texts_to_embed)

        points = []
        for i, ((section_title, content), vector) in enumerate(zip(sections, vectors)):
            point_id = str(uuid.uuid5(POINT_ID_NAMESPACE, f"{doc_id}#{i}"))
            points.append(PointStruct(
                id=point_id,
                vector=vector,
                payload={
                    "doc_id": doc_id,
                    "title": metadata["title"],
                    "category": metadata.get("category"),
                    "tags": metadata.get("tags", []),
                    "section_title": section_title,
                    "content": content,
                    "source_file": path.name,
                },
            ))

        qdrant.upsert(collection_name=COLLECTION_NAME, points=points)
        print(f"{path.name}：匯入 {len(points)} 個段落")
        total_chunks += len(points)

    print(f"完成，共匯入 {total_chunks} 個段落")


if __name__ == "__main__":
    main()
