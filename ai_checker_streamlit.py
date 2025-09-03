import streamlit as st
import pandas as pd
import re
import io
import os

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
    return "<span class='score-badge score-bad'>🔴 דורש שכתבּוב</span>"

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
# Optimization Score & Eval helpers
# ======================

def extract_scores_from_eval(md_text: str):
    """מחזיר רשימת ציונים + הערות מהטבלה (לפני/אחרי)."""
    md = safe_text(md_text)
    if "|" not in md:
        return [], []
    rows = [ln for ln in md.split("\n") if "|" in ln]
    scores, notes = [], []
    for r in rows[2:]:
        parts = [p.strip() for p in r.split("|")]
        if len(parts) >= 3:
            try:
                scores.append(float(parts[1]))
            except:
                pass
            notes.append(parts[2])
    return scores, notes

def parse_eval_tables_to_delta(before_md: str, after_md: str):
    """מחזיר טבלת דלתא לפי עיקרון: Before/After/Delta (אם אין התאמה מלאה – מכסה חלקית)."""
    bdf = markdown_to_df(before_md) or pd.DataFrame(columns=["עיקרון","ציון","הערה"])
    adf = markdown_to_df(after_md)  or pd.DataFrame(columns=["עיקרון","ציון","הערה"])
    # הסרה בטוחה של כותרות באנגלית אם קיימות
    b_key = "עיקרון" if "עיקרון" in bdf.columns else (bdf.columns[0] if len(bdf.columns) else "עיקרון")
    a_key = "עיקרון" if "עיקרון" in adf.columns else (adf.columns[0] if len(adf.columns) else "עיקרון")

    # המרות מספריות
    def to_num(s):
        try: return float(str(s).strip())
        except: return None

    b_small = pd.DataFrame({
        "Principle": bdf[b_key],
        "Before": [to_num(x) for x in (bdf["ציון"] if "ציון" in bdf.columns else bdf.iloc[:,1] if len(bdf.columns)>1 else [])]
    })
    a_small = pd.DataFrame({
        "Principle": adf[a_key],
        "After": [to_num(x) for x in (adf["ציון"] if "ציון" in adf.columns else adf.iloc[:,1] if len(adf.columns)>1 else [])]
    })
    # איחוד לפי עיקרון
    out = pd.merge(b_small, a_small, on="Principle", how="outer")
    out["Delta"] = out["After"] - out["Before"]
    return out

def optimization_label(before, delta, filled_ratio):
    """תווית עדיפות לפי מצב נוכחי, פוטנציאל שיפור ומלאות שדות עומק."""
    if pd.isna(before):
        return "לא ידוע"
    if before < 4:
        return "🔴 דחוף מאוד"
    if before < 5.5 and filled_ratio < 0.5:
        return "🟠 דורש טיפול"
    if before < 6.5 and (pd.isna(delta) or delta < 1.0):
        return "🟡 במעקב"
    return "🟢 טוב/מותאם"

def compute_optimization_score_row(row, df_cols):
    """ציון משוקלל 0–10: מצב נוכחי + פוטנציאל + עומק תוכן."""
    before = row.get("Score Before", 0) or 0
    after  = row.get("Score After", 0) or 0
    delta  = after - before

    b_scores, _ = extract_scores_from_eval(row.get("Evaluation Table Before", ""))
    a_scores, _ = extract_scores_from_eval(row.get("Evaluation Table After", ""))

    b_mean = sum(b_scores)/len(b_scores) if b_scores else before or 0
    a_mean = sum(a_scores)/len(a_scores) if a_scores else after  or before

    depth_cols = [
        "E-E-A-T Checker", "E-E-A-T Checklist",
        "Entities Extraction", "Intent Alignment",
        "Content Gap vs Competitors", "Schema Suggestions",
        "Featured Snippet Optimizer", "Featured Snippet Optimizer "
    ]
    present = 0; total = 0
    for c in depth_cols:
        if c in df_cols:
            total += 1
            if safe_text(row.get(c, "")):
                present += 1
    filled_ratio = (present / total) if total else 0

    w_before   = 0.45
    w_delta    = 0.25
    w_evalmean = 0.20
    w_depth    = 0.10

    score = (
        w_before * before +
        w_delta  * max(delta, 0) +
        w_evalmean * ((b_mean + a_mean) / 2) +
        w_depth * (filled_ratio * 10)
    )
    score = max(0, min(10, score))
    label = optimization_label(before, delta, filled_ratio)
    return round(score, 2), label

# ======================
# LLM (OpenAI) – optional with fallback
# ======================

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0.6

try:
    import openai
    OPENAI_API_KEY = st.secrets.get("OPENAI_API_KEY", os.getenv("OPENAI_API_KEY"))
    if OPENAI_API_KEY:
        openai.api_key = OPENAI_API_KEY
