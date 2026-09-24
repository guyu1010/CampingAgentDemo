from qdrant_client.models import Distance, VectorParams

from app.core.qdrant import get_qdrant_client

COLLECTION_NAME = "camping_knowledge"
EMBEDDING_SIZE = 1536

def main():
    client = get_qdrant_client()

    if client.collection_exists(COLLECTION_NAME):
        print(f"collection「{COLLECTION_NAME}」已經存在,不重複建立")
        return

    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=EMBEDDING_SIZE, distance=Distance.COSINE),
    )
    print(f"已建立 collection「{COLLECTION_NAME}」(向量維度 {EMBEDDING_SIZE}, 使用 cosine 相似度)")


if __name__ == "__main__":
    main()
