"""
rag/retriever.py
Builds (or loads a cached) vector index over the policy documents and
exposes a simple retrieve(query) -> List[chunk dict] interface.
"""
from pathlib import Path
from typing import List, Dict

from rag.loader import load_documents, DOCS_DIR
from rag.splitter import chunk_documents
from rag.embeddings import get_backend, STORE_DIR

_INDEX_PATH = STORE_DIR / "index"


class Retriever:
    def __init__(self):
        self.backend = get_backend()
        self.chunks: List[Dict] = []
        self._load_or_build()

    def _load_or_build(self):
        meta_path = STORE_DIR / "chunks.pkl"
        cache_ok = meta_path.exists()
        try:
            if cache_ok:
                import pickle
                with open(meta_path, "rb") as f:
                    self.chunks = pickle.load(f)
                self.backend.load(_INDEX_PATH)
                return
        except Exception:
            pass  # fall through to rebuild
        self.build_index()

    def build_index(self, docs_dir: Path = DOCS_DIR):
        documents = load_documents(docs_dir)
        self.chunks = chunk_documents(documents)
        texts = [c["text"] for c in self.chunks]
        if not texts:
            raise RuntimeError(f"No documents found in {docs_dir}")
        self.backend.build(texts)
        self.backend.save(_INDEX_PATH)
        import pickle
        with open(STORE_DIR / "chunks.pkl", "wb") as f:
            pickle.dump(self.chunks, f)

    def retrieve(self, query: str, k: int = 4, min_score: float = 0.05) -> List[Dict]:
        results = self.backend.search(query, k=k)
        out = []
        for idx, score in results:
            if score < min_score:
                continue
            chunk = dict(self.chunks[idx])
            chunk["score"] = score
            out.append(chunk)
        return out


_retriever_singleton = None


def get_retriever() -> Retriever:
    global _retriever_singleton
    if _retriever_singleton is None:
        _retriever_singleton = Retriever()
    return _retriever_singleton
