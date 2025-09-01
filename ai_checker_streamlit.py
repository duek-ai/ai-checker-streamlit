import streamlit as st
import pandas as pd
import re
import io

# ======================
# Utilities
# ======================

def clean_markdown_table(text: str) -> str:
    """ניקוי טקסט טבלה בפורמט Markdown (מסיר גרשיים, פייפים מובילים/סוגרים, מזהה כותרת אמיתית)."""
    if not isinstance(text, str):
        return ""
    s = text.strip().strip('"').strip()
    if not s:
        return ""
    lines = [ln.strip() for ln in s.split("\n") if ln.strip()]
    # דילוג עד לשורת הכותרת (כוללת עיקרון/Principle וציון/Score)
    start = 0
    for i, ln in enumerate(lines):
        if "|" in ln and ("עיקרון" in ln or "Principle" in ln) and ("ציון" in ln or "Score" in ln):
            start = i
            break
    lines = lines[start:] if start < len(lines) else lines
    norm = []
    for ln in lines:
        if "|" not in ln:
            continue
        ln = re.sub(r"^\|", "", ln)
        ln = re.sub(r"\|$", "", ln)
        parts = [c.strip() for c in ln.split("|")]
        # מזהה שורת מפריד --- | --- | ---
        if all(set(p) <= {"-"," "} for p in parts):
            norm.append("|".join(parts))
            continue
        # מסיר עמודות ריקות בתחילה/סוף
        while parts and parts[0] == "":
            parts.pop(0)
        while parts and parts[-1] == "":
            parts.pop()
        norm.append("|".join(parts))
    return "\n".join(norm)

def markdown_to_df(text: str):
    """ממיר טבלת Markdown ל-DataFrame, כולל דה-דופ של כותרות."""
    s = clean_markdown_table(text)
    if "|" not in s:
        return None
    rows = [ln for ln in s.split("\n") if "|" in ln]
    if len(rows) < 2:
        return None
    headers = [h.strip() for h in rows[0].split("|")]
    # דה-דופ כותרות
    seen, uniq = {}, []
    for h in headers:
        if h in seen:
            seen[h] += 1
            uniq.append(f"{h} {seen[h]}")
        else:
            seen[h] = 1
            uniq.append(h)
    body = []
    # דילוג על שורת המפריד (השורה השנייה)
    for ln in rows[2:]:
        parts = [c.strip() for c in ln.split("|")]
        if len(parts) == len(uniq):
            body.append(parts)
    return pd.DataFrame(body, columns=uniq) if body else None

def explain_badge(score: float) -> str:
    """תגית צבעונית (HTML) להצגה בתוך הכרטיס."""
    if pd.isna(score): return "<span class='score-badge score-unknown'>❓</span>"
    if score >= 6.5:   return "<span class='score-badge score-good'>✅ מושלם</span>"
    if score >= 5.5:   return "<span class='score-badge score-good'>🟢 טוב מאוד</span>"
    if score >= 4.5:   return "<span class='score-badge score-mid'>🟡 בינוני</span>"
    if score >= 3.5:   return "<span class='score-badge score-mid'>🟠 גבולי</span>"
    return "<span class='score-badge score-bad'>🔴 דורש שכתוב</span>"

def explain_label(score: float) -> str:
    """תיאור טקסטואלי לתווית expander."""
    if pd.isna(score): return "לא ידוע"
    if score >= 6.5:   return "מושלם"
    if score >= 5.5:   return "טוב מאוד"
    if score >= 4.5:   return "בינוני"
    if score >= 3.5:   return "גבולי"
    return "דורש שכתוב"

def priority_emoji(score: float) -> str:
    """אימוג׳י צבעוני לפי Score Before (נראה גם לפני פתיחה)."""
    if pd.isna(score): return "⚪"
    if score >= 6.5:   return "🟢"
    if score >= 5.5:   return "🟢"
    if score >= 4.5:   return "🟡"
    if score >= 3.5:   return "🟠"
    return "🔴"

def fmt_num(x):
    return "" if pd.isna(x) else f"{x:.1f}"

