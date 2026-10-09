from src.verify import quote_in_text

PAGE = """Emphasis of Matter: We draw attention to Note 45 regarding contingent
liabilities of Rs 1,250 crore towards disputed tax demands. Our opinion is not modified."""


def test_exact_quote_found():
    assert quote_in_text("We draw attention to Note 45 regarding contingent liabilities", PAGE)


def test_quote_with_line_break_and_case_differences():
    assert quote_in_text("contingent LIABILITIES of Rs 1,250 crore towards disputed tax demands", PAGE)


def test_fabricated_quote_rejected():
    assert not quote_in_text("The auditor expressed an adverse opinion on the consolidated statements", PAGE)


def test_empty_quote_rejected():
    assert not quote_in_text("", PAGE)
