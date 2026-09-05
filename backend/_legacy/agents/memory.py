"""
Memory Agent - ChromaDB 向量记忆
"""
from typing import Dict, Any, List, Optional
from langchain_openai import OpenAIEmbeddings
import chromadb
from chromadb.config import Settings
from config import settings


def _get_embeddings():
    return OpenAIEmbeddings(
        model=settings.EMBEDDING_MODEL,
        openai_api_key=settings.DEEPSEEK_API_KEY,
        openai_api_base=settings.DEEPSEEK_BASE_URL,
    )


def _get_client():
    return chromadb.Client(Settings(
        anonymized_telemetry=False,
        allow_reset=True,
        persist_directory=settings.CHROMA_PERSIST_DIR,
    ))


def store_memory(conversation_id: int, text: str, metadata: Optional[Dict] = None) -> str:
    """存入向量记忆"""
    try:
        client = _get_client()
        collection = client.get_or_create_collection(
            name=f"conv_{conversation_id}",
            metadata={"hnsw:space": "cosine"},
        )
        emb = _get_embeddings()
        vector = emb.embed_query(text)
        import uuid
        doc_id = str(uuid.uuid4())
        collection.add(
            ids=[doc_id],
            documents=[text],
            embeddings=[vector],
            metadatas=[metadata or {"conversation_id": conversation_id}],
        )
        return doc_id
    except Exception:
        return ""


def search_memory(conversation_id: int, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
    """搜索向量记忆"""
    try:
        client = _get_client()
        collection = client.get_or_create_collection(
            name=f"conv_{conversation_id}",
            metadata={"hnsw:space": "cosine"},
        )
        emb = _get_embeddings()
        vector = emb.embed_query(query)
        results = collection.query(
            query_embeddings=[vector],
            n_results=top_k,
        )
        docs = results.get("documents", [[]])[0]
        metas = results.get("metadatas", [[]])[0]
        dists = results.get("distances", [[]])[0]
        return [
            {"content": docs[i], "metadata": metas[i], "distance": dists[i]}
            for i in range(len(docs))
        ]
    except Exception:
        return []
