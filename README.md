# 🚩 Annual Report Red-Flag Detector

A RAG agent that reads an **Indian annual report (PDF)** and surfaces the risk signals that ratio screeners miss because they live in the *text*: auditor remarks, related-party transactions, contingent liabilities, accounting-policy changes and unusual notes to accounts. Every finding carries a **verbatim quote and a page citation**, and the quote is programmatically checked against the cited page.

## Quick start (VS Code)

```bash
# 1. open this folder in VS Code, then open the terminal
python -m venv .venv
.venv\Scripts\activate          # Windows   (macOS/Linux: source .venv/bin/activate)
pip install -r requirements.txt

# 2. add an API key (Anthropic, OpenAI or Gemini) - or paste it in the app sidebar
copy .env.example .env          # macOS/Linux: cp .env.example .env

# 3. run
streamlit run app.py
```

Then either copy PDFs into `data/reports/` and pick one from the dropdown, or choose 'Upload a PDF'. Click **Run red-flag analysis** to get the results. Download annual reports from a company's investor-relations page or BSE/NSE filings. The first run embeds the report locally (1-2 minutes for ~300 pages) and caches it in `data/cache/`, so re-opening the same PDF is instant. Gemini's free tier is the cheapest way to try it.

Run tests: `pytest`

## What it does

| Tab | Purpose |
|---|---|
| Summary | Risk score (0-100), counts, LLM executive summary |
| Red flags | Findings grouped by category, severity, quote, page, "show PDF page" viewer |
| Ratios | LLM-extracted financials (editable) -> interest coverage, D/E, CFO/PAT, receivable days, etc. |
| Ask the report | Chat Q&A with page citations |
| Export | Markdown / JSON report |

## Architecture

```
PDF -> PyMuPDF (page text) -> chunker (keeps page no.) -> MiniLM embeddings -> FAISS
                                                                    |
                    hybrid retrieval (semantic + keyword, reciprocal-rank fusion)
                                                                    |
 for each of 6 red-flag categories:  RETRIEVE -> EXTRACT (LLM, JSON) -> REFLECT (re-query if empty) -> VERIFY (quote in page?)
                                                                    |
              financial extraction -> ratio engine -> score -> executive summary -> Streamlit UI
```

```
app.py                Streamlit UI
src/config.py         paths, model names, chunk sizes
src/pdf_loader.py     PDF text, page rendering, scanned-PDF check
src/chunker.py        page-aware chunking
src/vector_store.py   embeddings + FAISS + hybrid search + disk cache
src/llm.py            Anthropic / OpenAI / Gemini wrapper, JSON parsing
src/red_flags.py      category definitions (queries + keywords)
src/agent.py          the agent loop, financial extraction, summary, Q&A
src/verify.py         quote-in-page check (anti-hallucination)
src/ratios.py         ratio engine with red/watch thresholds
src/scoring.py        transparent heuristic score
src/report.py         Markdown / JSON export
tests/                verify, ratios/scoring, chunker tests
```

## Design choices worth explaining in an interview

- **Citation verification.** LLM quotes are checked against the PDF page (exact or 4-word-shingle match). If the page number is wrong but the quote exists in another retrieved page, it is corrected; if the quote is nowhere, the finding is shown as *unverified* and excluded from the score.
- **Hybrid retrieval.** Accounting jargon ("emphasis of matter", "claims not acknowledged as debt") is matched well by keywords, while paraphrased disclosures need embeddings. Reciprocal-rank fusion combines both.
- **Reflection step.** If a category yields nothing, the agent asks the LLM for alternative queries and searches again before concluding "clean".
- **Numbers back up text.** Ratio flags (e.g. receivables growing much faster than revenue, CFO well below PAT) corroborate text findings. Numbers are editable because LLM extraction from PDF tables can be wrong.
- **Provider-agnostic.** One `LLM` class covers Claude, OpenAI and Gemini.

## Limitations (be upfront about these)

- Scanned PDFs need OCR first. Complex multi-column tables can extract imperfectly; always check the ratio inputs.
- Retrieval is top-k per category, so very long reports may have missed passages. Raise the slider for more coverage.
- Severity and the score are heuristics, not investment advice. Treat every finding as a lead to verify.
- The page number cited is the **PDF page index**, which may differ from the page number printed on the page.

## Ideas to extend

- Compare two years of the same company and flag *new* red flags.
- Add OCR (e.g. `pytesseract`) for scanned reports.
- Turn each category into a LangGraph node, or expose the retriever as an MCP tool.
- Add an evaluation set: annual reports of companies with known audit qualifications, then measure recall of the detector.
- Deploy on Streamlit Community Cloud or Hugging Face Spaces and link it from your resume.

## Resume bullets (edit to match what you actually built and tested)

- Built a RAG-based agent in Python (FAISS, sentence-transformers, Claude/Gemini APIs) that scans Indian annual reports for six categories of red flags and returns findings with page-level citations.
- Added a verification step that checks each LLM quote against the source PDF page to catch hallucinated citations, and a hybrid keyword + semantic retriever with a query-reformulation fallback.
- Combined text findings with ratio analysis (interest coverage, CFO/PAT, receivables vs revenue growth) and shipped a Streamlit app with a cited-page viewer, Q&A and exportable reports.
