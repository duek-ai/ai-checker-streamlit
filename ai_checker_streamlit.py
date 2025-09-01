import streamlit as st
import pandas as pd
import io

# פונקציה להמרת טקסט Markdown לטבלה
def markdown_to_df(text):
    lines = [line.strip() for line in text.split("\n") if "|" in line]
    if len(lines) < 2:
        return None
    headers = [h.strip() for h in lines[0].split("|")]
    seen = {}
    unique_headers = []
    for h in headers:
        if h in seen:
            seen[h] += 1
            unique_headers.append(f"{h} {seen[h]}")
        else:
            seen[h] = 1
            unique_headers.append(h)
    data = []
    for line in lines[2:]:
        parts = [cell.strip() for cell in line.split("|")]
        if len(parts) == len(unique_headers):
            data.append(parts)
    return pd.DataFrame(data, columns=unique_headers)

# הגדרת עמוד
st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")
st.markdown("<h1 class='rtl-text'>📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות</h1>", unsafe_allow_html=True)

# CSS לעיצוב RTL ותגיות ציונים
st.markdown("""
    <style>
    .rtl-text {
        direction: rtl;
        text-align: right;
        font-family: Arial, sans-serif;
    }
    .score-badge {
        border-radius: 8px;
        padding: 4px 8px;
        font-weight: bold;
        color: white;
        display: inline-block;
    }
    .score-good { background-color: #4CAF50; }
    .score-mid { background-color: #FFC107; }
    .score-bad { background-color: #F44336; }
    .score-unknown { background-color: #9E9E9E; }
    table {
        direction: rtl !important;
        text-align: right !important;
        font-family: Arial;
    }
    </style>
""", unsafe_allow_html=True)

# העלאת קובץ
uploaded_file = st.file_uploader("העלה קובץ Excel מהסריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # ניקוי שדות ציונים
    df["Score Before"] = df["Score Before"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Score After"] = df["Score After"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"] = df["Evaluation Table After"].fillna("")

    # הסבר הציון – מבוסס על Score Before בלבד
    def explain_score(score):
        if pd.isna(score):
            return "<span class='score-badge score-unknown'>❓</span>"
        elif score >= 6.5:
            return "<span class='score-badge score-good'>✅ מושלם</span>"
        elif score >= 5.5:
            return "<span class='score-badge score-good'>🟢 טוב מאוד</span>"
        elif score >= 4.5:
            return "<span class='score-badge score-mid'>🟡 בינוני</span>"
        elif score >= 3.5:
            return "<span class='score-badge score-mid'>🟠 גבולי</span>"
        else:
            return "<span class='score-badge score-bad'>🔴 דורש שכתוב</span>"

    df["Score Explanation"] = df["Score Before"].apply(explain_score)

    # סינון צד
    st.sidebar.header("🌟 סינון")
    indexability_filter = st.sidebar.selectbox("Indexability", options=["הכל"] + df["Indexability"].dropna().unique().tolist())
    weak_score = st.sidebar.checkbox("ציון Before נמוך מ-6")

    filtered_df = df.copy()
    if indexability_filter != "הכל":
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_score:
        filtered_df = filtered_df[filtered_df["Score Before"] < 6]

    # טבלת עמודים
    st.markdown("<h3 class='rtl-text'>📄 בחר/י אילו עמודות להצגה בטבלת עמודים</h3>", unsafe_allow_html=True)
    selected_columns = st.multiselect(
        "בחר/י שדות להצגה:",
        options=df.columns.tolist(),
        default=["Address", "Title 1", "Score Before", "Score Explanation"]
    )

    if selected_columns:
        st.markdown("<div class='rtl-text'>השדה <strong>Score Explanation</strong> מחושב מתוך Score Before בלבד, כדי לזהות עמודים הדורשים טיפול.</div>", unsafe_allow_html=True)
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    # ניתוח לפי עמוד
    st.markdown("<h3 class='rtl-text'>🗂 ניתוח מפורט לפי עמוד</h3>", unsafe_allow_html=True)
    for i, row in filtered_df.iterrows():
        with st.expander(f"🔗 {row['Address']}"):
            st.markdown(
                f"<div class='rtl-text'><strong>🔢 ציון לפני:</strong> {row['Score Before']} • <strong>אחרי:</strong> {row['Score After']} • <strong>פירוש:</strong> {row['Score Explanation']}</div>",
                unsafe_allow_html=True
            )

            col1, col2 = st.columns(2)

            with col1:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח לפני:</strong></div>", unsafe_allow_html=True)
                df_before = markdown_to_df(row["Evaluation Table Before"])
                if df_before is not None:
                    html_before = df_before.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_before}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table Before", row["Evaluation Table Before"], height=220)

            with col2:
                st.markdown("<div class='rtl-text'><strong>טבלת ניתוח אחרי:</strong></div>", unsafe_allow_html=True)
                df_after = markdown_to_df(row["Evaluation Table After"])
                if df_after is not None:
                    html_after = df_after.to_html(index=False, escape=False)
                    st.markdown(f"<div style='direction: rtl; text-align: right'>{html_after}</div>", unsafe_allow_html=True)
                else:
                    st.text_area("Evaluation Table After", row["Evaluation Table After"], height=220)

            # שדות ניתוח נוספים
            extra_fields = [
                ("🧠 המלצות E-E-A-T", "E-E-A-T Checker"),
                ("🧩 ישויות מזוהות (Entities)", "Entities Extraction"),
                ("🎯 ניתוח כוונת חיפוש", "Intent Alignment"),
                ("📉 פערי תוכן מול מתחרים", "Content Gap vs Competitors"),
                ("🧩 הצעות סכמות (Schema)", "Schema Suggestions"),
                ("🛠 המלצות יישום ישיר (Rewriters & Optimizers)","Rewriters & Optimizers"),
                ("🏆 Featured Snippet Optimizer", "Featured Snippet Optimizer")
            ]
            for label, field in extra_fields:
                if field in df.columns:
                    with st.expander(label):
                        st.markdown(f"<div class='rtl-text'>{row.get(field, '')}</div>", unsafe_allow_html=True)