except Exception:
    OPENAI_API_KEY = None

def llm_generate_json(system_msg: str, user_prompt: str, model: str = DEFAULT_MODEL, temperature: float = DEFAULT_TEMPERATURE):
    """שולף JSON מהמודל; מחזיר dict או None."""
    if not OPENAI_API_KEY:
        return None
    try:
        resp = openai.ChatCompletion.create(
            model=model,
            temperature=temperature,
            messages=[{"role":"system","content":system_msg},{"role":"user","content":user_prompt}]
        )
        text = resp["choices"][0]["message"]["content"].strip()
        import json
        m = re.search(r"\{.*\}", text, flags=re.S)
        return json.loads(m.group(0)) if m else json.loads(text)
    except Exception as e:
        st.warning(f"⚠️ LLM error: {e}")
        return None

def build_generation_prompt(row):
    url   = safe_text(row.get("Address",""))
    title = safe_text(row.get("Title 1",""))
    meta  = safe_text(row.get("Meta Description 1",""))
    h1    = safe_text(row.get("H1-1","")) if "H1-1" in row else ""
    entities = safe_text(row.get("Entities Extraction","")) if "Entities Extraction" in row else ""
    intent   = safe_text(row.get("Intent Alignment","")) if "Intent Alignment" in row else ""
    eeat     = safe_text(row.get("E-E-A-T Checker","")) if "E-E-A-T Checker" in row else safe_text(row.get("E-E-A-T Checklist",""))
    gap      = safe_text(row.get("Content Gap vs Competitors","")) if "Content Gap vs Competitors" in row else ""
    schema_s = safe_text(row.get("Schema Suggestions","")) if "Schema Suggestions" in row else ""
    eval_b   = safe_text(row.get("Evaluation Table Before",""))
    eval_a   = safe_text(row.get("Evaluation Table After",""))
    before   = row.get("Score Before", None)
    after    = row.get("Score After", None)

    return f"""
את/ה מומחה/ית SEO ו-GEO להתאמת תוכן למודלי שפה (LLM).
הפק שדות אופטימליים לעמוד אופנה בעברית, ידידותיים ל-LLM, תמציתיים וברורים.

קונטקסט:
URL: {url}
Title (קיים): {title}
H1 (קיים): {h1}
Meta Description (קיים): {meta}

רמזים סמנטיים:
Entities: {entities}
Intent: {intent}
E-E-A-T: {eeat}
Content Gap: {gap}
Schema Suggestions: {schema_s}

Evaluation Before:
{eval_b}

Evaluation After:
{eval_a}

Scores: Before={before}, After={after}

החזר JSON בלבד:
{{
  "meta_title": "עד ~60 תווים, מילה ראשית + מותג (אם רלוונטי)",
  "meta_description": "עד ~155 תווים, תמציתי ועם ערך/USP",
  "h1": "H1 אידאלי לעמוד",
  "h2": "H2 שמסדר את התוכן",
  "product_names": ["שם וריאציה 1", "שם וריאציה 2", "שם וריאציה 3"],
  "short_desc": "150–200 תווים",
  "long_desc": "120–200 מילים, נוח ל-LLM",
  "llm_gaps": ["רשימת פריטים שחסר כדי לשפר מענה של מודלי AI"]
}}
ללא HTML/אימוג'ים. עברית תקינה.
"""

def generate_optimized_fields_template(row):
    """Fallback מקומי אם אין API – מחולל שדות הגיוניים."""
    title = safe_text(row.get("Title 1", ""))
    h1    = safe_text(row.get("H1-1", "")) if "H1-1" in row else ""
    meta  = safe_text(row.get("Meta Description 1", ""))
    kw = title.split("|")[0].strip() if title else "מעילים לנשים"
    brand = "Crazyline"
    meta_title = f"{kw[:55]} | {brand}"
    meta_desc  = (meta or f"מחפשת {kw}? {brand} מציעה מגוון דגמים מחמיאים, משלוח מהיר והחלפה נוחה.").strip()[:155]
    product_names = [
        f"{kw} – גזרות מחמיאות ובדים איכותיים",
        f"{kw} – דגמים חדשים לעונה",
        f"{kw} – משלוח מהיר והחלפה נוחה",
    ]
    short_desc = f"{kw} של {brand} בעיצובים מחמיאים, מגוון בדים ומידות, ומשלוח מהיר. בחרי את הדגם המושלם לעונה."
    long_desc = (
        f"הקולקציה של {brand} מציעה {kw} במבחר גזרות, בדים וצבעים. "
        f"שלבי בין נוחות לסטייל ובחרי דגם שמתאים למזג האוויר ולשגרת היומיום. "
        f"משלוח מהיר והחלפה נוחה, טבלת מידות מפורטת והמלצות לבחירה נכונה."
    )
    llm_gaps = [
        "להוסיף טבלת מידות מלאה ומדויקת.",
        "להרחיב מפרט בד: הרכב, משקל, הוראות כביסה.",
        "להוסיף שו״ת (FAQ) תכל'ס: משלוחים, החזרות, אחריות."
    ]
    return {
        "meta_title": meta_title,
        "meta_description": meta_desc,
        "h1": h1 or f"{kw} – מבחר לעונה | {brand}",
        "h2": f"{kw}: מדריך קצר לבחירה",
        "product_names": product_names,
        "short_desc": short_desc,
        "long_desc": long_desc,
        "llm_gaps": llm_gaps
    }

