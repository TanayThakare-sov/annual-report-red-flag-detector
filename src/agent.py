"""The red-flag agent.

Per category the agent runs a small loop:
  1. RETRIEVE  hybrid (semantic + keyword) search over the report
  2. EXTRACT   LLM reads only the retrieved excerpts and returns findings with verbatim quotes + pages
  3. REFLECT   if nothing was found, the LLM writes new search queries and the agent retrieves again
  4. VERIFY    every quote is checked against the cited PDF page; unverifiable findings are flagged
Then it extracts key financials (for ratios), computes a score and writes an executive summary.
"""
import json
from dataclasses import dataclass, field

from src.llm import LLM
from src.models import Chunk, Finding
from src.ratios import FIELD_KEYS, compute_ratios
from src.red_flags import CATEGORIES, METRIC_KEYWORDS, METRIC_QUERIES, Category
from src.scoring import compute_score
from src.vector_store import ReportIndex
from src.verify import normalize, quote_in_text

EXTRACT_SYSTEM = """You are a forensic financial analyst reviewing an Indian company's annual report (Ind AS, Companies Act 2013, SEBI LODR).
Rules:
- Use ONLY the excerpts provided. Never use outside knowledge about the company.
- Every finding needs a verbatim quote (max 300 characters) copied exactly from ONE excerpt, and the page number from that excerpt's [Page N] header.
- Report only genuine risk signals, not routine boilerplate. A clean unmodified audit opinion is NOT a finding. A standard statement that no fraud was noticed is NOT a finding.
- Severity: High = could materially affect solvency, reliability of the financials or minority shareholders (qualified/adverse opinion, going concern doubt, large RPT loans to promoter entities, fraud, loan defaults). Medium = needs investor follow-up. Low = minor or disclosure-quality issue.
- If the excerpts contain no real signal for this category, return {"findings": []}.
Return ONLY JSON: {"findings":[{"title":str,"severity":"High|Medium|Low","summary":str,"quote":str,"page":int,"why_it_matters":str}]}"""

METRICS_SYSTEM = """You extract key financial figures from excerpts of an Indian annual report.
Rules:
- Use ONLY the excerpts. If a figure is not present, use null. Never guess.
- Prefer CONSOLIDATED statements when both consolidated and standalone appear; set "basis" accordingly.
- Report numbers exactly in the unit used by the report (do NOT convert). Set "unit" (e.g. "Rs crore", "Rs lakh", "Rs million").
- Remove commas; numbers in brackets are negative.
- total_debt = current + non-current borrowings (exclude lease liabilities and trade payables).
Return ONLY JSON:
{"basis":"consolidated|standalone|unknown","unit":str,"current_label":str,"previous_label":str,
 "current":{"revenue":num|null,"pbt":num|null,"pat":num|null,"finance_costs":num|null,"total_debt":num|null,"total_equity":num|null,"current_assets":num|null,"current_liabilities":num|null,"trade_receivables":num|null,"inventories":num|null,"cfo":num|null},
 "previous":{same keys},
 "pages":[int]}"""

ASK_SYSTEM = """You answer questions about an Indian company's annual report using ONLY the excerpts provided.
Cite the page for every claim like [p. 123]. If the excerpts do not contain the answer, say so plainly. Be concise."""


@dataclass
class AnalysisResult:
    company: str = ""
    findings: list = field(default_factory=list)
    metrics: dict = None
    ratios: list = field(default_factory=list)
    summary: str = ""
    score: int = 0
    band: str = "Low"
    pages_total: int = 0
    notes: list = field(default_factory=list)


def _format_chunks(chunks: list) -> str:
    return "\n\n".join(f"[Page {c.page}]\n{c.text}" for c in chunks)


