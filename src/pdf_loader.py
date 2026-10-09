"""PDF helpers built on PyMuPDF."""
import hashlib


def file_hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def load_pdf_pages(data: bytes) -> list:
    """Return the text of every page (index 0 = PDF page 1)."""
    import fitz  # PyMuPDF

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        return [page.get_text("text") for page in doc]
    finally:
        doc.close()


def looks_scanned(pages: list) -> bool:
    """Heuristic: almost no extractable text means a scanned (image-only) PDF."""
    if not pages:
        return True
    avg = sum(len(p) for p in pages) / len(pages)
    return avg < 200


def render_page_png(data: bytes, page: int, zoom: float = 1.6) -> bytes:
    """Render a 1-based page number to PNG bytes (used to show cited pages)."""
    import fitz

    doc = fitz.open(stream=data, filetype="pdf")
    try:
        page = max(1, min(page, len(doc)))
        pix = doc[page - 1].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")
    finally:
        doc.close()
