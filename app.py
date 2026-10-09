"""Annual Report Red-Flag Detector - Streamlit UI.  Run with:  streamlit run app.py"""

import pandas as pd
import streamlit as st

from src import config
from src.agent import RedFlagAgent
from src.llm import LLM
from src.pdf_loader import file_hash, load_pdf_pages, looks_scanned, render_page_png
from src.ratios import FIELDS, FIELD_KEYS, compute_ratios
from src.report import to_json, to_markdown
from src.scoring import compute_score
from src.vector_store import ReportIndex

st.set_page_config(page_title="Annual Report Red-Flag Detector", page_icon="🚩", layout="wide")

SEV_ICON = {"High": "🔴", "Medium": "🟠", "Low": "🟡"}
FLAG_ICON = {"red": "🔴", "watch": "🟠", "": "🟢"}

st.title("🚩 Annual Report Red-Flag Detector")
st.caption(
    "RAG agent that reads an Indian annual report, extracts risk signals buried in the text "
    "(auditor remarks, related-party deals, contingent liabilities, policy changes, unusual notes) "
    "and cites the exact page."
)

# ---------------- sidebar ----------------
with st.sidebar:
    st.header("Settings")
    provider = st.selectbox("LLM provider", list(config.DEFAULT_MODELS))
    model = st.text_input("Model", value=config.DEFAULT_MODELS[provider])
    api_key = st.text_input("API key (optional if set in .env)", type="password")
    top_k = st.slider("Passages retrieved per category", 4, 16, 10)
    company = st.text_input("Company name (optional)")
    st.divider()
    st.caption("Automated screening aid, not investment advice. Always verify against the source report.")

# ---------------- upload + indexing ----------------
source = st.radio(
    "Choose the document",
    ["Pick from data/reports folder", "Upload a PDF"],
    horizontal=True,
)
if source.startswith("Pick"):
    files = sorted(config.REPORTS_DIR.glob("*.pdf"))
    if not files:
        st.info(f"No PDFs found. Copy annual report PDFs into `{config.REPORTS_DIR}` and refresh, or switch to 'Upload a PDF'.")
        st.stop()
    choice = st.selectbox("Select a report", files, format_func=lambda p: p.name)
    data = choice.read_bytes()
else:
    uploaded = st.file_uploader("Upload an annual report (PDF)", type=["pdf"])
    if not uploaded:
        st.info("Upload a company annual report PDF to begin (download one from the company's investor-relations page or BSE/NSE).")
        st.stop()
    data = uploaded.getvalue()

key = file_hash(data)

if st.session_state.get("key") != key:
    try:
        with st.status("Reading and indexing the report...", expanded=True) as status:
            bar = st.progress(0.0)
            pages = load_pdf_pages(data)
            if looks_scanned(pages):
                st.warning("This PDF has very little extractable text; it may be scanned. Results may be poor.")
            cache = config.CACHE_DIR / key
            if (cache / "chunks.pkl").exists():
                index = ReportIndex.load(cache)
                bar.progress(1.0)
            else:
                st.write(f"{len(pages)} pages found. Creating embeddings (first run takes a minute or two)...")
                index = ReportIndex.build(pages, progress=lambda f: bar.progress(min(f, 1.0)))
                index.save(cache)
            status.update(label=f"Indexed {len(pages)} pages / {len(index.chunks)} passages", state="complete")
    except ValueError as e:
        st.error(str(e))
        st.stop()
    st.session_state.update(key=key, index=index, result=None, chat=[])

index = st.session_state["index"]


def make_agent() -> RedFlagAgent:
    return RedFlagAgent(index, LLM(provider, model, api_key or None), top_k)


if st.button("🔍 Run red-flag analysis", type="primary"):
    try:
        agent = make_agent()
    except Exception as e:
        st.error(str(e))
        st.stop()
    bar = st.progress(0.0, text="Starting...")
    st.session_state["result"] = agent.analyze(company, progress=lambda f, m: bar.progress(min(f, 1.0), text=m))
    bar.empty()

result = st.session_state.get("result")

tab_sum, tab_flags, tab_ratio, tab_ask, tab_export = st.tabs(
    ["Summary", "Red flags", "Ratios", "Ask the report", "Export"]
)

