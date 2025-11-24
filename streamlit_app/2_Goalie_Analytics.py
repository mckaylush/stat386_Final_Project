import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_goalie_data
from nhlRestEffects.utils import get_headshot_url, get_team_logo_url
from nhlRestEffects.analysis import filter_goalie, summarize_goalie

st.title("🎯 NHL Goalie Analytics Dashboard")

@st.cache_data
def load_cached_goalies():
    return load_goalie_data()

df = load_cached_goalies()


# ---------------------- SIDEBAR FILTERS ----------------------
st.sidebar.header("Filters")

mode = st.sidebar.radio("Mode", ["Single Goalie View", "Compare Two Goalies"])

goalies = sorted(df["name"].unique())
seasons = sorted(df["season"].unique())
situations = sorted(df["situation"].unique())

selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)
selected_situation = st.sidebar.selectbox("Game Situation", ["All"] + situations)

selected_goalie = st.sidebar.selectbox("Primary Goalie", goalies)

if mode == "Compare Two Goalies":
    selected_goalie_2 = st.sidebar.selectbox("Compare With", [g for g in goalies if g != selected_goalie])
else:
    selected_goalie_2 = None


# ---------------------- FILTER GOALIES USING PACKAGE ----------------------
goalie1 = filter_goalie(df, selected_goalie, selected_season, selected_situation)
goalie2 = filter_goalie(df, selected_goalie_2, selected_season, selected_situation) if selected_goalie_2 else None


# ---------------------- HEADER SECTION ----------------------
if mode == "Single Goalie View":
    st.header(f"📌 Goalie: {selected_goalie}")

    col_img, col_info = st.columns([1, 3])
    with col_img:
        st.image(get_headshot_url(goalie1["playerId"].iloc[0]), width=180)

    with col_info:
        st.write(f"**Team(s):** {', '.join(sorted(goalie1['team'].unique()))}")
        st.write(f"**Seasons:** {', '.join(sorted(goalie1['season'].astype(str).unique()))}")
        st.write(f"**Situation Filter:** {selected_situation}")

else:
    st.header(f"⚔️ Comparison: {selected_goalie} vs {selected_goalie_2}")


# ---------------------- SUMMARY TABLE ----------------------
st.subheader("📊 Summary Statistics")

if mode == "Single Goalie View":
    st.dataframe(pd.DataFrame(summarize_goalie(goalie1), index=[0]))
else:
    st.dataframe(pd.DataFrame(
        [summarize_goalie(goalie1), summarize_goalie(goalie2)],
        index=[selected_goalie, selected_goalie_2]
    ))


# ---------------------- VISUALIZATIONS ----------------------
st.subheader("📊 GSAx by Season")

g1_season = goalie1.groupby("season", as_index=False)["GSAx"].sum()
fig, ax = plt.subplots(figsize=(10, 5))
ax.bar(g1_season["season"].astype(str), g1_season["GSAx"], label=selected_goalie)

if goalie2 is not None:
    g2_season = goalie2.groupby("season", as_index=False)["GSAx"].sum()
    ax.bar(g2_season["season"].astype(str), g2_season["GSAx"], label=selected_goalie_2, alpha=0.6)

ax.axhline(0, linestyle="--", color="gray")
ax.set_ylabel("Total GSAx")
ax.grid(True, alpha=0.3)
ax.legend()

st.pyplot(fig)


# ---------------------- SCATTER PLOT ----------------------
st.subheader("🥅 Expected vs Actual Goals Allowed")

color_map = {
    "all": "#1f77b4", "5on5": "#2ca02c", "5on4": "#9467bd",
    "4on5": "#d62728", "other": "#ff7f0e"
}

fig2, ax2 = plt.subplots(figsize=(8, 5))

for situation, group in goalie1.groupby("situation"):
    ax2.scatter(group["xGoals"], group["goals"], s=80, alpha=0.8,
                label=f"{selected_goalie} — {situation}",
                color=color_map.get(str(situation).lower(), "#7f7f7f"))

if goalie2 is not None and not goalie2.empty:
    for situation, group in goalie2.groupby("situation"):
        ax2.scatter(group["xGoals"], group["goals"], s=90, marker="X", alpha=0.8,
                    label=f"{selected_goalie_2} — {situation}",
                    color=color_map.get(str(situation).lower(), "#aaaaaa"))

ax2.plot([0, df["xGoals"].max()], [0, df["goals"].max()],
         linestyle="--", color="gray", label="Expected = Actual")

ax2.set_xlabel("Expected Goals Against (xGA)")
ax2.set_ylabel("Actual Goals Allowed")
ax2.grid(True, alpha=0.3)
ax2.legend(bbox_to_anchor=(1.02, 1), loc='upper left')

st.pyplot(fig2)

st.markdown("---")
st.caption("Data source: MoneyPuck.com — powered by `nhlRestEffects` package.")