"""Financial ratio calculations that back up the text-based red flags with numbers."""
from dataclasses import dataclass

FIELDS = [
    ("revenue", "Revenue from operations"),
    ("pbt", "Profit before tax"),
    ("pat", "Profit after tax"),
    ("finance_costs", "Finance costs"),
    ("total_debt", "Total borrowings (current + non-current)"),
    ("total_equity", "Total equity"),
    ("current_assets", "Total current assets"),
    ("current_liabilities", "Total current liabilities"),
    ("trade_receivables", "Trade receivables"),
    ("inventories", "Inventories"),
    ("cfo", "Net cash from operating activities"),
]
FIELD_KEYS = [k for k, _ in FIELDS]


@dataclass
class Ratio:
    name: str
    value: float
    display: str
    flag: str  # "", "watch" or "red"
    note: str = ""


def _g(d, key):
    v = (d or {}).get(key)
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return float(v)


def _div(a, b):
    if a is None or b is None or b == 0:
        return None
    return a / b


def _pct(x):
    return f"{x * 100:.1f}%"


def compute_ratios(cur: dict, prev: dict = None) -> list:
    """Compute ratios from current-year (and optionally previous-year) metrics."""
    out = []
    revenue, pat, pbt = _g(cur, "revenue"), _g(cur, "pat"), _g(cur, "pbt")
    fin, debt, equity = _g(cur, "finance_costs"), _g(cur, "total_debt"), _g(cur, "total_equity")
    ca, cl = _g(cur, "current_assets"), _g(cur, "current_liabilities")
    rec, inv, cfo = _g(cur, "trade_receivables"), _g(cur, "inventories"), _g(cur, "cfo")
    p_rev, p_pat, p_rec = _g(prev, "revenue"), _g(prev, "pat"), _g(prev, "trade_receivables")

    rev_growth = None
    if revenue is not None and p_rev:
        rev_growth = (revenue - p_rev) / abs(p_rev)
        out.append(Ratio("Revenue growth (YoY)", rev_growth, _pct(rev_growth), "watch" if rev_growth < 0 else ""))

    if pat is not None and p_pat:
        g = (pat - p_pat) / abs(p_pat)
        flag = "red" if pat < 0 < p_pat else ("watch" if g < -0.3 else "")
        out.append(Ratio("Net profit growth (YoY)", g, _pct(g), flag))

    m = _div(pat, revenue)
    if m is not None:
        out.append(Ratio("Net profit margin", m, _pct(m), "red" if m < 0 else ("watch" if m < 0.03 else "")))

    if pbt is not None and fin is not None:
        ebit_margin = _div(pbt + fin, revenue)
        if ebit_margin is not None:
            out.append(Ratio("EBIT margin (PBT + finance cost)", ebit_margin, _pct(ebit_margin), ""))
        cover = _div(pbt + fin, fin)
        if cover is not None:
            flag = "red" if cover < 1.5 else ("watch" if cover < 3 else "")
            out.append(Ratio("Interest coverage", cover, f"{cover:.2f}x", flag, "EBIT / finance costs"))

    if debt is not None and equity is not None:
        if equity <= 0:
            out.append(Ratio("Debt-to-equity", float("nan"), "n/a", "red", "Equity is zero or negative"))
        else:
            de = debt / equity
            out.append(Ratio("Debt-to-equity", de, f"{de:.2f}x", "red" if de > 2 else ("watch" if de > 1 else "")))

    cr = _div(ca, cl)
    if cr is not None:
        out.append(Ratio("Current ratio", cr, f"{cr:.2f}x", "red" if cr < 1 else ("watch" if cr < 1.2 else "")))

    rd = _div(rec, revenue)
    if rd is not None:
        days = rd * 365
        p_days = (p_rec / p_rev * 365) if (p_rec is not None and p_rev) else None
        flag = "watch" if (p_days and days > p_days * 1.25) else ""
        note = f"Previous year: {p_days:.0f} days" if p_days else ""
        out.append(Ratio("Receivable days", days, f"{days:.0f} days", flag, note))

    idays = _div(inv, revenue)
    if idays is not None:
        out.append(Ratio("Inventory days (on revenue)", idays * 365, f"{idays * 365:.0f} days", "", "Uses revenue as proxy for COGS"))

    if rec is not None and p_rec and rev_growth is not None:
        rec_growth = (rec - p_rec) / abs(p_rec)
        gap = rec_growth - rev_growth
        flag = "red" if gap > 0.30 else ("watch" if gap > 0.15 else "")
        out.append(
            Ratio("Receivables growth minus revenue growth", gap, f"{gap * 100:+.1f} pp", flag,
                  "Receivables growing faster than sales can signal aggressive revenue recognition")
        )

    if cfo is not None and pat is not None:
        if cfo < 0:
            out.append(Ratio("Cash conversion (CFO / PAT)", _div(cfo, pat) or float("nan"), "negative CFO", "red", "Operating cash flow is negative"))
        elif pat > 0:
            conv = cfo / pat
            flag = "red" if conv < 0.5 else ("watch" if conv < 0.8 else "")
            out.append(Ratio("Cash conversion (CFO / PAT)", conv, f"{conv:.2f}x", flag, "Profits not backed by cash are a classic red flag"))

    return out
