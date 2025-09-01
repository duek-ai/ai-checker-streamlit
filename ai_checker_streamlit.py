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
    .score-badge {
        border-radius: 8px;
        padding: 4px 8px;
        font-weight: bold;
        color: white;
        display: inline-block;
    }
    .score-good { background-color: #4CAF50; }     /* ירוק */
    .score-mid { background-color: #FFC107; }     /* כתום */
    .score-bad { background-color: #F44336; }     /* אדום */
    .score-unknown { background-color: #9E9E9E; } /* אפור */
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
        st.markdown("<div class='rtl-text'>השדות <strong>Score After</strong> ו־<strong>Score Before</strong> מחושבים מתוך Evaluation Table באופן אוטומטי.</div>", unsafe_allow_html=True)
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    st.subheader("🗂 ניתוח מפורט לפי עמוד")
    for i, row in filtered_df.iterrows():
        with st.expander(f"🔗 {row['Address']}"):
            st.markdown(f"**🔢 ציון לפני:** {row['Score Before']} | **אחרי:** {row['Score After']} | **פירוש:** {row['Score Explanation']}", unsafe_allow_html=True)
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**טבלת ניתוח לפני:**")
                st.text_area("Evaluation Table Before", row["Evaluation Table Before"], height=220)
            with col2:
                st.markdown("**טבלת ניתוח אחרי:**")
                st.text_area("Evaluation Table After", row["Evaluation Table After"], height=220)

            extra_fields = [
                ("🧠 המלצות E-E-A-T", "E-E-A-T Checklist"),
                ("🧩 ישויות מזוהות (Entities)", "Entities Extraction"),
                ("🎯 ניתוח כוונת חיפוש", "Intent Alignment"),
                ("📉 פערי תוכן מול מתחרים", "Content Gap vs Competitors"),
                ("🧩 הצעות סכמות (Schema)", "Schema Suggestions"),
                ("🛠 המלצות יישום ישיר (Rewriters & Optimizers)", "Rewriters & Optimizers")
            ]

            for label, field in extra_fields:
                with st.expander(label):
                    st.markdown(f"<div class='rtl-text'>{row.get(field, '')}</div>", unsafe_allow_html=True)
