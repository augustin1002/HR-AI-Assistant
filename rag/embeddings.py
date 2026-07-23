"""
rag/embeddings.py
Two interchangeable embedding backends:

1. "st"    - sentence-transformers (all-MiniLM-L6-v2) + FAISS. Best quality,
             requires internet access on first run to download the model.
2. "tfidf" - scikit-learn TF-IDF + cosine similarity. No downloads required,
             works fully offline. Used automatically as a fallback.

Set EMBEDDING_BACKEND=st|tfidf in .env to force a choice.
"""
import os
import pickle
from pathlib import Path
from typing import List, Tuple

import numpy as np

BASE_DIR = Path(__file__).resolve().parent.parent
STORE_DIR = BASE_DIR / "vectorstore"
STORE_DIR.mkdir(exist_ok=True)


class TfidfBackend:
    name = "tfidf"

    def __init__(self):
        from sklearn.feature_extraction.text import TfidfVectorizer
        self.vectorizer = TfidfVectorizer(stop_words="english")
        self.matrix = None
        self.texts: List[str] = []

    def build(self, texts: List[str]):
        self.texts = texts
        self.matrix = self.vectorizer.fit_transform(texts)

    def search(self, query: str, k: int = 4) -> List[Tuple[int, float]]:
        from sklearn.metrics.pairwise import cosine_similarity
        q_vec = self.vectorizer.transform([query])
        sims = cosine_similarity(q_vec, self.matrix)[0]
        top_idx = np.argsort(sims)[::-1][:k]
        return [(int(i), float(sims[i])) for i in top_idx]

    def save(self, path: Path):
        with open(path, "wb") as f:
            pickle.dump({"vectorizer": self.vectorizer, "matrix": self.matrix,
                         "texts": self.texts}, f)

    def load(self, path: Path):
        with open(path, "rb") as f:
            data = pickle.load(f)
        self.vectorizer = data["vectorizer"]
        self.matrix = data["matrix"]
        self.texts = data["texts"]


class SentenceTransformerBackend:
    name = "st"

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        import faiss
        self.model = SentenceTransformer(model_name)
        self.faiss = faiss
        self.index = None
        self.texts: List[str] = []

    def build(self, texts: List[str]):
        self.texts = texts
        vecs = self.model.encode(texts, normalize_embeddings=True)
        vecs = np.asarray(vecs, dtype="float32")
        self.index = self.faiss.IndexFlatIP(vecs.shape[1])
        self.index.add(vecs)

    def search(self, query: str, k: int = 4) -> List[Tuple[int, float]]:
        q_vec = self.model.encode([query], normalize_embeddings=True)
        q_vec = np.asarray(q_vec, dtype="float32")
        scores, idx = self.index.search(q_vec, k)
        return [(int(i), float(s)) for i, s in zip(idx[0], scores[0]) if i != -1]

    def save(self, path: Path):
        self.faiss.write_index(self.index, str(path.with_suffix(".faiss")))
        with open(path.with_suffix(".texts.pkl"), "wb") as f:
            pickle.dump(self.texts, f)

    def load(self, path: Path):
        self.index = self.faiss.read_index(str(path.with_suffix(".faiss")))
        with open(path.with_suffix(".texts.pkl"), "rb") as f:
            self.texts = pickle.load(f)


def get_backend():
    """Pick an embedding backend based on .env config, falling back
    gracefully to TF-IDF if sentence-transformers/FAISS aren't installed."""
    choice = os.getenv("EMBEDDING_BACKEND", "auto").lower()
    if choice == "tfidf":
        return TfidfBackend()
    try:
        if choice in ("auto", "st"):
            return SentenceTransformerBackend()
    except ImportError:
        pass
    return TfidfBackend()
