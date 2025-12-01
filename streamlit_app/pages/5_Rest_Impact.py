import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import compute_days_rest

st.title("⏱️ Rest Impact Analysis")


# ---------------------- Date Cleaner ----------------------
def fix_dates(df):
    """Ensure all gameDate values convert into usable timestamps."""
    if pd.api.types.is_datetime64_any_dtype(df["gameDate"]):
        return df

    # If numeric, treat as unix
    if pd.api.types.is_numeric_dtype(df["gameDate"]):
        df["gameDate"] = pd.to_datetime(df["gameDate"], unit="s", errors="coerce")
        return df

    # Otherwise treat as string dates
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
    return df


# ---------------------- Load & Cache Data ----------------------
@st.cache_data
def cached_rest_data():
    df = load_rest_data("data/all_teams.csv").copy()

    df = fix_dates(df)

    # Sort for proper rest calculation
    df = df.sort_values(["playerTeam", "gameDate"])
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Create rest bins
    df["rest_bin"] = df["days_rest"].apply(lambda x:
        "0" if x == 0 else
        "1" if x == 1 else
        "2" if x == 2 else
        "3+" if pd.notna(x) else None
    )

    # Convert metrics to numeric safely
    df["xG%"] = pd.to_numeric(df["xG%"], errors="coerce")
    df["win"] = pd.to_numeric(df["win"], errors="coerce").fillna(0).astype(int)

    return df


df = cached_rest_data()


# ---------------------- Sidebar Filters ----------------------
teams = sorted(df["playerTeam"].unique())
team = st.sidebar.selectbox("Select Team", teams, index=teams.index("STL") if "STL" in teams else 0)

seasons = sorted(df["season"].unique())
season_options = ["All Seasons"] + seasons
selected_season = st.sidebar.selectbox("Season", season_options)


# Filter based on selection
filtered_df = df[df["playerTeam"] == team].copy()
if selected_season != "All Seasons":
    filtered_df = filtered_df[filtered_df["season"] == selected_season]


# ---------------------- DEBUG (can enable if needed) ----------------------
st.write("Rest bin counts in filtered data: ", filtered_df["rest_bin"].value_counts())


# ---------------------- Summary Section ----------------------
st.subheader(f"📋 Summary for {team} — {selected_season}")

if filtered_df.empty:
    st.warning("No data available for this selection.")
    st.stop()


# ---------------------- xG% vs Rest ----------------------
st.write("### 📈 Expected Goals % by Rest")

summary = filtered_df.groupby("rest_bin")["xG%"].mean().reset_index()

# Force order and show empty bins
order = ["0", "1", "2", "3+"]
summary = summary.set_index("rest_bin").reindex(order)
summary["xG%"] = summary["xG%"].fillna(0.0)
summary = summary.reset_index()

fig1, ax1 = plt.subplots(figsize=(8, 4))
ax1.bar(summary["rest_bin"], summary["xG%"], color="#1f77b4")
ax1.set_ylabel("Average xG%")
ax1.set_title("xG% Performance Relative to Rest Days")
st.pyplot(fig1)

st.dataframe(summary.style.format({"xG%": "{:.2f}"}))


# ---------------------- Win Rate vs Rest ----------------------
st.write("### 🏆 Win Rate by Rest")

win_df = filtered_df.groupby("rest_bin")["win"].mean().reset_index()
win_df = win_df.set_index("rest_bin").reindex(order)
win_df["win"] = win_df["win"].fillna(0.0)
win_df = win_df.reset_index()

fig2, ax2 = plt.subplots(figsize=(8, 4))
ax2.bar(win_df["rest_bin"], win_df["win"], color="#2ca02c")
ax2.set_ylabel("Win Rate")
ax2.set_title("Win Percentage Based on Rest Days")
st.pyplot(fig2)

st.dataframe(win_df.style.format({"win": "{:.2%}"}))


# ---------------------- Conclusion ----------------------
st.info(
    f"This visualization helps identify how rest affects performance. "
    f"Use the sidebar to compare different seasons or teams."
)

st.caption("Data powered by MoneyPuck & nhlRestEffects package.")
