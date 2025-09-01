import streamlit as st
import pandas as pd
import re

# ======================
# Utilities
# ======================

def clean_markdown_table(text: str) -> str:
    """ניקוי טקסט טבלה בפורמט Markdown"""
    if not isinstance(text, str):
        return ""
    s = text.strip().strip('"').strip()
    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
    # דילוג עד לשורת הכותרת
    start = 0
    for i, ln in enumerate(lines):
        if "|" in ln and ("עיקרון" in ln or "Principle" in ln) and ("ציון" in ln or "Score" in ln):
            start = i
            break
    lines = lines[start:]
    norm = []
    for ln in lines:
        if "|" not in ln: continue
        ln = re.sub(r"^\|", "", ln)
        ln = re.sub(r"\|$", "", ln)
        parts = [c.strip() for c in ln.split("|")]
        if all(set(p) <= {"-"," "} for p in parts):
            norm.append("|".join(parts)); continue
        while parts and parts[0] == "": parts.pop(0)
        while parts and parts[-1] == "": parts.pop()
        norm.append("|".join(parts))
    return "\n".join(norm)

def markdown_to_df(text: str):
    s = clean_markdown_table(text)
    if "|" not in s: return None
    rows = [ln for ln in s.split("\n") if "|" in ln]
    if len(rows) < 2: return None
    headers = [h.strip() for h in rows[0].split("|")]
    seen, uniq = {}, []
    for h in headers:
        if h in seen: seen[h]+=1; uniq.append(f"{h} {seen[h]}")
        else: seen[h]=1; uniq.append(h)
    body = []
    for ln in rows[2:]:
        parts = [c.strip() for c in ln.split("|")]
        if len(parts) == len(uniq): body.append(parts)
    return pd.DataFrame(body, columns=uniq) if body else None

def explain_badge(score: float) -> str:
    if pd.isna(score): return "<span class='score-badge score-unknown'>❓</span>"
    if score >= 6.5:  return "<span class='score-badge score-good'>✅ מושלם</span>"
    if score >= 5.5:  return "<span class='score-badge score-good'>🟢 טוב מאוד</span>"
    if score >= 4.5:  return "<span class='score-badge score-mid'>🟡 בינוני</span>"
    if score >= 3.5:  return "<span class='score-badge score-mid'>🟠 גבולי</span>"
    return "<span class='score-badge score-bad'>🔴 דורש שכתוב</span>"

def explain_label(score: float) -> str:
    if pd.isna(score): return "לא ידוע"
    if score >= 6.5:  return "מושלם"
    if score >= 5.5:  return "טוב מאוד"
    if score >= 4.5:  return "בינוני"
    if score >= 3.5:  return "גבולי"
    return "דורש שכתוב"

def priority_emoji(score: float) -> str:
    if pd.isna(score): return "⚪"
    if score >= 6.5:  return "🟢"
    if score >= 5.5:  return "🟢"
    if score >= 4.5:  return "🟡"
    if score >= 3.5:  return "🟠"
    return "🔴"

def fmt_num(x): return "" if pd.isna(x) else f"{x:.1f}"

def safe_text(val) -> str:
    if val is None: return ""
    if isinstance(val, float) and pd.isna(val): return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan","none","null") else s

EXTRA_FIELDS_ALIASES = {
    "E-E-A-T": ["E-E-A-T Checker", "E-E-A-T Checklist"],
    "Entities": ["Entities Extraction"],
    "Intent": ["Intent Alignment"],
    "Content Gap": ["Content Gap vs Competitors"],
    "Schema": ["Schema Suggestions"],
    "Featured Snippet": ["Featured Snippet Optimizer"],
}
def resolve_field_name(df_cols, aliases):
    for name in aliases:
        if name in df_cols: return name
    return None

# ======================
# Page Setup
# ======================

st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")
st.markdown("<h1 class='rtl-text'>📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות</h1>", unsafe_allow_html=True)

