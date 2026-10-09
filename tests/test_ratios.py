from src.ratios import compute_ratios
from src.scoring import compute_score
from src.models import Finding


def by_name(ratios):
    return {r.name: r for r in ratios}


def test_healthy_company_has_no_red_flags():
    cur = dict(revenue=1200, pbt=200, pat=150, finance_costs=20, total_debt=100, total_equity=800,
               current_assets=500, current_liabilities=250, trade_receivables=120, inventories=80, cfo=170)
    prev = dict(revenue=1000, pat=120, trade_receivables=100)
    r = by_name(compute_ratios(cur, prev))
    assert all(x.flag != "red" for x in r.values())
    assert round(r["Revenue growth (YoY)"].value, 2) == 0.20


def test_stressed_company_flags():
    cur = dict(revenue=1000, pbt=30, pat=20, finance_costs=40, total_debt=900, total_equity=300,
               current_assets=200, current_liabilities=400, trade_receivables=400, inventories=50, cfo=-10)
    prev = dict(revenue=950, pat=60, trade_receivables=150)
    r = by_name(compute_ratios(cur, prev))
    assert r["Debt-to-equity"].flag == "red"
    assert r["Current ratio"].flag == "red"
    assert r["Cash conversion (CFO / PAT)"].flag == "red"
    assert r["Receivables growth minus revenue growth"].flag == "red"


def test_missing_values_do_not_crash():
    assert compute_ratios({}, {}) == []
    assert isinstance(compute_ratios({"revenue": 100}, None), list)


def test_score_ignores_unverified_findings():
    f_ok = Finding("c", "t", "High", "s", "q", 1, verified=True)
    f_bad = Finding("c", "t", "High", "s", "q", 1, verified=False)
    assert compute_score([f_ok], [])[0] == 12
    assert compute_score([f_bad], [])[0] == 0
