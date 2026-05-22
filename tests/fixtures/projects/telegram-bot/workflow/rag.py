"""RAG pipeline — embed → store in ChromaDB → retrieve."""

import chromadb
from openai import OpenAI

_client = chromadb.PersistentClient(path="./chroma_data")
_collection = _client.get_or_create_collection("kb")
_openai = OpenAI()


def embed(text: str) -> list[float]:
    resp = _openai.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


def retrieve(query: str, k: int = 5) -> list[str]:
    qvec = embed(query)
    res = _collection.query(query_embeddings=[qvec], n_results=k)
    return res["documents"][0]
