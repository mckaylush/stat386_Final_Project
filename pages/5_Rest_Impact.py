import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ---------------------- DATA LOADER ----------------------
@st.cache_data
def load_rest_data(path: str = "all_teams.csv") -> pd.DataFrame:
    df = pd.read_csv(path)
# --------- TEAM NAME NORMALIZATION ---------
    team_map = {
        "N.J": "NJD",
        "NJ": "NJD",
        "N.J.": "NJD",
        
        "S.J": "SJS",
        "SJ": "SJS",
        "S.J.": "SJS",

        "T.B": "TBL",
        "TB": "TBL",
        "T.B.": "TBL",

        "L.A": "LAK",
        "LA": "LAK",
        "L.A.": "LAK",

        "M.T.L": "MTL",
        "MON": "MTL",

        "N.Y.I": "NYI",
        "N.Y.R": "NYR",
        "NY": "NYR"  # rare case, but safe

        # Add any weird ones if they appear in your dataset
    }

    df["playerTeam"] = df["playerTeam"].replace(team_map)

    # Parse dates
    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d", errors="coerce")
    df = df.dropna(subset=["gameDate"])

    # Keep team-level, all-strength rows (like your main app)
    if "position" in df.columns:
        df = df[df["position"] == "Team Level"]
    if "situation" in df.columns:
        df = df[df["situation"] == "all"]

    # Basic outcome metrics
    df["win"] = df["goalsFor"] > df["goalsAgainst"]
    df["goal_diff"] = df["goalsFor"] - df["goalsAgainst"]

    # xG% per game
    denom = df["xGoalsFor"] + df["xGoalsAgainst"]
    df["xg_pct_game"] = np.where(denom > 0, df["xGoalsFor"] / denom * 100, np.nan)

    # Compute rest days per team
    df = df.sort_values(["playerTeam", "gameDate"])
    df["rest_days"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    # Bucket rest days
    def bucket_rest(d):
        if pd.isna(d):
            return np.nan
        if d <= 0:
            return "0 (B2B)"
        elif d == 1:
            return "1 day"
        elif d == 2:
            return "2 days"
        elif d == 3:
            return "3 days"
        else:
            return "4+ days"

    df["rest_bucket"] = df["rest_days"].apply(bucket_rest)
    df = df.dropna(subset=["rest_bucket"])

    return df



# ---------------------- SUMMARY HELPER ----------------------
def summarize_by_rest(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate league or team data by rest bucket.
    Returns columns: rest_bucket, games, win_pct, xg_pct, goal_diff_mean
    """
    if df.empty:
        return pd.DataFrame(
            columns=["rest_bucket", "games", "win_pct", "xg_pct", "goal_diff_mean"]
        )

    grouped = df.groupby("rest_bucket")
    rows = []
    for bucket, g in grouped:
        games = len(g)
        win_pct = g["win"].mean() * 100 if games > 0 else np.nan
        xg_pct = g["xg_pct_game"].mean() if games > 0 else np.nan
        goal_diff_mean = g["goal_diff"].mean() if games > 0 else np.nan

        rows.append(
            {
                "rest_bucket": bucket,
                "games": games,
                "win_pct": win_pct,
                "xg_pct": xg_pct,
                "goal_diff_mean": goal_diff_mean,
            }
        )

    summary = pd.DataFrame(rows)

    # Order buckets nicely
    order = ["0 (B2B)", "1 day", "2 days", "3 days", "4+ days"]
    summary["rest_bucket"] = pd.Categorical(summary["rest_bucket"], categories=order, ordered=True)
    summary = summary.sort_values("rest_bucket")

    return summary


# ---------------------- TEAM RANKING HELPER ----------------------
def build_rest_ranking(df: pd.DataFrame) -> pd.DataFrame:
    """
    For each team, compare 'tired' (0–1 days rest) vs 'rested' (3+ days rest) win%.
    Returns a ranking DataFrame.
    """
    rows = []
    for team, g in df.groupby("playerTeam"):
        # Summaries per bucket
        by_bucket = g.groupby("rest_bucket")["win"].mean() * 100

        tired_buckets = [b for b in ["0 (B2B)", "1 day"] if b in by_bucket.index]
        rested_buckets = [b for b in ["3 days", "4+ days"] if b in by_bucket.index]

        if not tired_buckets or not rested_buckets:
            # Not enough variety in rest days for this team
            continue

        tired_win = by_bucket[tired_buckets].mean()
        rested_win = by_bucket[rested_buckets].mean()
        diff = rested_win - tired_win

        rows.append(
            {
                "Team": team,
                "Tired Win % (0–1 days)": tired_win,
                "Rested Win % (3+ days)": rested_win,
                "Rested – Tired (pp)": diff,
            }
        )

    if not rows:
        return pd.DataFrame(
            columns=["Team", "Tired Win % (0–1 days)", "Rested Win % (3+ days)", "Rested – Tired (pp)"]
        )

    ranking = pd.DataFrame(rows)
    ranking = ranking.sort_values("Rested – Tired (pp)", ascending=False)
    return ranking


# ---------------------- PAGE FUNCTION ----------------------
def rest_impact_page():
    st.title("⏱️ Rest Impact on Team Performance")

    df = load_rest_data()

    # ---------- SIDEBAR FILTERS ----------
    st.sidebar.header("Filters")

    metric_label = st.sidebar.selectbox(
        "Metric to analyze",
        ["Win %", "Expected Goals % (xG%)", "Goal Differential"],
    )

    home_filter = st.sidebar.radio(
        "Game location",
        ["All games", "Home only", "Away only"],
    )

    playoff_filter = st.sidebar.radio(
        "Games included",
        ["Regular season only", "Regular season + playoffs"],
    )

    team_choices = ["None (league curve only)"] + sorted(df["playerTeam"].unique())
    highlight_team = st.sidebar.selectbox("Highlight team (optional)", team_choices)

    # ---------- APPLY FILTERS ----------
    data = df.copy()

    # Playoffs
    if playoff_filter == "Regular season only" and "playoffGame" in data.columns:
        # assume 0/1 indicator
        data = data[data["playoffGame"] == 0]

    # Home/away
    if home_filter == "Home only":
        data = data[data["home_or_away"] == "HOME"]
    elif home_filter == "Away only":
        data = data[data["home_or_away"] == "AWAY"]

    if data.empty:
        st.warning("No games left after applying the current filters.")
        return

    # ---------- LEAGUE SUMMARY ----------
    league_summary = summarize_by_rest(data)
    if league_summary.empty:
        st.warning("Not enough data by rest-bucket to show results.")
        return

    metric_col_map = {
        "Win %": ("win_pct", "Win percentage"),
        "Expected Goals % (xG%)": ("xg_pct", "Expected goals share (xG%)"),
        "Goal Differential": ("goal_diff_mean", "Average goal differential"),
    }
    metric_col, metric_long_label = metric_col_map[metric_label]

    # Prepare x,y for league curve
    x_labels = league_summary["rest_bucket"].astype(str).tolist()
    x_positions = np.arange(len(x_labels))
    league_y = league_summary[metric_col].values

    # ---------- MAIN PLOT ----------
    st.subheader(f"📈 League Rest Curve — {metric_label}")

    fig, ax = plt.subplots(figsize=(10, 6))

    ax.plot(
        x_positions,
        league_y,
        marker="o",
        linewidth=2.5,
        label="League average",
        color="#1f77b4",
    )

    # Team overlay
    team_summary = None
    if highlight_team != "None (league curve only)":
        team_data = data[data["playerTeam"] == highlight_team]
        team_summary = summarize_by_rest(team_data)

        if not team_summary.empty:
            # Align team values to same x order
            team_map = dict(zip(team_summary["rest_bucket"].astype(str), team_summary[metric_col]))
            team_y = [team_map.get(lbl, np.nan) for lbl in x_labels]

            ax.plot(
                x_positions,
                team_y,
                marker="o",
                linewidth=2.5,
                label=highlight_team,
                color="#d62728",
            )

    ax.set_xticks(x_positions)
    ax.set_xticklabels(x_labels)
    ax.set_xlabel("Days Rest Before Game")
    ax.set_ylabel(metric_long_label)
    ax.grid(True, alpha=0.3)
    ax.legend()

    st.pyplot(fig)

    # ---------- QUICK TEXT SUMMARY ----------
    st.subheader("🧠 Quick Takeaways")

    # league: compare low rest vs high rest
    low_rest = league_summary[league_summary["rest_bucket"].isin(["0 (B2B)", "1 day"])]
    high_rest = league_summary[league_summary["rest_bucket"].isin(["3 days", "4+ days"])]

    if not low_rest.empty and not high_rest.empty:
        low_val = low_rest[metric_col].mean()
        high_val = high_rest[metric_col].mean()
        delta = high_val - low_val

        if metric_label == "Goal Differential":
            st.write(
                f"- League teams average **{high_val:.3f}** goal diff on 3+ days rest "
                f"vs **{low_val:.3f}** on 0–1 days rest "
                f"(**Δ {delta:+.3f} goals per game**)."
            )
        else:
            st.write(
                f"- League average **{metric_label}** is **{high_val:.2f}** on 3+ days rest "
                f"vs **{low_val:.2f}** on 0–1 days rest "
                f"(**Δ {delta:+.2f} points**)."
            )

    if team_summary is not None and not team_summary.empty:
        t_low = team_summary[team_summary["rest_bucket"].isin(["0 (B2B)", "1 day"])]
        t_high = team_summary[team_summary["rest_bucket"].isin(["3 days", "4+ days"])]
        if not t_low.empty and not t_high.empty:
            t_low_val = t_low[metric_col].mean()
            t_high_val = t_high[metric_col].mean()
            t_delta = t_high_val - t_low_val

            st.write(
                f"- **{highlight_team}** specifically: {metric_label} is "
                f"**{t_high_val:.2f}** on 3+ days rest vs **{t_low_val:.2f}** on 0–1 days rest "
                f"(**Δ {t_delta:+.2f}**)."
            )

    # ---------- LEAGUE TABLE ----------
    st.subheader("📋 League Rest Performance Table")

    table = league_summary.copy()
    table = table.rename(
        columns={
            "rest_bucket": "Rest Bucket",
            "games": "Games",
            "win_pct": "Win %",
            "xg_pct": "xG %",
            "goal_diff_mean": "Avg Goal Diff",
        }
    )

    st.dataframe(
        table.style.format(
            {
                "Win %": "{:.1f}",
                "xG %": "{:.1f}",
                "Avg Goal Diff": "{:.3f}",
            }
        ),
        use_container_width=True,
    )

    # ---------- TEAM RANKING ----------
    st.subheader("🏅 Rest Sensitivity by Team (Win %)")

    ranking = build_rest_ranking(data)
    if ranking.empty:
        st.info("Not enough variety in rest days per team to build a ranking.")
    else:
        st.caption(
            "Positive values mean the team performs better when rested (3+ days) than when tired (0–1 days)."
        )
        st.dataframe(
            ranking.head(15).style.format(
                {
                    "Tired Win % (0–1 days)": "{:.1f}",
                    "Rested Win % (3+ days)": "{:.1f}",
                    "Rested – Tired (pp)": "{:+.1f}",
                }
            ),
            use_container_width=True,
        )

    st.markdown("---")
    st.caption("Data source: MoneyPuck.com — rest buckets computed from `gameDate` and `playerTeam`.")
