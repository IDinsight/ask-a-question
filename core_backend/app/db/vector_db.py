from app.configs.app_config import QDRANT_API_KEY, QDRANT_URL, QDRANT_HOST, QDRANT_PORT

from qdrant_client import QdrantClient
from qdrant_client.models import VectorParams, Distance

_qdrant_client: QdrantClient | None = None


def get_qdrant_client() -> QdrantClient:
    """
    Return QdrantClient instance. If an instance already exists, return it.
    """
    global _qdrant_client
    if _qdrant_client is None:
        if QDRANT_URL and QDRANT_API_KEY:
            _qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
        elif QDRANT_HOST and QDRANT_PORT:
            _qdrant_client = QdrantClient(host=QDRANT_HOST, port=int(QDRANT_PORT))
        else:
            raise Exception("Unable to instantiate QdrantClient")

    return _qdrant_client


def create_qdrant_collection(collection_name: str, embeddings_dim: int) -> None:
    """
    Create a collection in Qdrant
    """
    qdrant_client = get_qdrant_client()
    result = qdrant_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(size=embeddings_dim, distance=Distance.COSINE),
    )

    if not result:
        raise Exception("Unable to create collection in Qdrant")