def generate_optimized_fields_llm(row, model=DEFAULT_MODEL, temperature=DEFAULT_TEMPERATURE):
    """מנסה לייצר שדות בעזרת OpenAI; אם אין API – נופל ל-template המקומי."""
    system = "You are an expert SEO & GEO copywriter for Hebrew e-commerce, writing concise, LLM-friendly fields."
    prompt = build_generation_prompt(row)
    data = llm_generate_json(system, prompt, model=model, temperature=temperature)
    if data:
        data.setdefault("product_names", [])
        data.setdefault("llm_gaps", [])
        return data
    return generate_optimized_fields_template(row)

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

# Sidebar – LLM settings
st.sidebar.subheader("🤖 LLM Generator")
OPENAI_HINT = "מפתח ב־st.secrets['OPENAI_API_KEY'] או כ־ENV"
use_llm = st.sidebar.checkbox("הפעל ייצור אוטומטי (OpenAI)", value=bool(os.getenv("OPENAI_API_KEY") or st.secrets.get("OPENAI_API_KEY")))
model_name = st.sidebar.text_input("Model", value=DEFAULT_MODEL, help=OPENAI_HINT)
temp_val = st.sidebar.slider("Temperature", 0.0, 1.0, DEFAULT_TEMPERATURE, 0.05)

