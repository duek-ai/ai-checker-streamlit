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
    </style>
""", unsafe_allow_html=True)

uploaded_file = st.file_uploader("העלה קובץ Excel מהסריקה", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    df["Score Before"] = df["Score Before"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Score After"] = df["Score After"].astype(str).str.extract(r"([0-9]+\.?[0-9]*)").astype(float)
    df["Evaluation Table Before"] = df["Evaluation Table Before"].fillna("")
    df["Evaluation Table After"] = df["Evaluation Table After"].fillna("")

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

    st.sidebar.header("🌟 סינון")
    indexability_filter = st.sidebar.selectbox("Indexability", options=["הכל"] + df["Indexability"].dropna().unique().tolist())
    weak_score = st.sidebar.checkbox("ציון After נמוך מ-6")

    filtered_df = df.copy()
    if indexability_filter != "הכל":
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_score:
        filtered_df = filtered_df[filtered_df["Score After"] < 6]

    st.subheader("📄 בחר/י אילו עמודות להצגה בטבלת עמודים")
    selected_columns = st.multiselect(
        "בחר/י שדות להצגה:",
        options=df.columns.tolist(),
        default=["Address", "Title 1", "Score Before", "Score After", "Score Explanation"]
    )

    if selected_columns:
        st.markdown("**📌 שימו לב:** השדות *Score Before* ו־*Score After* מחושבים מתוך הטבלאות Evaluation Table באופן אוטומטי.", unsafe_allow_html=True)
        st.dataframe(filtered_df[selected_columns], use_container_width=True)

        for i, row in filtered_df.iterrows():
            with st.expander(f"🔗 {row['Address']}"):
                st.markdown(f"**ציון לפני:** {row['Score Before']} | **אחרי:** {row['Score After']} | **פירוש:** {row['Score Explanation']}")

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("<div class='rtl-text'>טבלת ניתוח לפני:</div>", unsafe_allow_html=True)
                    st.dataframe(pd.read_fwf(io.StringIO(row['Evaluation Table Before'])), use_container_width=True)
                with col2:
                    st.markdown("<div class='rtl-text'>טבלת ניתוח אחרי:</div>", unsafe_allow_html=True)
                    st.dataframe(pd.read_fwf(io.StringIO(row['Evaluation Table After'])), use_container_width=True)

                with st.expander("🧠 המלצות E-E-A-T"):
                    st.markdown(f"<div class='rtl-text'>{row['E-E-A-T Checker']}</div>", unsafe_allow_html=True)

                with st.expander("🧩 ישויות מזוהות (Entities)"):
                    st.markdown(f"<div class='rtl-text'>{row['Entities Extraction']}</div>", unsafe_allow_html=True)

                with st.expander("🎯 ניתוח כוונת חיפוש"):
                    st.markdown(f"<div class='rtl-text'>{row['Intent Alignment']}</div>", unsafe_allow_html=True)

                with st.expander("📉 פערי תוכן מול מתחרים"):
                    st.markdown(f"<div class='rtl-text'>{row['Content Gap vs Competitors']}</div>", unsafe_allow_html=True)

                with st.expander("🧩 הצעות סכמות (Schema)"):
                    st.markdown(f"<div class='rtl-text'>{row['Schema Suggestions']}</div>", unsafe_allow_html=True)

                with st.expander("🛠 המלצות יישום ישיר (Rewriters & Optimizers)"):
                    st.markdown("<div class='rtl-text'>🔷 <b>כותרת H1 מומלצת</b>:</div>", unsafe_allow_html=True)
                    st.markdown(row['H1 Rewriter'])
                    st.markdown("<div class='rtl-text'>⭐ <b>Featured Snippet מוצע</b>:</div>", unsafe_allow_html=True)
                    st.markdown(row['Featured Snippet Optimizer'])
                    st.markdown("<div class='rtl-text'>🎯 <b>קריאה לפעולה (CTA) מומלצת</b>:</div>", unsafe_allow_html=True)
                    st.markdown(row['CTA Optimizer'])
                    st.markdown("<div class='rtl-text'>📝 <b>כותרת מוצר מומלצת</b>:</div>", unsafe_allow_html=True)
                    st.markdown(row['Product Title Optimizer'])
                    st.markdown("<div class='rtl-text'>🧾 <b>תיאור מוצר מומלץ</b>:</div>", unsafe_allow_html=True)
                    st.markdown(row['Product Description Optimizer'])
    else:
        st.warning("לא נבחרו עמודות להצגה")
