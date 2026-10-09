from src.chunker import chunk_pages


def test_chunks_keep_page_numbers_and_skip_empty_pages():
    pages = ["", "A" * 30, ("Related party transactions are disclosed in Note 38. " * 60)]
    chunks = chunk_pages(pages, size=500, overlap=50)
    assert chunks, "expected chunks"
    assert all(c.page == 3 for c in chunks)
    assert all(len(c.text) <= 1100 for c in chunks)
    assert [c.id for c in chunks] == list(range(len(chunks)))
