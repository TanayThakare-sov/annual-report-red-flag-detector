"""FAISS-backed index over report chunks with hybrid (semantic + keyword) retrieval."""
import pickle
from pathlib import Path

import numpy as np

from src import config
from src.chunker import chunk_pages
from src.models import Chunk

_model = None


def _get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer

        _model = SentenceTransformer(config.EMBED_MODEL)
    return _model


def embed(texts: list, progress=None, batch: int = 64) -> np.ndarray:
    model = _get_model()
    out = []
    for i in range(0, len(texts), batch):
        out.append(model.encode(texts[i : i + batch], normalize_embeddings=True, show_progress_bar=False))
        if progress:
            progress(min(1.0, (i + batch) / len(texts)))
    return np.vstack(out).astype("float32")


class ReportIndex:
    def __init__(self, chunks: list, pages: list, embeddings: np.ndarray):
        import faiss

        self.chunks = chunks
        self.pages = pages
        self.embeddings = embeddings
        self.faiss = faiss.IndexFlatIP(embeddings.shape[1])
        self.faiss.add(embeddings)
        self._lower = [c.text.lower() for c in chunks]

    # ---------- build / persist ----------
    @classmethod
    def build(cls, pages: list, progress=None) -> "ReportIndex":
        chunks = chunk_pages(pages, config.CHUNK_CHARS, config.CHUNK_OVERLAP)
        if not chunks:
            raise ValueError(
                "No extractable text found. The PDF may be a scanned image; run OCR on it first."
            )
        emb = embed([c.text for c in chunks], progress)
        return cls(chunks, pages, emb)

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / "emb.npy", self.embeddings)
        with open(folder / "chunks.pkl", "wb") as f:
            pickle.dump({"chunks": self.chunks, "pages": self.pages}, f)

    @classmethod
    def load(cls, folder: Path) -> "ReportIndex":
        with open(folder / "chunks.pkl", "rb") as f:
            blob = pickle.load(f)
        return cls(blob["chunks"], blob["pages"], np.load(folder / "emb.npy"))

    # ---------- retrieval ----------
    def _semantic(self, query: str, n: int) -> list:
        qv = embed([query])
        _, idx = self.faiss.search(qv, min(n, len(self.chunks)))
        return [int(i) for i in idx[0] if i != -1]

    def _keyword(self, keywords: list, n: int) -> list:
        kws = [k.lower() for k in keywords]
        scored = []
        for i, text in enumerate(self._lower):
            matched = [k for k in kws if k in text]
            if matched:
                hits = sum(text.count(k) for k in matched)
                scored.append((len(matched) * 3 + min(hits, 5), i))
        scored.sort(reverse=True)
        return [i for _, i in scored[:n]]

    def hybrid_search(self, queries: list, keywords: list, k: int = 8, exclude=None) -> list:
        """Reciprocal-rank fusion of one semantic ranking per query plus a keyword ranking."""
        rankings = [self._semantic(q, 30) for q in queries]
        if keywords:
            rankings.append(self._keyword(keywords, 30))
        fused = {}
        for ranking in rankings:
            for rank, i in enumerate(ranking):
                fused[i] = fused.get(i, 0.0) + 1.0 / (60 + rank)
        ids = sorted(fused, key=fused.get, reverse=True)
        if exclude:
            ids = [i for i in ids if self.chunks[i].id not in exclude]
        return [self.chunks[i] for i in ids[:k]]