def safe_text(val) -> str:
    """נרמול ערך טקסטואלי: NaN/None/'nan' → '', ו-strip."""
    if val is None:
        return ""
    if isinstance(val, float) and pd.isna(val):
        return ""
    s = str(val).strip()
    return "" if s.lower() in ("nan", "none", "null") else s

# שמות עמודות אפשריים (aliases) לשדות העומק
EXTRA_FIELDS_ALIASES = {
    "E-E-A-T": ["E-E-A-T Checker", "E-E-A-T Checklist"],
    "Entities": ["Entities Extraction"],
    "Intent": ["Intent Alignment"],
    "Content Gap": ["Content Gap vs Competitors"],
    "Schema": ["Schema Suggestions"],
    "Featured Snippet": ["Featured Snippet Optimizer", "Featured Snippet Optimizer "],  # כולל רווח טריילינג אם קיים
}

def resolve_field_name(df_cols, aliases):
    """מחזיר את שם העמודה כפי שקיים בפועל בדאטה (מתוך רשימת aliases)."""
    for name in aliases:
        if name in df_cols:
            return name
    return None

# ======================
# Page Setup
# ======================

st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")
st.markdown("<h1 class='rtl-text'>📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות</h1>", unsafe_allow_html=True)

# RTL + badges + table styles
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
    # --- קריאה + נרמול שמות עמודות ---
    df = pd.read_excel(uploaded_file)
    df.columns = df.columns.str.strip()

    # ניקוי שדות ציונים (שומרים רק מספר)
    df["Score Before"] = df["Score Before"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Score After"]  = df["Score After"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)

    # הבטחה שהעמודות קיימות
    for col in ["Evaluation Table Before", "Evaluation Table After"]:
        if col not in df.columns:
            df[col] = ""
    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"]  = df["Evaluation Table After"].fillna("")

    # תיעדוף לפי BEFORE
    df["Score Explanation"]    = df["Score Before"].apply(explain_badge)
    df["Score Label (Before)"] = df["Score Before"].apply(explain_label)
    df["Score Emoji (Before)"] = df["Score Before"].apply(priority_emoji)

    # מקרא צבעים
    st.markdown(
        "<div class='legend rtl-text'>"
        "<span>🔴 דחוף</span><span>🟠 גבולי</span><span>🟡 בינוני</span><span>🟢 טוב/מושלם</span>"
        "</div>",
        unsafe_allow_html=True
    )

    # -------------------------
    # Sidebar Filters
    # -------------------------
    st.sidebar.header("🌟 סינון")
    idx_options = ["הכל"] + (df["Indexability"].dropna().unique().tolist() if "Indexability" in df.columns else [])
    indexability_filter = st.sidebar.selectbox("Indexability", options=idx_options)
    weak_before = st.sidebar.checkbox("הצג רק ציון Before < 6")

    filtered_df = df.copy()
    if indexability_filter != "הכל" and "Indexability" in df.columns:
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_before:
        filtered_df = filtered_df[filtered_df["Score Before"] < 6]

    # -------------------------
    # 📋 טבלה מותאמת (Builder)
    # -------------------------
    st.markdown("<h3 class='rtl-text'>📋 טבלה מותאמת</h3>", unsafe_allow_html=True)

    base_cols = ["Address", "Original Url", "Title 1", "Indexability",
                 "Score Before", "Score After", "Score Explanation"]
    extra_cols_candidates = [
        "Content Type", "Status Code", "Meta Description 1", "H1-1",
        "Closest Semantically Similar Address", "Semantic Similarity Score",
        "No. Semantically Similar", "Semantic Relevance Score",
    ]
    available_base = [c for c in base_cols if c in filtered_df.columns or c == "Score Explanation"]
    available_extra = [c for c in extra_cols_candidates if c in filtered_df.columns]

    with st.expander("⚙️ אפשרויות מתקדמות לטבלה"):
        add_priority_emoji = st.checkbox("הוסף עמודת עדיפות (אימוג׳י לפי Score Before)", value=True)
        add_delta = st.checkbox("הוסף Δ שיפור (Score After − Score Before)", value=True)
        add_eval_means = st.checkbox("חשב ממוצע ציונים מתוך Evaluation Table (לפני/אחרי)", value=False)
        st.caption("הפעלת חישובי Evaluation תלויה באיכות הטבלאות בשדות Evaluation Table Before/After.")

    df_custom = filtered_df.copy()

    if add_priority_emoji:
        if "Score Emoji (Before)" not in df_custom.columns:
            df_custom["Score Emoji (Before)"] = df_custom["Score Before"].apply(priority_emoji)
        available_base = ["Score Emoji (Before)"] + available_base

    if add_delta:
        df_custom["Δ Score"] = df_custom["Score After"] - df_custom["Score Before"]
        if "Δ Score" not in available_base:
            available_base.append("Δ Score")

    if add_eval_means:
        def _extract_scores(md):
            md = safe_text(md)
            if "|" not in md:
                return []
            rows = [ln for ln in md.split("\n") if "|" in ln]
            scores = []
            for r in rows[2:]:
                parts = [p.strip() for p in r.split("|")]
                if len(parts) >= 2:
                    try:
                        scores.append(float(parts[1]))
                    except:
                        pass
            return scores

        for col_src, col_dst in [("Evaluation Table Before", "Eval Mean Before"),
                                 ("Evaluation Table After",  "Eval Mean After")]:
            if col_src in df_custom.columns:
                df_custom[col_dst] = df_custom[col_src].apply(
                    lambda t: round(sum(_extract_scores(t))/len(_extract_scores(t)), 2) if _extract_scores(t) else None
                )
                if col_dst not in available_base:
                    available_base.append(col_dst)

    c1, c2, c3 = st.columns([2, 2, 2])
    with c1:
        default_selection = [c for c in ["Score Emoji (Before)", "Address", "Title 1",
                                         "Score Before", "Score Explanation", "Score After", "Δ Score"]
                             if c in (available_base + available_extra)]
        selected_cols = st.multiselect(
            "בחר/י עמודות להצגה:",
            options=available_base + available_extra,
            default=default_selection
        )
    with c2:
        search_text = st.text_input("🔎 חיפוש חופשי (URL/כותרת/תיאור):", value="")
    with c3:
        sort_by = st.selectbox("מיין לפי:", options=(selected_cols or ["Address"]))
        sort_desc = st.checkbox("מיון יורד", value=True)

    df_view = df_custom.copy()
    if search_text.strip():
        patt = search_text.strip().lower()
        mask = False
        for candidate in ["Address", "Title 1", "Meta Description 1", "H1-1"]:
            if candidate in df_view.columns:
                m = df_view[candidate].astype(str).str.lower().str.contains(patt, na=False)
                mask = m if mask is False else (mask | m)
        if isinstance(mask, pd.Series):
            df_view = df_view[mask]

    if selected_cols:
        safe_cols = [c for c in selected_cols if c in df_view.columns]
        if safe_cols:
            try:
                df_view = df_view.sort_values(by=sort_by, ascending=not sort_desc)
            except Exception:
                pass
            st.dataframe(df_view[safe_cols], use_container_width=True)

            # הורדה CSV
            csv_bytes = df_view[safe_cols].to_csv(index=False).encode("utf-8-sig")
            st.download_button("⬇️ הורדה כ-CSV", data=csv_bytes,
                               file_name="custom_table.csv", mime="text/csv")
            # הורדה Excel
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="xlsxwriter") as writer:
                df_view[safe_cols].to_excel(writer, index=False, sheet_name="Custom Table")
            st.download_button("⬇️ הורדה כ-Excel", data=out.getvalue(),
                               file_name="custom_table.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        else:
            st.info("לא נבחרו עמודות קיימות להצגה.")
    else:
        st.warning("נא לבחור לפחות עמודה אחת.")

    # -------------------------
    # 🗂 ניתוח מפורט לפי עמוד (טאבים)
    # -------------------------
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
            # שורת סיכום צבעונית בראש הכרטיס
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

                render_field(resolved_fields["E-E-A-T"], "המלצות E-E-A-T")   # tab 1
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
