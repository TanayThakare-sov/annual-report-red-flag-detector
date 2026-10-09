"""Check that a quote returned by the LLM really exists in the cited page."""
import re


def normalize(s: str) -> str:
    s = re.sub(r"[^\w]+", " ", s.lower())
    return re.sub(r"\s+", " ", s).strip()


def quote_in_text(quote: str, text: str, threshold: float = 0.8, n: int = 4) -> bool:
    """True if the quote appears in `text` (exactly, or >= threshold of its n-word shingles)."""
    q, t = normalize(quote), normalize(text)
    if not q or not t:
        return False
    if q in t:
        return True
    words = q.split()
    if len(words) < n:
        return False
    shingles = [" ".join(words[i : i + n]) for i in range(len(words) - n + 1)]
    hits = sum(1 for s in shingles if s in t)
    return hits / len(shingles) >= threshold