class RedFlagAgent:
    def __init__(self, index: ReportIndex, llm: LLM, top_k: int = 10):
        self.index = index
        self.llm = llm
        self.top_k = top_k

    # ---------- main entry ----------
    def analyze(self, company: str = "", progress=None) -> AnalysisResult:
        res = AnalysisResult(company=company, pages_total=len(self.index.pages))
        total_steps = len(CATEGORIES) + 2
        step = 0

        def tick(msg):
            nonlocal step
            step += 1
            if progress:
                progress(step / total_steps, msg)

        for cat in CATEGORIES:
            try:
                res.findings.extend(self._scan_category(cat))
            except Exception as e:
                res.notes.append(f"{cat.label}: scan failed ({e})")
            tick(f"Scanned: {cat.label}")

        res.findings = self._dedupe(res.findings)
        order = {"High": 0, "Medium": 1, "Low": 2}
        res.findings.sort(key=lambda f: (not f.verified, order.get(f.severity, 3)))

        try:
            res.metrics = self.extract_metrics()
            res.ratios = compute_ratios(res.metrics.get("current"), res.metrics.get("previous"))
        except Exception as e:
            res.notes.append(f"Financial extraction failed ({e}). You can type the numbers in manually.")
            res.metrics = {"basis": "unknown", "unit": "", "current_label": "Current", "previous_label": "Previous",
                           "current": {}, "previous": {}, "pages": []}
        tick("Extracted key financials")

        res.score, res.band = compute_score(res.findings, res.ratios)
        try:
            res.summary = self._summarize(res)
        except Exception as e:
            res.notes.append(f"Summary failed ({e})")
        tick("Wrote summary")
        return res

    # ---------- per-category loop ----------
    def _scan_category(self, cat: Category) -> list:
        chunks = self.index.hybrid_search(cat.queries, cat.keywords, k=self.top_k)
        findings = self._extract(cat, chunks)
        if not findings:  # REFLECT: try again with new queries
            seen = {c.id for c in chunks}
            new_queries = self._reformulate(cat)
            if new_queries:
                more = self.index.hybrid_search(new_queries, cat.keywords, k=self.top_k, exclude=seen)
                if more:
                    chunks = chunks + more
                    findings = self._extract(cat, more)
        return self._verify(findings, chunks)

    def _extract(self, cat: Category, chunks: list) -> list:
        if not chunks:
            return []
        user = (
            f"CATEGORY: {cat.label}\nWHAT TO LOOK FOR: {cat.description}\n\n"
            f"EXCERPTS:\n{_format_chunks(chunks)}"
        )
        data = self.llm.complete_json(EXTRACT_SYSTEM, user, max_tokens=3000)
        out = []
        for item in data.get("findings", []) or []:
            try:
                sev = str(item.get("severity", "Medium")).capitalize()
                if sev not in ("High", "Medium", "Low"):
                    sev = "Medium"
                out.append(
                    Finding(
                        category=cat.label,
                        title=str(item["title"]).strip(),
                        severity=sev,
                        summary=str(item.get("summary", "")).strip(),
                        quote=str(item.get("quote", "")).strip(),
                        page=int(item.get("page", 0)),
                        why_it_matters=str(item.get("why_it_matters", "")).strip(),
                    )
                )
            except (KeyError, ValueError, TypeError):
                continue
        return out

    def _reformulate(self, cat: Category) -> list:
        try:
            data = self.llm.complete_json(
                "You write short search queries for semantic search over an annual report.",
                f"Topic: {cat.label} - {cat.description}\nQueries already tried: {cat.queries}\n"
                'Write 3 different short queries using alternative wording. Return JSON {"queries":[...]}',
                max_tokens=400,
            )
            return [str(q) for q in data.get("queries", [])][:3]
        except Exception:
            return []

    def _verify(self, findings: list, chunks: list) -> list:
        retrieved_pages = []
        for c in chunks:
            if c.page not in retrieved_pages:
                retrieved_pages.append(c.page)
        for f in findings:
            candidates = [f.page] + [p for p in retrieved_pages if p != f.page]
            for p in candidates:
                if 1 <= p <= len(self.index.pages) and quote_in_text(f.quote, self.index.pages[p - 1]):
                    f.page, f.verified = p, True
                    break
        return findings

    @staticmethod
    def _dedupe(findings: list) -> list:
        seen, out = set(), []
        for f in findings:
            key = (f.page, normalize(f.quote)[:80])
            if key in seen:
                continue
            seen.add(key)
            out.append(f)
        return out

    # ---------- financials ----------
    def extract_metrics(self) -> dict:
        chunks = self.index.hybrid_search(METRIC_QUERIES, METRIC_KEYWORDS, k=14)
        data = self.llm.complete_json(METRICS_SYSTEM, f"EXCERPTS:\n{_format_chunks(chunks)}", max_tokens=1500)
        for period in ("current", "previous"):
            block = data.get(period) or {}
            data[period] = {k: block.get(k) for k in FIELD_KEYS}
        data.setdefault("basis", "unknown")
        data.setdefault("unit", "")
        data.setdefault("current_label", "Current")
        data.setdefault("previous_label", "Previous")
        data.setdefault("pages", [])
        return data

    # ---------- summary + Q&A ----------
    def _summarize(self, res: AnalysisResult) -> str:
        verified = [
            {"category": f.category, "title": f.title, "severity": f.severity, "page": f.page, "summary": f.summary}
            for f in res.findings if f.verified
        ]
        flagged = [{"ratio": r.name, "value": r.display, "flag": r.flag} for r in res.ratios if r.flag]
        user = (
            f"Company: {res.company or 'unknown'}\n"
            f"Verified findings: {json.dumps(verified)}\nRatio flags: {json.dumps(flagged)}\n\n"
            "Write a 120-180 word executive risk summary for an investor: the top 3 concerns (cite pages like [p. 45]), "
            "then 2-3 specific things to check next. Neutral tone. Do NOT give buy/sell advice. "
            "If there are no findings, say the scan found no significant signals and note its limits."
        )
        return self.llm.complete("You are a careful equity research analyst.", user, max_tokens=800).strip()

    def ask(self, question: str):
        chunks = self.index.hybrid_search([question], [], k=self.top_k)
        user = f"QUESTION: {question}\n\nEXCERPTS:\n{_format_chunks(chunks)}"
        return self.llm.complete(ASK_SYSTEM, user, max_tokens=1200).strip(), chunks
