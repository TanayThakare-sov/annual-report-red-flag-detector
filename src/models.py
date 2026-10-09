from dataclasses import dataclass


@dataclass
class Chunk:
    id: int
    page: int  # 1-based PDF page index
    text: str


@dataclass
class Finding:
    category: str
    title: str
    severity: str  # High | Medium | Low
    summary: str
    quote: str
    page: int
    why_it_matters: str = ""
    verified: bool = False  # True if the quote was found in the cited PDF page
