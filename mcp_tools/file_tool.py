"""mcp_tools/file_tool.py - list / keyword-search the policy document set."""
from pathlib import Path
from rag.loader import DOCS_DIR, load_documents


def list_documents() -> str:
    files = [p.name for p in sorted(DOCS_DIR.glob("*")) if p.suffix.lower() in (".pdf", ".txt", ".md")]
    return "\n".join(files) if files else "No documents found."


def search_documents(keyword: str) -> str:
    """Plain keyword search across raw document text (separate from the
    semantic RAG retriever) - useful for exact-term lookups like policy
    version numbers or specific defined terms."""
    hits = []
    for doc in load_documents():
        if keyword.lower() in doc["text"].lower():
            idx = doc["text"].lower().find(keyword.lower())
            snippet = doc["text"][max(0, idx - 80): idx + 120].replace("\n", " ")
            hits.append(f"{doc['source']}: ...{snippet}...")
    return "\n".join(hits) if hits else f"No mention of '{keyword}' found in documents."
