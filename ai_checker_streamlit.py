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
    OPENAI
