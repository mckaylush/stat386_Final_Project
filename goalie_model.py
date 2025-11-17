import streamlit as st
import pandas as pd
import numpy as np

@st.cache_data
def load_data():
    df = pd.read_csv("data/goalies_allseasons.csv")

    df["save_pct"] = 1 - (df["goals"] / df["xOnGoal"].clip(lower=1))
    df["high_sv"] = 1 - (df["highDangerGoals"] / df["highDangerShots"].clip(lower=1))
    df["med_sv"] = 1 - (df["mediumDangerGoals"] / df["mediumDangerShots"].clip(lower=1))
    df["low_sv"] = 1 - (df["lowDangerGoals"] / df["lowDangerShots"].clip(lower=1))
    df["GSAx"] = df["xGoals"] - df["goals"]
    df["GSAx_game"] = df["GSAx"] / df["games_played"].clip(lower=1)

    return df

def model_page():

    st.title("🧤 Goalie Style & Strength Profile")

    df = load_data()

    goalies = sorted(df["name"].unique())
    selected = st.selectbox("Select a Goalie", goalies)

    g = df[df["name"] == selected]

    # Compute averages for goalie vs league
    metrics = ["save_pct", "high_sv", "med_sv", "low_sv", "GSAx_game"]

    goalie_avg = g[metrics].mean()
    league_avg = df[metrics].mean()

    # Compute z-scores
    stdev = df[metrics].std()
    z = (goalie_avg - league_avg) / stdev

    result_df = pd.DataFrame({"Metric": metrics, "Value": goalie_avg.values, "Z-Score": z.values})
    result_df["Value"] = result_df["Value"].round(3)
    result_df["Z-Score"] = result_df["Z-Score"].round(2)

    st.subheader("🔍 Performance Relative to League")
    st.dataframe(result_df.set_index("Metric"))

    # Classification rules
    st.subheader("🧠 Style Interpretation")

    style = ""

    if z["high_sv"] > 0.7:
        style += "🧱 **High-Danger Specialist:** Excellent in traffic and breakaways.\n\n"

    if z["low_sv"] < -0.6:
        style += "🥅 **Soft Goal Risk:** Below average on low-danger shots.\n\n"

    if z["GSAx_game"] > 0.6:
        style += "🔥 **Game Stealer:** Frequently saves more than expected.\n\n"

    if abs(z["save_pct"]) < 0.2:
        style += "⚖️ **Steady and Predictable:** League-average outcomes but low volatility.\n\n"

    if z["save_pct"] > 0.6 and z["high_sv"] > 0.6 and z["low_sv"] > 0.6:
        style = "🏆 **Elite All-Around Performer — top tier across the board.**"

    if style.strip() == "":
        style = "📌 **Balanced Goalie — No single extreme strengths or weaknesses.**"

    st.write(style)

    # Simple bar visualization
    st.subheader("📊 Standardized Strength Chart")

    st.bar_chart(pd.DataFrame({"Z-Score": z}), use_container_width=True)


st.caption("Data Source: MoneyPuck.com")
