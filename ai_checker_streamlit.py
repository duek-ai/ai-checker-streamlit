import streamlit as st
import pandas as pd
import io

st.set_page_config(layout="wide", page_title="AI Evaluation Viewer")

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
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📊 דוח SEO מעילים – ציון וניתוח לפי 7 עקרונות")

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

    def display_table_or_fallback(text):
        cleaned_text = text.strip()
        if "\\begin" in cleaned_text or "\begin" in cleaned_text:
            st.latex(cleaned_text)
        elif "|" in cleaned_text and cleaned_text.count("|") >= 2:
            try:
                df = pd.read_csv(io.StringIO(cleaned_text), sep='|', engine='python', skiprows=[1])
                df = df.dropna(axis=1, how='all')
                df = df.dropna(how='all')
                df.columns = [col.strip() for col in df.columns]
                st.dataframe(
                    df.style.set_table_styles([
                        {'selector': 'th', 'props': [('text-align', 'right')]},
                        {'selector': 'td', 'props': [('text-align', 'right')]}
                    ]),
                    use_container_width=True
                )
            except Exception:
                st.warning("⚠️ לא ניתן להציג טבלה, הפורמט אינו תקני")
                st.markdown(f"<div class='rtl-text'>{cleaned_text}</div>", unsafe_allow_html=True)
        else:
            st.warning("⚠️ אין תוכן להצגה כטבלה")
            st.markdown(f"<div class='rtl-text'>{cleaned_text}</div>", unsafe_allow_html=True)

    # כרטיסיות נפרדות לפי עמוד
    st.subheader("🗂 ניתוח מפורט לפי עמוד")
    for _, row in filtered_df.iterrows():
        with st.expander(f"{row['Address']}"):
            st.markdown(
                f"**🔢 ציון לפני:** {row['Score Before']} | **אחרי:** {row['Score After']} | **פירוש:** {row['Score Explanation']}"
            )
            col1, col2 = st.columns(2)

            with col1:
                st.markdown("**טבלת ניתוח לפני:**")
                display_table_or_fallback(row["Evaluation Table Before"])

            with col2:
                st.markdown("**טבלת ניתוח אחרי:**")
                display_table_or_fallback(row["Evaluation Table After"])

            if row.get("E-E-A-T Checker") and str(row["E-E-A-T Checker"]).strip():
                with st.expander("🧠 המלצות E-E-A-T"):
                    st.markdown(f"<div class='rtl-text'>{row['E-E-A-T Checker']}</div>", unsafe_allow_html=True)

            if row.get("Entities Extraction") and str(row["Entities Extraction"]).strip():
                with st.expander("🧩 ישויות מזוהות (Entities)"):
                    st.markdown("<div class='rtl-text'>", unsafe_allow_html=True)
                    for line in str(row["Entities Extraction"]).split(","):
                        st.markdown(f"- {line.strip()}")
                    st.markdown("</div>", unsafe_allow_html=True)

            if row.get("Intent Alignment") and str(row["Intent Alignment"]).strip():
                with st.expander("🎯 ניתוח כוונת חיפוש"):
                    st.markdown(f"<div class='rtl-text'>{row['Intent Alignment']}</div>", unsafe_allow_html=True)

            if row.get("Content Gap vs Competitors") and str(row["Content Gap vs Competitors"]).strip():
                with st.expander("📉 פערי תוכן מול מתחרים"):
                    st.markdown(f"<div class='rtl-text'>{row['Content Gap vs Competitors']}</div>", unsafe_allow_html=True)

            if row.get("Schema Suggestions") and str(row["Schema Suggestions"]).strip():
                with st.expander("🧩 הצעות סכמות (Schema)"):
                    st.markdown(f"<div class='rtl-text'>{row['Schema Suggestions']}</div>", unsafe_allow_html=True)

            optimization_fields = [
                ("H1 Rewriter", "🔠 כותרת H1 מומלצת"),
                ("Featured Snippet Optimizer", "⭐ Featured Snippet מוצע"),
                ("CTA Optimizer", "🎯 קריאה לפעולה (CTA) מומלצת"),
                ("Product Title Optimizer", "🏷️ כותרת מוצר מומלצת"),
                ("Product Description Optimizer", "📝 תיאור מוצר מומלץ")
            ]

            has_optimizations = any(row.get(field) and str(row[field]).strip() for field, _ in optimization_fields)
            if has_optimizations:
                with st.expander("🛠 המלצות יישום ישיר (Rewriters & Optimizers)"):
                    st.markdown("<div class='rtl-text'>", unsafe_allow_html=True)
                    for field, label in optimization_fields:
                        if row.get(field) and str(row[field]).strip():
                            st.markdown(f"<div class='rtl-text'><b>{label}</b></div>", unsafe_allow_html=True)
                            st.markdown(f"<div class='rtl-text'>{row[field]}</div>", unsafe_allow_html=True)
                            st.markdown("<br>", unsafe_allow_html=True)

    # הורדה
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        filtered_df.to_excel(writer, index=False, sheet_name='Evaluation')

    st.download_button("📥 הורד את הקובץ כ-Excel", data=output.getvalue(), file_name="evaluation_report.xlsx")
