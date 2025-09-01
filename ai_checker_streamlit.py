import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")
st.title("📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות")

st.markdown("""
    <style>
    .rtl-text {
        direction: rtl;
        text-align: right;
        font-family: Arial;
    }
    .streamlit-expanderHeader {
        direction: rtl;
        text-align: right;
    }
    </style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("העלה קובץ Excel מהסריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"] = df["Evaluation Table After"].fillna("")

    def recalculate_score(table_text):
        try:
            df_score = pd.read_csv(io.StringIO(table_text), sep='|', engine='python', skiprows=[1])
            df_score = df_score.dropna(axis=1, how='all').dropna(how='all')
            df_score.columns = [col.strip() for col in df_score.columns]
            score_col = df_score.columns[1] if df_score.shape[1] >= 2 else None
            if score_col:
                scores = pd.to_numeric(df_score[score_col], errors='coerce')
                scores = scores.dropna()
                if not scores.empty:
                    return round(scores.mean(), 1)
        except Exception:
            return None
        return None

    df["Score Before"] = df["Evaluation Table Before"].apply(recalculate_score)
    df["Score After"] = df["Evaluation Table After"].apply(recalculate_score)

    def explain_score(score):
        if pd.isna(score):
            return "❓"
        elif score >= 6.5:
            return "✅ מושלם"
        elif score >= 5.5:
            return "🟢 טוב מאוד"
        elif score >= 4.5:
            return "🟡 בינוני"
        elif score >= 3.5:
            return "🟠 גבולי"
        else:
            return "🔴 דורש שכתוב"

    df["Score Explanation"] = df["Score After"].apply(explain_score)

    # פילטרים
    st.sidebar.header("🎯 סינון")
    indexability_filter = st.sidebar.selectbox("Indexability", options=["הכל"] + df["Indexability"].dropna().unique().tolist())
    weak_score = st.sidebar.checkbox("ציון After נמוך מ-6")

    filtered_df = df.copy()
    if indexability_filter != "הכל":
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_score:
        filtered_df = filtered_df[filtered_df["Score After"] < 6]

    # טבלת עמודים
    st.subheader("📄 טבלת עמודים עם ציונים (מבוסס חישוב ממוצע מתוך הטבלאות)")
    st.dataframe(filtered_df[["Address", "Title 1", "Score Before", "Score After", "Score Explanation"]], use_container_width=True)

    # הורדה
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Evaluation')

    st.download_button("📥 הורד את הקובץ כ-Excel", data=output.getvalue(), file_name="evaluation_report.xlsx")
