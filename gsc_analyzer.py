import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="📊 GSC Monthly Analyzer", layout="wide")

st.title("📊 Google Search Console Monthly Analyzer")

st.markdown("""
Upload your monthly GSC data in **Excel format** with the following columns:

- `URL`
- `Month 1 Clicks`, `Month 2 Clicks`
- `Month 1 Impr`, `Month 2 Impr`
- `Month 1 CTR`, `Month 2 CTR`
- `Month 1 Pos`, `Month 2 Pos`

🧠 This tool analyzes changes, explains trends, and detects possible **AI Overview** effects.
""")

file = st.file_uploader("📂 Upload Excel file", type=["xlsx"])


def calc_change(v1, v2):
    try:
        v1 = float(str(v1).strip('%'))
        v2 = float(str(v2).strip('%'))
        delta = v2 - v1
        pct = (delta / v1) * 100 if v1 != 0 else 0
        return round(v1, 2), round(v2, 2), round(delta, 2), round(pct, 1)
    except:
        return None, None, None, None


def ai_impact_logic(clicks1, clicks2, pos1, pos2, ctr1, ctr2, impr1, impr2):
    try:
        clicks1, clicks2 = float(clicks1), float(clicks2)
        pos1, pos2 = float(pos1), float(pos2)
        ctr1 = float(str(ctr1).strip('%'))
        ctr2 = float(str(ctr2).strip('%'))
        impr1, impr2 = float(impr1), float(impr2)

        pos_improved = pos2 <= pos1
        clicks_dropped = clicks2 < clicks1
        ctr_dropped = ctr2 < ctr1
        impressions_similar_or_up = impr2 >= (0.9 * impr1)

        if pos_improved and clicks_dropped and ctr_dropped and impressions_similar_or_up:
            return "🤖 Possible AI Overview impact"
        return "—"
    except:
        return "—"


# Main Logic
if file:
    try:
        df = pd.read_excel(file)

        required_cols = [
            "URL", "Month 1 Clicks", "Month 2 Clicks",
            "Month 1 Impr", "Month 2 Impr",
            "Month 1 CTR", "Month 2 CTR",
            "Month 1 Pos", "Month 2 Pos"
        ]

        if not all(col in df.columns for col in required_cols):
            st.error("❌ File is missing required columns. Please match the template exactly.")
        else:
            df["URL"] = df["URL"].astype(str)
            analysis_results = []

            # Loop over all URLs
            for idx, row in df.iterrows():
                result = {"URL": row["URL"]}
                metrics = {
                    "Clicks": ("Month 1 Clicks", "Month 2 Clicks", True),
                    "Impressions": ("Month 1 Impr", "Month 2 Impr", True),
                    "CTR (%)": ("Month 1 CTR", "Month 2 CTR", True),
                    "Position": ("Month 1 Pos", "Month 2 Pos", False)
                }

                for label, (col1, col2, higher_is_better) in metrics.items():
                    v1, v2, delta, pct = calc_change(row[col1], row[col2])
                    result[f"{label} M1"] = v1
                    result[f"{label} M2"] = v2
                    result[f"{label} Δ"] = delta
                    result[f"{label} %"] = pct
                    if v1 is not None:
                        if higher_is_better:
                            insight = "📈 Growth" if delta > 0 else "🔻 Drop" if delta < 0 else "➖ No Change"
                        else:
                            insight = "📉 Improvement" if delta < 0 else "🔺 Decline" if delta > 0 else "➖ No Change"
                        result[f"{label} Insight"] = insight

                result["AI Overview"] = ai_impact_logic(
                    row["Month 1 Clicks"], row["Month 2 Clicks"],
                    row["Month 1 Pos"], row["Month 2 Pos"],
                    row["Month 1 CTR"], row["Month 2 CTR"],
                    row["Month 1 Impr"], row["Month 2 Impr"]
                )

                analysis_results.append(result)

            results_df = pd.DataFrame(analysis_results)

            st.markdown("### 📋 Full URL Analysis Table")
            st.dataframe(results_df, use_container_width=True)

            # === Downloads ===
            st.markdown("### 📥 Download Full Report")

            # CSV Download
            csv = results_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV (Basic)", csv, "gsc_analysis.csv", "text/csv")

            # Excel Download with emojis preserved
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                results_df.to_excel(writer, index=False, sheet_name='Analysis')
            excel_data = output.getvalue()

            st.download_button(
                "📥 Download Excel (Recommended)",
                excel_data,
                "gsc_analysis.xlsx",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # === URL Drilldown ===
            st.markdown("### 🔍 Individual URL Insight")
            selected_url = st.selectbox("Choose a URL to inspect", results_df["URL"].unique())
            selected_row = results_df[results_df["URL"] == selected_url].iloc[0]

            st.markdown(f"#### 🔎 Detailed Analysis for `{selected_url}`")
            for metric in ["Clicks", "Impressions", "CTR (%)", "Position"]:
                st.markdown(
                    f"- **{metric}**: {selected_row[f'{metric} M1']} ➡️ {selected_row[f'{metric} M2']} | Δ {selected_row[f'{metric} Δ']} | {selected_row[f'{metric} %']}% — {selected_row[f'{metric} Insight']}"
                )

            if selected_row["AI Overview"] != "—":
                st.warning(selected_row["AI Overview"])
            else:
                st.info("No signs of AI Overview impact.")

            st.success("✅ Done. You can select another URL or upload a new file.")

    except Exception as e:
        st.error(f"❌ Error reading file: {e}")
