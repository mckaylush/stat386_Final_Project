import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

@st.cache_data
def load_data():
    df = pd.read_csv("data/goalies_allseasons.csv")

    # compute actual save%
    df["actual_sv"] = 1 - (df["goals"] / df["xOnGoal"])
    df["actual_sv"] = df["actual_sv"].clip(0, 1)

    # expected save% baseline (league average across similar danger levels)
    df["expected_sv"] = 1 - (
        (df["highDangerShots"] * 0.30 +
         df["mediumDangerShots"] * 0.10 +
         df["lowDangerShots"] * 0.02) 
        / df["unblocked_shot_attempts"].clip(lower=1)
    )

    df["expected_sv"] = df["expected_sv"].clip(0, 1)

    # performance delta
    df["delta_sv"] = df["actual_sv"] - df["expected_sv"]

    return df


def model_page():
    st.title("🧤 Goalie Expected vs Actual Performance")

    df = load_data()

    goalies = sorted(df["name"].unique())
    selected = st.selectbox("Select a Goalie", goalies)

    g = df[df["name"] == selected].copy()

    if g.empty:
        st.warning("No data available.")
        return

    # Aggregate by season
    season_summary = g.groupby("season")[["actual_sv", "expected_sv", "delta_sv"]].mean()

    st.subheader(f"📈 Seasonal Performance: {selected}")

    fig, ax = plt.subplots(figsize=(10,5))
    ax.plot(season_summary.index, season_summary["actual_sv"], marker="o", label="Actual Save %")
    ax.plot(season_summary.index, season_summary["expected_sv"], marker="o", label="Expected Save %", linestyle="--")
    ax.axhline(season_summary["expected_sv"].mean(), color="gray", linestyle=":", label="League Baseline")
    ax.set_ylabel("Save %")
    ax.set_ylim(0.85, 1.0)
    ax.grid(alpha=0.3)
    ax.legend()

    st.pyplot(fig)

    # 📊 Table
    st.subheader("📊 Numbers by Season")
    st.dataframe(season_summary.style.format("{:.3f}"))

    # Interpretation
    avg_delta = season_summary["delta_sv"].mean()

    st.subheader("🧠 Interpretation")

    if avg_delta > 0.010:
        st.success(f"🔥 {selected} consistently **outperformed expectations** (+{avg_delta:.3f}).")
    elif avg_delta < -0.010:
        st.error(f"❄️ {selected} performed **below expected level** ({avg_delta:.3f}).")
    else:
        st.info(f"⚖️ {selected} performed **very close to expected level** ({avg_delta:.3f}).")
