"""Transparent, heuristic risk score. Not investment advice."""

FINDING_POINTS = {"High": 12, "Medium": 5, "Low": 1}
RATIO_POINTS = {"red": 8, "watch": 3}


def compute_score(findings: list, ratios: list):
    """Return (score 0-100, band). Only citation-verified findings count."""
    pts = 0
    for f in findings:
        if f.verified:
            pts += FINDING_POINTS.get(f.severity, 1)
    for r in ratios:
        pts += RATIO_POINTS.get(r.flag, 0)
    score = min(100, pts)
    if score < 20:
        band = "Low"
    elif score < 45:
        band = "Moderate"
    elif score < 70:
        band = "Elevated"
    else:
        band = "High"
    return score, band
