"""Export the analysis as Markdown or JSON."""
import json
from dataclasses import asdict


def to_markdown(res) -> str:
    lines = [f"# Red-Flag Report{': ' + res.company if res.company else ''}", ""]
    lines.append(f"**Risk score:** {res.score}/100 ({res.band})  |  **Pages scanned:** {res.pages_total}")
    lines.append("")
    if res.summary:
        lines += ["## Executive summary", "", res.summary, ""]

    lines += ["## Findings", ""]
    if not res.findings:
        lines.append("_No findings._")
    for f in res.findings:
        mark = "verified" if f.verified else "UNVERIFIED - quote not found on cited page"
        lines += [
            f"### [{f.severity}] {f.title} (p. {f.page})",
            f"*{f.category}* - {mark}",
            "",
            f.summary,
            "",
            f"> {f.quote}",
            "",
            f"**Why it matters:** {f.why_it_matters}",
            "",
        ]

    lines += ["## Ratios", "", "| Ratio | Value | Flag | Note |", "|---|---|---|---|"]
    for r in res.ratios:
        lines.append(f"| {r.name} | {r.display} | {r.flag or '-'} | {r.note} |")

    if res.notes:
        lines += ["", "## Run notes", ""] + [f"- {n}" for n in res.notes]
    lines += ["", "_Automated screening aid, not investment advice. Verify every item against the source report._"]
    return "\n".join(lines)


def to_json(res) -> str:
    return json.dumps(asdict(res), indent=2, default=str)
