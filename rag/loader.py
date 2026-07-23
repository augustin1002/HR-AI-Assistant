"""
rag/loader.py
Loads all policy documents (PDF or TXT) from the documents/ folder into
plain text, tagged with their source filename.
"""
from pathlib import Path
from typing import List, Dict

BASE_DIR = Path(__file__).resolve().parent.parent
DOCS_DIR = BASE_DIR / "documents"


def _load_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ImportError("Install pypdf to load PDF documents: pip install pypdf")
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def load_documents(docs_dir: Path = DOCS_DIR) -> List[Dict]:
    """Return a list of {"source": filename, "text": full_text} dicts."""
    documents = []
    for path in sorted(docs_dir.glob("*")):
        if path.suffix.lower() == ".pdf":
            text = _load_pdf(path)
        elif path.suffix.lower() in (".txt", ".md"):
            text = path.read_text(encoding="utf-8", errors="ignore")
        else:
            continue
        if text.strip():
            documents.append({"source": path.name, "text": text})
    return documents


if __name__ == "__main__":
    docs = load_documents()
    for d in docs:
        print(f"{d['source']}: {len(d['text'])} chars")
