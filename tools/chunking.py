"""Split the policy docs into small chunks for embedding (stage 5).

Why chunk? An embedding is one vector per piece of text. Embed a whole document and
its vector is a blur of every topic in it (meals, hotels, flights...). Embed one
paragraph or bullet and the vector means one thing, so a query can match it precisely.

Each chunk is prefixed with its document title ("Expense Policy: Meals while
traveling...") so it keeps some context once it's cut out of the document.
"""

import hashlib
import re
from pathlib import Path

DOCS_DIR = Path(__file__).parent.parent / "data" / "docs"


def chunk_document(name: str, text: str) -> list[dict]:
    lines = text.splitlines()
    title = next((ln.lstrip("# ").strip() for ln in lines if ln.startswith("#")), name)
    chunks = []

    blocks = re.split(r"\n\s*\n", text.strip())          # paragraphs = blank-line separated
    for block in blocks:
        block = block.strip()
        if not block or block.startswith("#"):
            continue
        items = [b.strip() for b in re.split(r"\n(?=\s*(?:[-*]|\d+\.)\s)", block)]
        if len(items) > 1 or re.match(r"\s*(?:[-*]|\d+\.)\s", block):
            pieces = [re.sub(r"^\s*(?:[-*]|\d+\.)\s*", "", it) for it in items]   # one chunk per bullet
        else:
            pieces = [" ".join(block.split())]                                  # one chunk per paragraph
        for piece in pieces:
            body = " ".join(piece.split())
            chunks.append({
                "id": f"{name}#{len(chunks)}",
                "doc": name,
                "heading": title,
                "text": f"{title}: {body}",
                "hash": hashlib.sha256(f"{title}: {body}".encode()).hexdigest()[:16],
            })
    return chunks


def load_chunks() -> list[dict]:
    chunks = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        chunks += chunk_document(path.name, path.read_text(encoding="utf-8"))
    return chunks
