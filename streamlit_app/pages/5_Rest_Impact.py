import streamlit as st
import numpy as np
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import summarize_rest_buckets, rank_rest_sensitivity


# ---------------------- PAGE ----------------------
st.title("⏱️ Rest Impact on Team Performance")

@st.cache_data
def cached_rest_data():
    return load_rest_data("data/all_teams.csv")

df = cached_rest_data()


# ---------------------- SIDEBAR ----------------------
st.sidebar.header("Filters")

metric_choice = st.sidebar.selectbox("Metric", ["Win %", "Expected Goals % (xG%)", "Goal Differential"])
home_filter = st.sidebar.radio("Game Location", ["All Games", "Home Only", "Away Only"])
team_highlight = st.sidebar.selectbox("Highlight Team", ["None"] + sorted(df["playerTeam"].unique()))

# Apply filters
filtered = df.copy()
if home_filter == "Home Only":
    filtered = filtered[filtered["home_or_away"] == "HOME"]
elif home_filter == "Away Only":
    filtered = filtered[filtered["home_or_away"] == "AWAY"]


# ---------------------- LEAGUE SUMMARY ----------------------
league_summary = summarize_rest_buckets(filtered)

metric_map = {
    "Win %": ("win_pct", "Win Percentage"),
    "Expected Goals % (xG%)": ("xg_pct", "Expected Goals %"),
    "Goal Differential": ("goal_diff_mean", "Goal Differential"),
}

metric_col, metric_label = metric_map[metric_choice]

x_labels = league_summary["rest_bucket"].astype(str).tolist()
y_values = league_summary[metric_col].values


# ---------------------- PLOT ----------------------
st.subheader(f"📈 League Performance Trend — {metric_choice}")

fig, ax = plt.subplots(figsize=(10, 6))
x = np.arange(len(x_labels))

ax.plot(x, y_values, marker="o", linewidth=2.5, label="League Avg")

# Add team overlay
if team_highlight != "None":
    team_df = filtered[filtered["playerTeam"] == team_highlight]
    team_summary = summarize_rest_buckets(team_df)
    if not team_summary.empty:
        team_map = dict(zip(team_summary["rest_bucket"].astype(str), team_summary[metric_col]))
        team_y = [team_map.get(lbl, np.nan) for lbl in x_labels]
        ax.plot(x, team_y, marker="o", linewidth=2.5, color="#d62728", label=team_highlight)

ax.set_xticks(x)
ax.set_xticklabels(x_labels)
ax.set_ylabel(metric_label)
ax.grid(True, alpha=0.3)
ax.legend()
st.pyplot(fig)


# ---------------------- TABLES ----------------------
st.subheader("📋 Performance by Rest Bucket")
st.dataframe(league_summary)


st.subheader("🏅 Rest Sensitivity Ranking (Win %)")
ranking = rank_rest_sensitivity(filtered)
st.dataframe(ranking)


st.caption("Data from MoneyPuck.com — computed using nhlRestEffects package.")
