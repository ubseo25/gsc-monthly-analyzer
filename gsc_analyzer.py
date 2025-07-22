import streamlit as st
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="📊 Search Console Analyzer ", layout="wide")

st.title("📊 Google Search Console Analyzer (Updated by UB)")

st.markdown("""
Upload your monthly GSC data in **Excel format** with the following columns:

- `URL`
- `Current Month Clicks`, `Previous Month Clicks`
- `Current Month Impr`, `Previous Month Impr`
- `Current Month CTR`, `Previous Month CTR`
- `Current Month Pos`, `Previous Month Pos`

🧠 This tool analyzes changes, explains trends, and detects possible **AI Overview** effects.
""")

# 👇 Show expected structure before upload
st.markdown("### 📑 Required Excel Format Example")
sample_data = {
    "URL": ["https://example.com/page1"],
    "Current Month Clicks": [1200],
    "Previous Month Clicks": [1450],
    "Current Month Impr": [10000],
    "Previous Month Impr": [11500],
    "Current Month CTR": ["12.0%"],
    "Previous Month CTR": ["12.6%"],
    "Current Month Pos": [8.4],
    "Previous Month Pos": [7.9],
}
st.dataframe(pd.DataFrame(sample_data))
st.info("📌 Make sure your file has **exact column names** and values formatted like above.")

file = st.file_uploader("📂 Upload Excel File", type=["xlsx"])


def calc_change(v1, v2, is_percentage=False, is_position=False):
    try:
        if is_percentage:
            v2 = float(str(v2).strip('%'))
            v1 = float(str(v1).strip('%'))
        else:
            v2 = float(v2)
            v1 = float(v1)

        if is_position and v2 == 0:
            return v1, 0, float('inf'), -100

        delta = v1 - v2
        pct_change = ((v1 - v2) / v2) * 100 if v2 != 0 else 0
        if is_position:
            pct_change = ((v2 - v1) / v2) * 100 if v2 != 0 else 0

        return round(v1, 2), round(v2, 2), round(delta, 2), round(pct_change, 1)
    except:
        return None, None, None, None


def ai_impact_logic(clicks1, clicks2, pos1, pos2, ctr1, ctr2, impr1, impr2):
    try:
        clicks1, clicks2 = float(clicks1), float(clicks2)
        pos1, pos2 = float(pos1), float(pos2)
        ctr1 = float(str(ctr1).strip('%'))
        ctr2 = float(str(ctr2).strip('%'))
        impr1, impr2 = float(impr1), float(impr2)

        pos_disappeared = pos2 == 0
        pos_improved = pos2 < pos1 and not pos_disappeared
        clicks_dropped = clicks2 < clicks1
        ctr_dropped = ctr2 < ctr1
        impressions_stable = impr2 >= 0.9 * impr1

        if (pos_improved or pos_disappeared) and clicks_dropped and ctr_dropped and impressions_stable:
            return "🤖 Possible AI Overview impact"
        return "—"
    except:
        return "—"


if file:
    try:
        df = pd.read_excel(file)

        required_cols = [
            "URL", "Current Month Clicks", "Previous Month Clicks",
            "Current Month Impr", "Previous Month Impr",
            "Current Month CTR", "Previous Month CTR",
            "Current Month Pos", "Previous Month Pos"
        ]

        if not all(col in df.columns for col in required_cols):
            st.error("❌ File is missing required columns.")
        else:
            df["URL"] = df["URL"].astype(str)
            output_data = []

            for idx, row in df.iterrows():
                result = {"URL": row["URL"]}
                metrics = {
                    "Clicks": ("Current Month Clicks", "Previous Month Clicks", True, False, False),
                    "Impressions": ("Current Month Impr", "Previous Month Impr", True, False, False),
                    "CTR (%)": ("Current Month CTR", "Previous Month CTR", True, True, False),
                    "Position": ("Current Month Pos", "Previous Month Pos", False, False, True)
                }

                for label, (c1, c2, high_better, pct, pos) in metrics.items():
                    v1, v2, delta, perc = calc_change(row[c1], row[c2], pct, pos)
                    result[f"{label} PM"] = v1
                    result[f"{label} CM"] = v2
                    result[f"{label} Δ"] = delta
                    result[f"{label} %"] = perc

                    if v1 is not None:
                        if pos and v2 == 0:
                            insight = "❌ Disappeared"
                        elif pos:
                            insight = "📈 Improved" if delta < 0 else "🔻 Declined" if delta > 0 else "➖ No Change"
                        else:
                            insight = "📈 Growth" if delta > 0 and high_better else "🔻 Drop" if delta < 0 and high_better else "➖ No Change"
                        result[f"{label} Insight"] = insight

                result["AI Overview"] = ai_impact_logic(
                    row["Current Month Clicks"], row["Previous Month Clicks"],
                    row["Current Month Pos"], row["Previous Month Pos"],
                    row["Current Month CTR"], row["Previous Month CTR"],
                    row["Current Month Impr"], row["Previous Month Impr"]
                )
                output_data.append(result)

            final_df = pd.DataFrame(output_data)

            st.markdown("### 📋 URL-Level Comparison")
            st.dataframe(final_df, use_container_width=True)

            # Download options
            csv = final_df.to_csv(index=False).encode('utf-8')
            st.download_button("⬇️ Download CSV", csv, "gsc_analysis.csv", "text/csv")

            buffer = BytesIO()
            with pd.ExcelWriter(buffer, engine="xlsxwriter") as writer:
                final_df.to_excel(writer, index=False, sheet_name="Analysis")
            st.download_button("📥 Download Excel", buffer.getvalue(), "gsc_analysis.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

            # URL Drilldown
            st.markdown("### 🔍 Detailed View for One URL")
            selected_url = st.selectbox("Select a URL", final_df["URL"].unique())
            r = final_df[final_df["URL"] == selected_url].iloc[0]

            st.markdown(f"#### 📊 `{selected_url}`")
            for metric in ["Clicks", "Impressions", "CTR (%)", "Position"]:
                st.markdown(
                    f"- **{metric}**: {r[f'{metric} PM']} ➡️ {r[f'{metric} CM']} | Δ {r[f'{metric} Δ']} | {r[f'{metric} %']}% — {r[f'{metric} Insight']}"
                )

            if r["AI Overview"] != "—":
                st.warning(r["AI Overview"])
            else:
                st.info("No clear sign of AI Overview impact.")

    except Exception as e:
        st.error(f"❌ Failed to process file: {e}")
