import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.utils import clean_team_abbrev

st.title("⏱️ Rest Impact Analysis")

@st.cache_data
def load_data():
    try:
        df = load_rest_data("../../data/all_teams.csv").copy()
    except Exception as e:
        st.error(f"❌ Could not load file: {e}")
        return pd.DataFrame()

    # --- Fix dates properly (YYYYMMDD format) ---
    df["gameDate"] = (
        df["gameDate"]
        .astype(str)
        .str.extract(r"(\d{8})")[0]
    )
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")

    # --- Clean team abbreviations ---
    df["playerTeam"] = df["playerTeam"].astype(str).apply(clean_team_abbrev)

    # --- Use already computed xG% from package ---
    if "xG%" in df.columns:
        df["xG"] = pd.to_numeric(df["xG%"], errors="coerce")
    elif "xGoalsPercentage" in df.columns:
        df["xG"] = pd.to_numeric(df["xGoalsPercentage"], errors="coerce")
    else:
        st.error("❌ No expected goals column found.")
        return pd.DataFrame()

    # Drop any unusable rows
    return df.dropna(subset=["xG", "rest_bucket", "gameDate"])


df = load_data()

# ---------------------- Check Data ----------------------
if df.empty:
    st.error("❌ Dataset loaded, but contains no usable data. Check formatting.")
    st.stop()

# Debug display
st.write("📌 Loaded rows:", len(df))

# ---------------------- Sidebar ----------------------
teams = sorted(df["playerTeam"].unique())
seasons = sorted(df["season"].astype(str).unique())

selected_team = st.sidebar.selectbox("Select Team", teams)
selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons)

# ---------------------- Filter ----------------------
team_df = df[df["playerTeam"] == selected_team].copy()
if selected_season != "All Seasons":
    team_df = team_df[team_df["season"].astype(str) == selected_season]

if team_df.empty:
    st.warning("⚠ No data for this team/season.")
    st.stop()

# ---------------------- Bucket Counts ----------------------
st.caption(f"Rest bucket counts for {selected_team}")
st.write(team_df["rest_bucket"].value_counts().sort_index())

# ---------------------- Plot ----------------------
st.subheader(f"📉 Expected Goals % by Rest Days — {selected_team}")

rest_order = ["0", "1", "2", "3+"]

summary = team_df.groupby("rest_bucket")["xG"].mean().reindex(rest_order).fillna(0)

fig, ax = plt.subplots(figsize=(10, 4))
ax.bar(rest_order, summary.values, edgecolor="black")

for x, v in zip(rest_order, summary.values):
    ax.text(x, v + 0.01, f"{v:.2f}", ha="center")

ax.axhline(summary.mean(), linestyle="--", color="red", alpha=0.5)
ax.set_ylabel("Avg xG%")
ax.set_xlabel("Rest Days")
ax.set_title(f"{selected_team} — Rest Impact ({selected_season})")

st.pyplot(fig)

# ---------------------- League Ranking ----------------------
st.subheader("📋 Fatigue Sensitivity Ranking")

league = (
    df.groupby(["playerTeam", "rest_bucket"])["xG"]
    .mean()
    .unstack()
    .reindex(columns=rest_order)
    .fillna(0)
)

league["Fatigue Impact (0 → 3+)"] = league["3+"] - league["0"]
league = league.sort_values("Fatigue Impact (0 → 3+)")

st.dataframe(league.style.format("{:.3f}"))

st.caption("📊 Data sourced from MoneyPuck.com — Powered by nhlRestEffects.")