st.markdown("""
<style>
.rtl-text { direction: rtl; text-align: right; font-family: Arial, sans-serif; }
.score-badge { border-radius: 8px; padding: 4px 8px; font-weight: bold; color: #fff; display: inline-block; }
.score-good { background-color: #4CAF50; }
.score-mid  { background-color: #FFC107; }
.score-bad  { background-color: #F44336; }
.score-unknown { background-color: #9E9E9E; }
table { direction: rtl !important; text-align: right !important; font-family: Arial, sans-serif; }
</style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("העלה קובץ Excel מהסריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    df["Score Before"] = df["Score Before"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Score After"]  = df["Score After"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)

    for col in ["Evaluation Table Before", "Evaluation Table After"]:
        if col not in df.columns: df[col] = ""
    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"]  = df["Evaluation Table After"].fillna("")

    df["Score Explanation"]    = df["Score Before"].apply(explain_badge)
    df["Score Label (Before)"] = df["Score Before"].apply(explain_label)
    df["Score Emoji (Before)"] = df["Score Before"].apply(priority_emoji)

    # סינון
    st.sidebar.header("🌟 סינון")
    idx_options = ["הכל"] + (df["Indexability"].dropna().unique().tolist() if "Indexability" in df.columns else [])
    indexability_filter = st.sidebar.selectbox("Indexability", options=idx_options)
    weak_before = st.sidebar.checkbox("הצג רק ציון Before < 6")

    filtered_df = df.copy()
    if indexability_filter != "הכל" and "Indexability" in df.columns:
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_before:
        filtered_df = filtered_df[filtered_df["Score Before"] < 6]

    # ======================
    # ניתוח מפורט לפי עמוד (טאבים)
    # ======================

    st.markdown("<h3 class='rtl-text'>🗂 ניתוח מפורט לפי עמוד</h3>", unsafe_allow_html=True)

    resolved_fields = {
        "E-E-A-T": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["E-E-A-T"]),
        "Entities": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Entities"]),
        "Intent": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Intent"]),
        "Content Gap": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Content Gap"]),
        "Schema": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Schema"]),
        "Featured Snippet": resolve_field_name(df.columns, EXTRA_FIELDS_ALIASES["Featured Snippet"]),
    }

    for _, row in filtered_df.iterrows():
        url    = row.get("Address", "")
        before = row.get("Score Before", float("nan"))
        after  = row.get("Score After", float("nan"))
        label  = row.get("Score Label (Before)", "לא ידוע")
        emoji  = row.get("Score Emoji (Before)", "⚪")

        expander_title = f"{emoji}  🔗 {url}  |  ציון לפני: {fmt_num(before)}  •  {label}"
        with st.expander(expander_title):
            st.markdown(
                f"<div class='rtl-text'><strong>🔢 ציון לפני:</strong> {fmt_num(before)}"
                f" • <strong>אחרי:</strong> {fmt_num(after)}"
                f" • <strong>פירוש:</strong> {row['Score Explanation']}</div>",
                unsafe_allow_html=True
            )

            # טאבים
            tab_before, tab_after, tab_deep = st.tabs(["🔎 לפני", "✍️ אחרי", "🧩 עומק (GEO/AI)"])

            with tab_before:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח לפני:</strong></div>", unsafe_allow_html=True)
                df_before_tbl = markdown_to_df(row.get("Evaluation Table Before", ""))
                if df_before_tbl is not None:
                    html_before = df_before_tbl.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_before}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table Before", row.get("Evaluation Table Before", ""), height=220)

            with tab_after:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח אחרי:</strong></div>", unsafe_allow_html=True)
                df_after_tbl = markdown_to_df(row.get("Evaluation Table After", ""))
                if df_after_tbl is not None:
                    html_after = df_after_tbl.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_after}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table After", row.get("Evaluation Table After", ""), height=220)

            with tab_deep:
                sub_tabs = st.tabs([
                    "🧠 E-E-A-T",
                    "🧩 Entities",
                    "🎯 Intent",
                    "📉 Content Gap",
                    "🧾 Schema",
                    "🏆 Featured Snippet",
                ])

                def render_field(col_name, title):
                    st.markdown(f"<div class='rtl-text'><strong>{title}</strong></div>", unsafe_allow_html=True)
                    content = safe_text(row.get(col_name, "")) if col_name else ""
                    st.markdown(f"<div class='rtl-text'>{content}</div>", unsafe_allow_html=True)

                with sub_tabs[0]:
                    render_field(resolved_fields["E-E-A-T"], "המלצות E-E-A-T")
                with sub_tabs[1]:
                    render_field(resolved_fields["Entities"], "ישויות מזוהות (Entities)")
                with sub_tabs[2]:
                    render_field(resolved_fields["Intent"], "כוונת חיפוש (Intent)")
                with sub_tabs[3]:
                    render_field(resolved_fields["Content Gap"], "פערי תוכן מול מתחרים")
                with sub_tabs[4]:
                    render_field(resolved_fields["Schema"], "הצעות סכמות (Schema)")
                with sub_tabs[5]:
                    render_field(resolved_fields["Featured Snippet"], "Featured Snippet Optimizer")
