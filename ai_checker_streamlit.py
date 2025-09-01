import streamlit as st
import pandas as pd
import io
import re

st.set_page_config(layout="wide", page_title="AI Screaming Frog Viewer")
st.title("📊 דוח SEO מעילים – ניתוח Screaming Frog עם תובנות")

uploaded_file = st.file_uploader("העלה קובץ Excel מתבנית סריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    def extract_score(text):
        if pd.isna(text):
            return None
        text = str(text)
        match_decimal = re.search(r"ציון כולל[:\s]*([0-9]+\.?[0-9]*)", text)
        if match_decimal:
            try:
                score = float(match_decimal.group(1))
                if score >= 6.5:
                    return 7
                elif score >= 5.5:
                    return 6
                elif score >= 4.5:
                    return 5
                elif score >= 3.5:
                    return 4
                else:
                    return 3
            except:
                pass
        match_fraction = re.search(r"(\d)/7", text)
        if match_fraction:
            return int(match_fraction.group(1))
        return None

    def evaluate_score_text(score):
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
        return "❓ לא זוהה"

    # הפקת ציונים ומידע נוסף
    df["Score Before"] = df["7-Point Evaluation – Before"].apply(extract_score)
    df["Score After"] = df["7-Point Evaluation – After"].apply(extract_score)
    df["Score Explanation"] = df["Score After"].apply(evaluate_score_text)
    df["Text Before"] = df["7-Point Evaluation – Before"]
    df["Text After"] = df["7-Point Evaluation – After"]

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
        if pd.isna(row.get("Score After")):
            actions.append("אין ציון 7 נקודות - לנתח מחדש")
        return ", ".join(actions)

    def suggest_text_improvement(row):
        score = row.get("Score After")
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

    # מסננים
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
        filtered_df = filtered_df[filtered_df["Score After"].apply(lambda x: x is not None and x <= 5)]

    # סטטיסטיקות
    st.subheader("📌 סטטיסטיקות כלליות")
    col1, col2, col3 = st.columns(3)
    col1.metric('סה"כ עמודים', len(df))
    col2.metric("לא אינדקסביליים", len(df[df["Indexability"] == "Non-Indexable"]))
    col3.metric("חסרי תיאור מוצר", df["Product Description Optimizer"].isna().sum())

    # טבלת תצוגה
    st.subheader("📄 טבלת עמודים")
    st.dataframe(filtered_df[[
        "Address",
        "Indexability",
        "Title 1",
        "Score Before",
        "Score After",
        "Score Explanation",
        "Action Items",
        "GPT Suggestion"
    ]], use_container_width=True)

    # תצוגת כרטיסיות עם Expander
    st.subheader("🗂 תצוגה מפורטת לפי עמוד")
    for i, row in filtered_df.iterrows():
        with st.expander(f"{row['Address']}"):
            st.markdown(f"**📉 ציון לפני:** {row['Score Before']} | **📈 ציון אחרי:** {row['Score After']} | {row['Score Explanation']}")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**טקסט Before:**")
                st.text_area("Before", row["Text Before"], height=200)
            with col2:
                st.markdown("**טקסט After:**")
                st.text_area("After", row["Text After"], height=200)

    # הורדת אקסל
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Filtered')
    st.download_button("📥 הורד את הטבלה המסוננת כ-Excel", data=output.getvalue(), file_name="filtered_report.xlsx")
