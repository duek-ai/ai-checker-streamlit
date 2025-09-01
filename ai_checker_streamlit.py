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
        st.dataframe(filtered_df[selected_columns], use_container_width=True)
    else:
        st.warning("לא נבחרו עמודות להצגה")

    st.markdown("""
        <p class='rtl-text'>🧠 <b>שימו לב:</b> השדות <code>Score Before</code> ו-<code>Score After</code> מחושבים מתוך טבלת הניתוח באופן אוטומטי.</p>
    """, unsafe_allow_html=True)

    # Show evaluation tables if available
    for i, row in filtered_df.iterrows():
        with st.expander(f"🔗 {row['Address']}"):
            st.markdown(f"**ציון לפני:** {row['Score Before']} | **אחרי:** {row['Score After']} | **פירוש:** {row['Score Explanation']}")
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**טבלת ניתוח לפני:**")
                st.markdown("<div class='rtl-text'>", unsafe_allow_html=True)
                st.text(row["Evaluation Table Before"])
                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                st.markdown("**טבלת ניתוח אחרי:**")
                st.markdown("<div class='rtl-text'>", unsafe_allow_html=True)
                st.text(row["Evaluation Table After"])
                st.markdown("</div>", unsafe_allow_html=True)

            # Optional: Display E-E-A-T and other semantic field values as RTL tables
            semantic_fields = [
                "E-E-A-T Recommendation", "Entities Extraction", "Intent Alignment", "Content Gap vs Competitors",
                "Schema Suggestions", "H1 Rewriter", "Featured Snippet Optimizer", "CTA Optimizer",
                "Product Title Optimizer", "Product Description Optimizer"
            ]

            for field in semantic_fields:
                if field in row and pd.notna(row[field]):
                    with st.expander(f"📌 {field}"):
                        st.markdown("<div class='rtl-text'>", unsafe_allow_html=True)
                        st.text(row[field])
                        st.markdown("</div>", unsafe_allow_html=True)
