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

    # פילטרים
    st.sidebar.header("🎯 סינון")
    indexability_filter = st.sidebar.selectbox("Indexability", options=["הכל"] + df["Indexability"].dropna().unique().tolist())
    weak_score = st.sidebar.checkbox("ציון After נמוך מ-6")

    filtered_df = df.copy()
    if indexability_filter != "הכל":
        filtered_df = filtered_df[filtered_df["Indexability"] == indexability_filter]
    if weak_score:
        filtered_df = filtered_df[filtered_df["Score After"] < 6]

    # בחירת עמודות דינמית
    st.subheader("📄 בחר/י אילו עמודות להציג בטבלת עמודים")
    selected_columns = st.multiselect(
        "בחר/י שדות להצגה:",
        options=df.columns.tolist(),
        default=["Address", "Title 1", "Score Before", "Score After", "Score Explanation"]
    )

    if selected_columns:
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    # כרטיסיות נפרדות לפי עמוד
    st.subheader("🗂 ניתוח מפורט לפי עמוד")
    for i, row in filtered_df.iterrows():
        with st.expander(f"{row['Address']}"):
            st.markdown(f"**🔢 ציון לפני:** {row['Score Before']} | **אחרי:** {row['Score After']} | **פירוש:** {row['Score Explanation']}")
            col1, col2 = st.columns(2)
            with col1:
            st.markdown("**טבלת ניתוח לפני:**")
            try:
                df_before = pd.read_csv(io.StringIO(row["Evaluation Table Before"]), sep='|', engine='python')
                df_before = df_before.dropna(axis=1, how='all')
                df_before.columns = [col.strip() for col in df_before.columns]
                st.dataframe(df_before.style.set_properties(**{'text-align': 'right'}), use_container_width=True)
            except:
                st.markdown(f"<div class='rtl-text'>{row['Evaluation Table Before']}</div>", unsafe_allow_html=True)
        with col2:
            st.markdown("**טבלת ניתוח אחרי:**")
            try:
                df_after = pd.read_csv(io.StringIO(row["Evaluation Table After"]), sep='|', engine='python')
                df_after = df_after.dropna(axis=1, how='all')
                df_after.columns = [col.strip() for col in df_after.columns]
                st.dataframe(df_after.style.set_properties(**{'text-align': 'right'}), use_container_width=True)
            except:
                st.markdown(f"<div class='rtl-text'>{row['Evaluation Table After']}</div>", unsafe_allow_html=True)
                    st.markdown("""
                        <div class="rtl-text">
                    """ + row["Evaluation Table Before"] + """
                        </div>
                    """, unsafe_allow_html=True)
            with col2:
                st.markdown("**טבלת ניתוח אחרי:**")
                if row["Evaluation Table After"].strip().startswith("\begin"):
                    st.latex(row["Evaluation Table After"])
                else:
                    st.markdown("""
                        <div class="rtl-text">
                    """ + row["Evaluation Table After"] + """
                        </div>
                    """, unsafe_allow_html=True)

    # הורדה
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Evaluation')
    st.download_button("📥 הורד את הקובץ כ-Excel", data=output.getvalue(), file_name="evaluation_report.xlsx")