# ---------------- summary ----------------
with tab_sum:
    if not result:
        st.write("Click **Run red-flag analysis** to scan the report.")
    else:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Risk score", f"{result.score}/100", result.band, delta_color="off")
        c2.metric("Verified findings", sum(f.verified for f in result.findings))
        c3.metric("High severity", sum(f.verified and f.severity == "High" for f in result.findings))
        c4.metric("Pages scanned", result.pages_total)
        st.subheader("Executive summary")
        st.write(result.summary or "_No summary generated._")
        for n in result.notes:
            st.warning(n)
        with st.expander("How is the score calculated?"):
            st.write(
                "Verified findings: High = 12, Medium = 5, Low = 1 points. Ratio flags: red = 8, watch = 3. "
                "Capped at 100. Bands: <20 Low, <45 Moderate, <70 Elevated, otherwise High. "
                "Findings whose quote could not be found on the cited page are shown but not scored."
            )

# ---------------- red flags ----------------
with tab_flags:
    if not result:
        st.write("No analysis yet.")
    else:
        f1, f2 = st.columns([2, 1])
        sevs = f1.multiselect("Severity", ["High", "Medium", "Low"], default=["High", "Medium", "Low"])
        only_verified = f2.checkbox("Verified citations only", value=False)
        shown = [f for f in result.findings if f.severity in sevs and (f.verified or not only_verified)]
        if not shown:
            st.info("No findings match the current filters.")
        categories = list(dict.fromkeys(f.category for f in shown))
        for cat in categories:
            st.subheader(cat)
            for i, f in enumerate([x for x in shown if x.category == cat]):
                tag = "✅" if f.verified else "⚠️ unverified"
                with st.expander(f"{SEV_ICON.get(f.severity, '')} {f.severity}: {f.title}  (p. {f.page})  {tag}"):
                    st.write(f.summary)
                    st.markdown(f"> {f.quote}")
                    if f.why_it_matters:
                        st.markdown(f"**Why it matters:** {f.why_it_matters}")
                    if not f.verified:
                        st.caption("The quoted text was not found on the cited page. Treat as unconfirmed.")
                    if st.checkbox("Show PDF page", key=f"pg-{cat}-{i}-{f.page}"):
                        st.image(render_page_png(data, f.page), caption=f"PDF page {f.page}")

# ---------------- ratios ----------------
with tab_ratio:
    if not result or not result.metrics:
        st.write("No analysis yet.")
    else:
        m = result.metrics
        st.caption(
            f"Basis: **{m.get('basis', 'unknown')}**  |  Unit: **{m.get('unit') or 'as in report'}**  |  "
            f"Source pages: {', '.join(map(str, m.get('pages', []))) or 'n/a'}. "
            "Extracted by the LLM - check and edit the numbers below; ratios update instantly."
        )
        df = pd.DataFrame(
            {
                m.get("current_label") or "Current": [(m.get("current") or {}).get(k) for k in FIELD_KEYS],
                m.get("previous_label") or "Previous": [(m.get("previous") or {}).get(k) for k in FIELD_KEYS],
            },
            index=[label for _, label in FIELDS],
        ).astype("float64")
        edited = st.data_editor(df, use_container_width=True)

        def to_dict(col):
            return {k: (None if pd.isna(v) else float(v)) for k, v in zip(FIELD_KEYS, edited[col])}

        cur_col, prev_col = edited.columns[0], edited.columns[1]
        m["current"], m["previous"] = to_dict(cur_col), to_dict(prev_col)
        result.ratios = compute_ratios(m["current"], m["previous"])
        result.score, result.band = compute_score(result.findings, result.ratios)

        if result.ratios:
            st.dataframe(
                pd.DataFrame(
                    [{"": FLAG_ICON.get(r.flag, ""), "Ratio": r.name, "Value": r.display, "Note": r.note}
                     for r in result.ratios]
                ),
                hide_index=True,
                use_container_width=True,
            )
        else:
            st.info("Not enough numbers to compute ratios. Fill in the table above.")

# ---------------- Q&A ----------------
with tab_ask:
    st.write("Ask anything about the report. Answers use only retrieved passages and cite pages.")
    for role, text in st.session_state.get("chat", []):
        with st.chat_message(role):
            st.markdown(text)
    q = st.chat_input("e.g. What are the largest related-party loans?")
    if q:
        st.session_state["chat"].append(("user", q))
        with st.chat_message("user"):
            st.markdown(q)
        with st.chat_message("assistant"):
            try:
                with st.spinner("Searching the report..."):
                    answer, chunks = make_agent().ask(q)
                st.markdown(answer)
                st.caption("Passages used: pages " + ", ".join(str(p) for p in sorted({c.page for c in chunks})))
                st.session_state["chat"].append(("assistant", answer))
            except Exception as e:
                st.error(str(e))

# ---------------- export ----------------
with tab_export:
    if not result:
        st.write("No analysis yet.")
    else:
        st.download_button("Download Markdown report", to_markdown(result), "redflag_report.md", "text/markdown")
        st.download_button("Download JSON", to_json(result), "redflag_report.json", "application/json")
