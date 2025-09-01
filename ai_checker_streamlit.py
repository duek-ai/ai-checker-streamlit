import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(layout="wide", page_title="AI Screaming Frog Viewer")
st.title("📊 דוח SEO מעילים – ניתוח Screaming Frog עם תובנות")

uploaded_file = st.file_uploader("העלה קובץ Excel מתבנית סריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    def extract_score_from_text(text):
        if pd.isna(text):
            return None
        match = re.search(r"(\d)/7", str(text))
        if match:
            return int(match.group(1))
        return None

    def evaluate_score_text(text):
        score = extract_score_from_text(text)
        if score is None:
            return "❓ לא זוהה"
        elif score == 7:
            return "✅ מושלם – אין צורך בשיפור"
        elif score == 6:
            return "🟢 טוב מאוד – תיקון קל"
        elif score == 5:
            return "🟡 בינוני – כדאי לשפר"
        elif score == 4:
            return "🟠 גבולי – נדרש שכתוב"
        elif score <= 3:
            return "🔴 חלש – דרוש שכתוב מלא"
        else:
            return "❓ לא זוהה"

    # יצירת טור פעולות מומלצות
    def generate_action(row):
        actions = []
        if row.get("Indexability") == "Non-Indexable":
            actions.append("להפוך לאינדקס")
        if row.get("Title 1 Length", 0) > 60:
            actions.append("טייטל ארוך מדי")
        if pd.isna(row.get("Product Description Optimizer")):
            actions.append("להוסיף תיאור מוצר")
        if pd.isna(row.get("Product Title Optimizer")):
            actions.append("להוסיף שם מוצר שיווקי")
        if pd.isna(row.get("FAQ Generator")):
            actions.append("ליצור שאלות נפוצות (FAQs)")
        if pd.isna(row.get("7-Point Evaluation – After")):
            actions.append("אין ציון 7 נקודות - לנתח מחדש")
        return ", ".join(actions)

    def suggest_text_improvement(row):
        score = extract_score_from_text(row.get("7-Point Evaluation – After"))
        if score is None:
            return ""
        elif score >= 6:
            return "שפר ניסוח לפי עקרונות: מיקוד ועוגנים"
        elif score >= 4:
            return "שכתב פתיח, עוגנים, דיוק והקשר"
        else:
            return "דרוש שכתוב מלא לפי 7 העקרונות"

    df["Action Items"] = df.apply(generate_action, axis=1)
    df["GPT Suggestion"] = df.apply(suggest_text_improvement, axis=1)
    df["Score Explanation"] = df["7-Point Evaluation – After"].apply(evaluate_score_text)

    # מסננים לפי שדות נפוצים
    st.sidebar.header("🎯 מסננים")
    indexability_filter = st.sidebar.selectbox("Indexability", options=["הכל"] + df["Indexability"].dropna().unique().tolist())
    title_len_filter = st.sidebar.checkbox("Title ארוך מ-60 תווים")
    missing_description = st.sidebar.checkbox("חסר תיאור מוצר")
    weak_score = st.sidebar.checkbox("ציון 7 נקודות נמוך (<=5)")

    filtered_df = df.copy()
    if indexability_filter != "הכל":
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if title_len_filter:
        filtered_df = filtered_df[filtered_df["Title 1 Length"] > 60]
    if missing_description:
        filtered_df = filtered_df[filtered_df["Product Description Optimizer"].isna()]
    if weak_score:
        filtered_df = filtered_df[filtered_df["7-Point Evaluation – After"].apply(lambda x: extract_score_from_text(x) is not None and extract_score_from_text(x) <= 5)]

    # הצגת תובנות כלליות
    st.subheader("📌 סטטיסטיקות כלליות")
    col1, col2, col3 = st.columns(3)
    col1.metric('סה"כ עמודים', len(df))
    col2.metric("לא אינדקסביליים", len(df[df["Indexability"] == "Non-Indexable"]))
    col3.metric("חסרי תיאור מוצר", df["Product Description Optimizer"].isna().sum())

    st.subheader("📄 טבלת עמודים")
    st.dataframe(filtered_df[[
        "Address",
        "Indexability",
        "Title 1",
        "Title 1 Length",
        "Product Title Optimizer",
        "Product Description Optimizer",
        "7-Point Evaluation – Before",
        "7-Point Evaluation – After",
        "Score Explanation",
        "Action Items",
        "GPT Suggestion"
    ]], use_container_width=True)

    # הורדה כקובץ אקסל
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Filtered')
    st.download_button("📥 הורד את הטבלה המסוננת כ-Excel", data=output.getvalue(), file_name="filtered_report.xlsx")
