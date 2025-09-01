import streamlit as st
import pandas as pd
import re
import io

# ---------- Utilities ----------

def markdown_to_df(text: str):
    """Parse a simple pipe-table markdown into a DataFrame, with duplicate-column handling."""
    if not isinstance(text, str) or "|" not in text:
        return None
    lines = [line.strip() for line in text.split("\n") if "|" in line]
    if len(lines) < 2:
        return None

    headers = [h.strip() for h in lines[0].split("|")]
    # de-dup headers
    seen = {}
    uniq_headers = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            uniq_headers.append(f"{h} {seen[h]}")
        else:
            seen[h] = 1
            uniq_headers.append(h)

    rows = []
    # skip header + separator line (--- | --- | ---)
    for line in lines[2:]:
        parts = [c.strip() for c in line.split("|")]
        if len(parts) == len(uniq_headers):
            rows.append(parts)

    if not rows:
        return None
    return pd.DataFrame(rows, columns=uniq_headers)

def explain_badge(score: float) -> str:
    """HTML badge (inside expander content). Based on Score Before as requested."""
    if pd.isna(score):
        return "<span class='score-badge score-unknown'>❓</span>"
    if score >= 6.5:
        return "<span class='score-badge score-good'>✅ מושלם</span>"
    if score >= 5.5:
        return "<span class='score-badge score-good'>🟢 טוב מאוד</span>"
    if score >= 4.5:
        return "<span class='score-badge score-mid'>🟡 בינוני</span>"
    if score >= 3.5:
        return "<span class='score-badge score-mid'>🟠 גבולי</span>"
    return "<span class='score-badge score-bad'>🔴 דורש שכתוב</span>"

def explain_label(score: float) -> str:
    """Plain-text label (for expander TITLE line)."""
    if pd.isna(score):
        return "לא ידוע"
    if score >= 6.5:
        return "מושלם"
    if score >= 5.5:
        return "טוב מאוד"
    if score >= 4.5:
        return "בינוני"
    if score >= 3.5:
        return "גבולי"
    return "דורש שכתוב"

def fmt_num(x):
    return "" if pd.isna(x) else f"{x:.1f}"

# ---------- Page ----------

st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")
st.markdown("<h1 class='rtl-text'>📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות</h1>", unsafe_allow_html=True)

# RTL + badges + table base styles
st.markdown("""
<style>
.rtl-text { direction: rtl; text-align: right; font-family: Arial, sans-serif; }
.score-badge { border-radius: 8px; padding: 4px 8px; font-weight: bold; color: #fff; display: inline-block; }
.score-good { background-color: #4CAF50; }
.score-mid { background-color: #FFC107; }
.score-bad { background-color: #F44336; }
.score-unknown { background-color: #9E9E9E; }
table { direction: rtl !important; text-align: right !important; font-family: Arial, sans-serif; }
.expander-row { direction: rtl; text-align: right; }
</style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("העלה קובץ Excel מהסריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Normalize numeric scores (strip text and keep number)
    df["Score Before"] = df["Score Before"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Score After"]  = df["Score After"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)

    for col in ["Evaluation Table Before", "Evaluation Table After"]:
        if col not in df.columns:
            df[col] = ""
    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"]  = df["Evaluation Table After"].fillna("")

    # Score explanation based on BEFORE (priority triage)
    df["Score Explanation"] = df["Score Before"].apply(explain_badge)
    # Plain text label for expander title
    df["Score Label (Before)"] = df["Score Before"].apply(explain_label)

    # --- Sidebar filters ---
    st.sidebar.header("🌟 סינון")
    idx_options = ["הכל"] + (df["Indexability"].dropna().unique().tolist() if "Indexability" in df.columns else [])
    indexability_filter = st.sidebar.selectbox("Indexability", options=idx_options)
    weak_before = st.sidebar.checkbox("ציון Before נמוך מ-6")

    filtered_df = df.copy()
    if indexability_filter != "הכל" and "Indexability" in df.columns:
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_before:
        filtered_df = filtered_df[filtered_df["Score Before"] < 6]

    # --- Main table with selected columns ---
    st.markdown("<h3 class='rtl-text'>📄 בחר/י אילו עמודות להצגה בטבלת עמודים</h3>", unsafe_allow_html=True)
    default_cols = [c for c in ["Address", "Title 1", "Score Before", "Score After", "Score Explanation"] if c in df.columns]
    selected_columns = st.multiselect(
        "בחר/י שדות להצגה:",
        options=df.columns.tolist(),
        default=default_cols
    )
    if selected_columns:
        st.markdown("<div class='rtl-text'>הפירוש (תגית צבעונית) מחושב מתוך <b>Score Before</b> כדי לתת עדיפות טיפול.</div>", unsafe_allow_html=True)
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    # --- Per-page detailed analysis ---
    st.markdown("<h3 class='rtl-text'>🗂 ניתוח מפורט לפי עמוד</h3>", unsafe_allow_html=True)

    for _, row in filtered_df.iterrows():
        # Build expander TITLE that already shows URL + Score Before + plain-text label
        url = row.get("Address", "")
        before = row.get("Score Before", float("nan"))
        after  = row.get("Score After", float("nan"))
        label  = row.get("Score Label (Before)", "לא ידוע")

        expander_title = f"🔗 {url}  |  ציון לפני: {fmt_num(before)}  •  פירוש: {label}"
        with st.expander(expander_title):
            # Top line inside expander (with the colored badge)
            st.markdown(
                f"<div class='rtl-text'><strong>🔢 ציון לפני:</strong> {fmt_num(before)}"
                f" • <strong>אחרי:</strong> {fmt_num(after)}"
                f" • <strong>פירוש:</strong> {row['Score Explanation']}</div>",
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח לפני:</strong></div>", unsafe_allow_html=True)
                df_before_tbl = markdown_to_df(row.get("Evaluation Table Before", ""))
                if df_before_tbl is not None:
                    html_before = df_before_tbl.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_before}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table Before", row.get("Evaluation Table Before", ""), height=220)

            with col2:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח אחרי:</strong></div>", unsafe_allow_html=True)
                df_after_tbl = markdown_to_df(row.get("Evaluation Table After", ""))
                if df_after_tbl is not None:
                    html_after = df_after_tbl.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_after}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table After", row.get("Evaluation Table After", ""), height=220)

            # Extra textual fields (only if exist in the sheet)
            extra_fields = [
                ("🧠 המלצות E-E-A-T", "E-E-A-T Checker"),
                ("🧩 ישויות מזוהות (Entities)", "Entities Extraction"),
                ("🎯 ניתוח כוונת חיפוש", "Intent Alignment"),
                ("📉 פערי תוכן מול מתחרים", "Content Gap vs Competitors"),
                ("🧩 הצעות סכמות (Schema)", "Schema Suggestions"),
                ("🛠 המלצות יישום ישיר (Rewriters & Optimizers)", "Rewriters & Optimizers"),
                ("🏆 Featured Snippet Optimizer", "Featured Snippet Optimizer")
            ]
            for label_txt, field_name in extra_fields:
                if field_name in df.columns:
                    with st.expander(label_txt):
                        st.markdown(f"<div class='rtl-text'>{row.get(field_name, '')}</div>", unsafe_allow_html=True)
