import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(layout="wide")

# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_goalie_data(path="data/goalies_allseasons.csv"):
    df = pd.read_csv(path)

    # Ensure dates format correctly
    if "gameDate" in df.columns:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="ignore")

    # Compute core metrics
    df["GSAx"] = df["xGoals"] - df["goals"]
    df["save_pct"] = 1 - (df["goals"] / df["xOnGoal"])
    df["rest_days"] = df.groupby("name")["gameDate"].diff().dt.days.fillna("Start")

    # Collapse too-large gap values
    df["rest_cat"] = df["rest_days"].apply(lambda x:
                                           "Start" if x == "Start"
                                           else "Back-to-Back (1 Day)" if x == 1
                                           else "Short Rest (2 Days)" if x == 2
                                           else "Normal Rest (3–4 Days)" if 3 <= x <= 4
                                           else "Extended Rest (5+ Days)"
                                          )
    return df


# ---------------------- PAGE FUNCTION ----------------------
def goalie_fatigue_page():

    st.title("🥵 Goalie Fatigue & Workload Impact Analysis")

    df = load_goalie_data()

    # Sidebar filters
    st.sidebar.header("Filters")
    goalies = sorted(df["name"].unique())

    selected_goalie = st.sidebar.selectbox("Select Goalie", ["League Average"] + goalies)

    # Filter if user selects an individual goalie
    if selected_goalie != "League Average":
        df_filtered = df[df["name"] == selected_goalie].copy()
        title = f"📌 Performance Breakdown — {selected_goalie}"
    else:
        df_filtered = df.copy()
        title = "📌 League-Wide Fatigue Performance Trends"

    st.header(title)

    # Summary Table
    st.subheader("📊 Performance by Rest Level")

    summary = df_filtered.groupby("rest_cat").agg(
        Games=("games_played", "count"),
        Avg_SavePct=("save_pct", "mean"),
        Avg_GSAx=("GSAx", "mean"),
        Avg_xGA=("xGoals", "mean"),
        Avg_Shots=("xOnGoal", "mean"),
    ).round(3)

    st.dataframe(summary, use_container_width=True)

    # ---------------------- BAR CHART: SAVE % ----------------------
    st.subheader("🧤 Save Percentage vs Rest Level")

    fig1, ax1 = plt.subplots(figsize=(10, 5))
    ax1.bar(summary.index, summary["Avg_SavePct"], color="#1f77b4")
    ax1.set_ylabel("Save %")
    ax1.set_ylim(0, max(summary["Avg_SavePct"]) + 0.05)
    ax1.grid(True, alpha=0.3)
    plt.xticks(rotation=20)

    st.pyplot(fig1)

    # ---------------------- BAR CHART: GSAx ----------------------
    st.subheader("🔥 Goals Saved Above Expected (GSAx) vs Rest Level")

    fig2, ax2 = plt.subplots(figsize=(10, 5))
    colors = ["#2ca02c" if v > 0 else "#d62728" for v in summary["Avg_GSAx"]]
    ax2.bar(summary.index, summary["Avg_GSAx"], color=colors)
    ax2.axhline(0, linestyle="--", color="gray")
    ax2.set_ylabel("Avg. GSAx (per game)")
    ax2.grid(True, alpha=0.3)
    plt.xticks(rotation=20)

    st.pyplot(fig2)

    # ---------------------- LINE TREND: GSAx by Chronological Games ----------------------
    st.subheader("📈 Game-to-Game Fatigue Trend")

    df_filtered = df_filtered.sort_values("gameDate")

    fig3, ax3 = plt.subplots(figsize=(12, 5))
    ax3.plot(df_filtered["gameDate"], df_filtered["GSAx"], marker="o", linewidth=2)
    ax3.axhline(0, linestyle="--", color="gray")
    ax3.set_ylabel("GSAx Per Game")
    ax3.grid(True, alpha=0.35)

    st.pyplot(fig3)

    st.markdown("---")
    st.caption("Data Source: MoneyPuck.com — processed for analytics")


