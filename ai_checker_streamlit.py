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

    # Ensure all expected fields exist
    expected_fields = [
        "E-E-A-T Recommendations", "Entities Extraction", "Intent Alignment", "Content Gap vs Competitors",
        "Schema Suggestions", "H1 Rewriter", "Featured Snippet Optimizer", "CTA Optimizer",
        "Product Title Optimizer", "Product Description Optimizer"
    ]
    for field in expected_fields:
        if field not in df.columns:
            df[field] = ""

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
        st.markdown("<span title='שדות Score מחושבים אוטומטית מתוך Evaluation Table'>📝 שימו לב: <b>Score Before</b> ו־<b>Score After</b> מחושבים באופן אוטומטי מתוך טבלת הניתוח Evaluation Table.</span>", unsafe_allow_html=True)
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    # Show field panels per row
    st.subheader("🗂 ניתוח מפורט לפי עמוד")
    for i, row in filtered_df.iterrows():
        with st.expander(f"🔗 {row['Address']}"):
            st.markdown(f"**🔢 ציון לפני:** {row['Score Before']} | **אחרי:** {row['Score After']} | **פירוש:** {row['Score Explanation']}")

            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**טבלת ניתוח לפני:**")
                st.markdown(f"<div class='rtl-text'>{row['Evaluation Table Before'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)
            with col2:
                st.markdown("**טבלת ניתוח אחרי:**")
                st.markdown(f"<div class='rtl-text'>{row['Evaluation Table After'].replace(chr(10), '<br>')}</div>", unsafe_allow_html=True)

            for label, field in [
                ("🧠 המלצות E-E-A-T", "E-E-A-T Recommendations"),
                ("🧩 ישויות מזוהות (Entities)", "Entities Extraction"),
                ("🎯 ניתוח כוונת חיפוש", "Intent Alignment"),
                ("📉 פערי תוכן מול מתחרים", "Content Gap vs Competitors"),
                ("🧩 הצעות סכמות (Schema)", "Schema Suggestions")
            ]:
                if row[field]:
                    with st.expander(label):
                        st.markdown(f"<div class='rtl-text'>{row[field]}</div>", unsafe_allow_html=True)

            with st.expander("🛠 המלצות יישום ישיר (Rewriters & Optimizers)"):
                for label, field in [
                    ("🧾 כותרת H1 מומלצת", "H1 Rewriter"),
                    ("⭐️ Featured Snippet מוצע", "Featured Snippet Optimizer"),
                    ("🎯 קריאה לפעולה (CTA) מומלצת", "CTA Optimizer"),
                    ("🛍 כותרת מוצר מומלצת", "Product Title Optimizer"),
                    ("📝 תיאור מוצר מומלץ", "Product Description Optimizer")
                ]:
                    if row[field]:
                        st.markdown(f"**{label}:**", unsafe_allow_html=True)
                        st.markdown(f"<div class='rtl-text'>{row[field]}</div>", unsafe_allow_html=True)