# קלט הקובץ
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

    # Optimization Score + Label
    df[["Optimization Score", "Optimization Label"]] = df.apply(
        lambda r: pd.Series(compute_optimization_score_row(r, df.columns)),
        axis=1
    )

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
                 "Score Before", "Score After", "Score Explanation",
                 "Optimization Score", "Optimization Label"]
    extra_cols_candidates = [
        "Content Type", "Status Code", "Meta Description 1", "H1-1",
        "Closest Semantically Similar Address", "Semantic Similarity Score",
        "No. Semantically Similar", "Semantic Relevance Score",
    ]
    available_base = [c for c in base_cols if (c in filtered_df.columns) or c in ["Score Explanation","Optimization Score","Optimization Label"]]
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
            if "|" not in md: return []
            rows = [ln for ln in md.split("\n") if "|" in ln]
            vals = []
            for r in rows[2:]:
                parts = [p.strip() for p in r.split("|")]
                if len(parts) >= 2:
                    try: vals.append(float(parts[1]))
                    except: pass
            return vals

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
                                         "Score Before", "Score Explanation", "Score After",
                                         "Δ Score", "Optimization Score", "Optimization Label"]
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
            # הורדה Excel (openpyxl)
            out = io.BytesIO()
            with pd.ExcelWriter(out, engine="openpyxl") as writer:
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

            # טאבים (כולל Entities פעם אחת בלבד)
            tab_before, tab_after, tab_deep, tab_opt, tab_summary = st.tabs(
                ["🔎 לפני", "✍️ אחרי", "🧩 עומק (GEO/AI)", "✨ אופטימיזציה", "📈 סיכום שיפורים"]
            )

            # --- Tab: לפני ---
            with tab_before:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח לפני:</strong></div>", unsafe_allow_html=True)
                df_before_tbl = markdown_to_df(row.get("Evaluation Table Before", ""))
                if df_before_tbl is not None:
                    html_before = df_before_tbl.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_before}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table Before", row.get("Evaluation Table Before", ""), height=220)

            # --- Tab: אחרי ---
            with tab_after:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח אחרי:</strong></div>", unsafe_allow_html=True)
                df_after_tbl = markdown_to_df(row.get("Evaluation Table After", ""))
                if df_after_tbl is not None:
                    html_after = df_after_tbl.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_after}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table After", row.get("Evaluation Table After", ""), height=220)

            # --- Tab: עומק (טאבים פנימיים, ללא כפילות Entities) ---
            with tab_deep:
                sub_tabs = st.tabs([
                    "🧠 E-E-A-T",
                    "🎯 Intent",
                    "📉 Content Gap",
                    "🧩 Entities",
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
                    render_field(resolved_fields["Intent"], "כוונת חיפוש (Intent)")
                with sub_tabs[2]:
                    render_field(resolved_fields["Content Gap"], "פערי תוכן מול מתחרים")
                with sub_tabs[3]:
                    render_field(resolved_fields["Entities"], "ישויות מזוהות (Entities)")
                with sub_tabs[4]:
                    render_field(resolved_fields["Schema"], "הצעות סכמות (Schema)")
                with sub_tabs[5]:
                    render_field(resolved_fields["Featured Snippet"], "Featured Snippet Optimizer")

            # --- Tab: אופטימיזציה (LLM/Template) ---
            with tab_opt:
                st.markdown("<div class='rtl-text'><strong>שדות מוצעים (SEO/LLM-Ready):</strong></div>", unsafe_allow_html=True)

                # ייצור נקודתי לכל שורה
                key_prefix = f"gen_{row.name}"
                if use_llm:
                    if st.button("⚡ ייצור אוטומטי עם LLM", key=f"{key_prefix}_btn"):
                        gen_now = generate_optimized_fields_llm(row, model=model_name, temperature=temp_val)
                        st.session_state[key_prefix] = gen_now

                gen = st.session_state.get(key_prefix)
                if not gen:
                    gen = generate_optimized_fields_llm(row, model=model_name, temperature=temp_val) if use_llm else generate_optimized_fields_template(row)

                st.text_input("Meta Title", gen.get("meta_title",""), key=f"mt_{row.name}")
                st.text_area("Meta Description", gen.get("meta_description",""), height=80, key=f"md_{row.name}")

                st.text_input("H1 מוצע", gen.get("h1",""), key=f"h1_{row.name}")
                st.text_input("H2 מוצע", gen.get("h2",""), key=f"h2_{row.name}")

                st.markdown("<div class='rtl-text'><strong>שמות פריטים מוצעים:</strong></div>", unsafe_allow_html=True)
                for i, name in enumerate(gen.get("product_names", [])[:3], 1):
                    st.text_input(f"שם פריט #{i}", name, key=f"pname_{i}_{row.name}")

                st.text_area("תיאור קצר (SEO/LLM)", gen.get("short_desc",""), height=110, key=f"short_{row.name}")
                st.text_area("תיאור ארוך (SEO/LLM)", gen.get("long_desc",""), height=180, key=f"long_{row.name}")

                st.markdown("<div class='rtl-text'><strong>מידע חסר מומלץ ל-LLM/AI:</strong></div>", unsafe_allow_html=True)
                for j, gap in enumerate(gen.get("llm_gaps", [])[:10], 1):
                    st.markdown(f"<div class='rtl-text'>• {gap}</div>", unsafe_allow_html=True)

            # --- Tab: סיכום שיפורים (Delta per principle) ---
            with tab_summary:
                delta_df = parse_eval_tables_to_delta(row.get("Evaluation Table Before",""),
                                                      row.get("Evaluation Table After",""))
                if not delta_df.empty:
                    # עיצוב תצוגה
                    html_sum = delta_df.to_html(index=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_sum}</div>", unsafe_allow_html=True)
                else:
                    st.info("לא נמצאה טבלת עקרונות שניתן להציג בהפרשים.")
    
    # -------------------------
    # יצוא Batch של שדות אופטימיים (לכל הכתובות המסוננות)
    # -------------------------
    st.markdown("### ⬇️ יצוא אופטימיזציות (Batch)")
    if st.button("הפק קובץ Excel לכל הכתובות המסוננות"):
        rows_out = []
        for _, r in filtered_df.iterrows():
            gen = generate_optimized_fields_llm(r, model=model_name, temperature=temp_val) if use_llm else generate_optimized_fields_template(r)
            rows_out.append({
                "Address": safe_text(r.get("Address","")),
                "Meta Title": gen.get("meta_title",""),
                "Meta Description": gen.get("meta_description",""),
                "H1": gen.get("h1",""),
                "H2": gen.get("h2",""),
                "Product Name 1": (gen.get("product_names") or ["","",""])[0] if gen.get("product_names") else "",
                "Product Name 2": (gen.get("product_names") or ["","",""])[1] if gen.get("product_names") and len(gen["product_names"]) > 1 else "",
                "Product Name 3": (gen.get("product_names") or ["","",""])[2] if gen.get("product_names") and len(gen["product_names"]) > 2 else "",
                "Short Desc": gen.get("short_desc",""),
                "Long Desc": gen.get("long_desc",""),
                "LLM Gaps": " • ".join(gen.get("llm_gaps", [])),
                "Optimization Score": r.get("Optimization Score",""),
                "Optimization Label": r.get("Optimization Label",""),
            })

        out_df = pd.DataFrame(rows_out)
        out = io.BytesIO()
        with pd.ExcelWriter(out, engine="openpyxl") as writer:
            out_df.to_excel(writer, index=False, sheet_name="Optimized Fields")
        st.download_button(
            "⬇️ הורד/י Excel עם שדות אופטימליים",
            data=out.getvalue(),
            file_name="optimized_fields.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
