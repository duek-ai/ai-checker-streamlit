import streamlit as st
import pandas as pd
import re

# ======================
# Utilities
# ======================

def markdown_to_df(text: str):
    """Parse simple pipe-table markdown into a DataFrame, with duplicate-column handling."""
    if not isinstance(text, str) or "|" not in text:
        return None
    lines = [line.strip() for line in text.split("\n") if "|" in line]
    if len(lines) < 2:
        return None

    headers = [h.strip() for h in lines[0].split("|")]
    # de-dup headers
    seen, uniq_headers = {}, []
    for h in headers:
        if h in seen:
            seen[h] += 1
            uniq_headers.append(f"{h} {seen[h]}")
        else:
            seen[h] = 1
            uniq_headers.append(h)

    rows = []
    # skip header + separator (--- | --- | ---)
    for line in lines[2:]:
        parts = [c.strip() for c in line.split("|")]
        if len(parts) == len(uniq_headers):
            rows.append(parts)

    if not rows:
        return None
    return pd.DataFrame(rows, columns=uniq_headers)

def explain_badge(score: float) -> str:
    """HTML badge used *inside* the expander (colored)."""
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
    """Plain text label for expander TITLE."""
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

def priority_emoji(score: float) -> str:
    """Emoji shown in expander TITLE (works before opening)."""
    if pd.isna(score): return "⚪"
    if score >= 6.5:  return "🟢"
    if score >= 5.5:  return "🟢"
    if score >= 4.5:  return "🟡"
    if score >= 3.5:  return "🟠"
    return "🔴"

def fmt_num(x):
    return "" if pd.isna(x) else f"{x:.1f}"

def safe_text(val) -> str:
    """Normalize cell text: NaN/None/'nan' -> '' and strip."""
    if val is None:
        return ""
    if isinstance(val, float) and pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "null") else s

# Map of friendly names -> possible column aliases in the sheet
EXTRA_FIELDS_ALIASES = {
    "E-E-A-T": ["E-E-A-T Checker", "E-E-A-T Checklist"],
    "Entities": ["Entities Extraction"],
    "Intent": ["Intent Alignment"],
    "Content Gap": ["Content Gap vs Competitors"],
    "Schema": ["Schema Suggestions"],
    "Featured Snippet": ["Featured Snippet Optimizer", "Featured Snippet Optimizer "],  # covers trailing space
}

def resolve_field_name(df_cols, aliases):
    """Return the first alias that exists in df.columns (after strip)."""
    for name in aliases:
        if name in df_cols:
            return name
    return None

# ======================
# Page
# ======================

st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")
st.markdown("<h1 class='rtl-text'>📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות</h1>", unsafe_allow_html=True)

# RTL + badges + table base styles
st.markdown("""
<style>
.rtl-text { direction: rtl; text-align: right; font-family: Arial, sans-serif; }
.score-badge { border-radius: 8px; padding: 4px 8px; font-weight: bold; color: #fff; display: inline-block; }
.score-good { background-color: #4CAF50; }
.score-mid  { background-color: #FFC107; }
.score-bad  { background-color: #F44336; }
.score-unknown { background-color: #9E9E9E; }
table { direction: rtl !important; text-align: right !important; font-family: Arial, sans-serif; }
.legend { display:flex; gap:10px; margin:6px 0 16px; }
.legend span { padding:2px 8px; border-radius:999px; background:#f6f6f6; }
</style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("העלה קובץ Excel מהסריקה", type=["xlsx"])

if uploaded_file:
    # --- Load + normalize columns ---
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()  # important: remove accidental spaces

    # Normalize numeric score fields
    df["Score Before"] = df["Score Before"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Score After"]  = df["Score After"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)

    # Ensure evaluation columns exist
    for col in ["Evaluation Table Before", "Evaluation Table After"]:
        if col not in df.columns:
            df[col] = ""
    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"]  = df["Evaluation Table After"].fillna("")

    # Derive explanation triage FROM BEFORE (as requested)
    df["Score Explanation"]     = df["Score Before"].apply(explain_badge)
    df["Score Label (Before)"]  = df["Score Before"].apply(explain_label)
    df["Score Emoji (Before)"]  = df["Score Before"].apply(priority_emoji)

    # Legend for quick triage
    st.markdown(
        "<div class='legend rtl-text'>"
        "<span>🔴 דחוף</span><span>🟠 גבולי</span><span>🟡 בינוני</span><span>🟢 טוב/מושלם</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # Sidebar filters
    st.sidebar.header("🌟 סינון")
    idx_options = ["הכל"] + (df["Indexability"].dropna().unique().tolist() if "Indexability" in df.columns else [])
    indexability_filter = st.sidebar.selectbox("Indexability", options=idx_options)
    weak_before = st.sidebar.checkbox("הצג רק ציון Before < 6")

    filtered_df = df.copy()
    if indexability_filter != "הכל" and "Indexability" in df.columns:
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_before:
        filtered_df = filtered_df[filtered_df["Score Before"] < 6]

    # Main table
    st.markdown("<h3 class='rtl-text'>📄 בחר/י אילו עמודות להצגה בטבלת עמודים</h3>", unsafe_allow_html=True)
    default_cols = [c for c in ["Address", "Title 1", "Score Before", "Score After", "Score Explanation"] if c in df.columns]
    selected_columns = st.multiselect(
        "בחר/י שדות להצגה:",
        options=df.columns.tolist(),
        default=default_cols
    )
    if selected_columns:
        st.markdown("<div class='rtl-text'>הפירוש והעדיפות נגזרים מ־<b>Score Before</b>.</div>", unsafe_allow_html=True)
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    # Resolve actual column names for the extra fields (considering aliases)
    resolved_fields = {
        "E-E-A-T": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["E-E-A-T"]),
        "Entities": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Entities"]),
        "Intent": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Intent"]),
        "Content Gap": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Content Gap"]),
        "Schema": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Schema"]),
        "Featured Snippet": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Featured Snippet"]),
    }

    # Detail per page
    st.markdown("<h3 class='rtl-text'>🗂 ניתוח מפורט לפי עמוד</h3>", unsafe_allow_html=True)

    for _, row in filtered_df.iterrows():
        url    = row.get("Address", "")
        before = row.get("Score Before", float("nan"))
        after  = row.get("Score After", float("nan"))
        label  = row.get("Score Label (Before)", "לא ידוע")
        emoji  = row.get("Score Emoji (Before)", "⚪")

        # Expander TITLE (emoji + URL + triage based on BEFORE)
        expander_title = f"{emoji}  🔗 {url}  |  ציון לפני: {fmt_num(before)}  •  {label}"
        with st.expander(expander_title):
            # Colored badge inside
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

            # Extra fields with alias resolution + safe_text normalization
            groups = [
                ("🧠 המלצות E-E-A-T", resolved_fields["E-E-A-T"]),
                ("🧩 ישויות מזוהות (Entities)", resolved_fields["Entities"]),
                ("🎯 ניתוח כוונת חיפוש", resolved_fields["Intent"]),
                ("📉 פערי תוכן מול מתחרים", resolved_fields["Content Gap"]),
                ("🧩 הצעות סכמות (Schema)", resolved_fields["Schema"]),
                ("🏆 Featured Snippet Optimizer", resolved_fields["Featured Snippet"]),
            ]
            for label_txt, actual_col in groups:
                if actual_col:
                    with st.expander(label_txt):
                        content = safe_text(row.get(actual_col, ""))
                        st.markdown(f"<div class='rtl-text'>{content}</div>", unsafe_allow_html=True)
