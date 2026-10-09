"""Split page text into overlapping chunks that remember their page number."""
import re

from src.models import Chunk


def _clean(text: str) -> str:
    text = text.replace("\r", "\n").replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def chunk_pages(pages: list, size: int = 1200, overlap: int = 200) -> list:
    chunks = []
    cid = 0
    for page_no, raw in enumerate(pages, start=1):
        text = _clean(raw)
        if len(text) < 40:
            continue
        # split on blank lines or on lines ending with sentence punctuation
        parts = [p.strip() for p in re.split(r"\n\s*\n|(?<=[.;:])\n", text) if p.strip()]
        buf = ""
        for part in parts:
            if len(buf) + len(part) + 1 <= size:
                buf = f"{buf}\n{part}".strip()
                continue
            if buf:
                chunks.append(Chunk(cid, page_no, buf))
                cid += 1
            tail = buf[-overlap:] if (buf and overlap) else ""
            buf = f"{tail}\n{part}".strip()
            while len(buf) > size * 2:  # a single very long paragraph
                chunks.append(Chunk(cid, page_no, buf[:size]))
                cid += 1
                buf = buf[max(1, size - overlap):]
        if buf:
            chunks.append(Chunk(cid, page_no, buf))
            cid += 1
    return chunks
