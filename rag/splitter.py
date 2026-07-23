"""
rag/splitter.py
Splits document text into overlapping chunks suitable for embedding.
Simple character-based splitter with sentence-aware boundaries - no
external dependency required.
"""
import re
from typing import List, Dict


def split_text(text: str, chunk_size: int = 800, overlap: int = 150) -> List[str]:
    """Split text into chunks of ~chunk_size characters with overlap,
    breaking on sentence/paragraph boundaries where possible."""
    text = re.sub(r"\n{2,}", "\n\n", text.strip())
    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Split into sentences/paragraphs first, then greedily pack into chunks.
    pieces = re.split(r"(?<=[.\n])\s+", text)
    chunks, current = [], ""
    for piece in pieces:
        if len(current) + len(piece) + 1 <= chunk_size:
            current = (current + " " + piece).strip()
        else:
            if current:
                chunks.append(current)
            # start new chunk, carrying overlap from end of previous chunk
            overlap_text = current[-overlap:] if current else ""
            current = (overlap_text + " " + piece).strip()
    if current:
        chunks.append(current)
    return chunks


def chunk_documents(documents: List[Dict], chunk_size: int = 800,
                     overlap: int = 150) -> List[Dict]:
    """Turn [{"source", "text"}] into [{"source", "chunk_id", "text"}]."""
    chunks = []
    for doc in documents:
        for i, chunk in enumerate(split_text(doc["text"], chunk_size, overlap)):
            chunks.append({
                "source": doc["source"],
                "chunk_id": f"{doc['source']}::{i}",
                "text": chunk,
            })
    return chunks
