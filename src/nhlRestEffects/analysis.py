import pandas as pd

def add_rolling_metrics(df: pd.DataFrame, window: int = 5) -> pd.DataFrame:
    """
    Add rolling averages for expected goals, actual goals, and xG%.
    """
    df = df.copy()
    if window > 1:
        df["xGF_roll"] = df["xGF"].rolling(window).mean()
        df["xGA_roll"] = df["xGA"].rolling(window).mean()
        df["xG%_roll"] = df["xG%"].rolling(window).mean()
        df["GF_roll"] = df["goalsFor"].rolling(window).mean()
        df["GA_roll"] = df["goalsAgainst"].rolling(window).mean()
    return df


def summarize_back_to_backs(df: pd.DataFrame) -> pd.DataFrame | None:
    """
    Compare mean performance in back-to-back vs non-back-to-back games.
    Returns a DataFrame or None if insufficient data.
    """
    b2b = df[df["back_to_back"] == True]
    non = df[df["back_to_back"] == False]

    if b2b.empty or non.empty:
        return None

    b2b_stats = b2b[["xGF", "xGA", "goalsFor", "goalsAgainst"]].mean().rename("Back-to-Back")
    non_stats = non[["xGF", "xGA", "goalsFor", "goalsAgainst"]].mean().rename("Non-B2B")

    return pd.concat([non_stats, b2b_stats], axis=1).T


def get_back_to_back_pairs(df: pd.DataFrame) -> list:
    """
    Return paired tuples: (Game 1, Game 2) for each back-to-back sequence.
    """
    df = df.copy()
    df["next_days_rest"] = df["days_rest"].shift(-1)

    pairs = []
    for i in range(len(df) - 1):
        if df.loc[i + 1, "days_rest"] == 1:
            pairs.append((df.loc[i], df.loc[i + 1]))
    return pairs

def filter_goalie(df: pd.DataFrame, name: str, season=None, situation=None) -> pd.DataFrame:
    g = df[df["name"] == name].copy()

    if season and season != "All Seasons":
        g = g[g["season"] == season]

    if situation and situation != "All":
        g = g[g["situation"] == situation]

    g["GSAx"] = g["xGoals"] - g["goals"]
    g["save_pct"] = 1 - (g["goals"] / g["xOnGoal"])
    return g


def summarize_goalie(g: pd.DataFrame) -> dict:
    games_by_season = g.groupby("season")["games_played"].max()
    total_games = int(games_by_season.sum())

    shots = g["xOnGoal"].sum()
    goals = g["goals"].sum()
    xga = g["xGoals"].sum()
    gsax = g["GSAx"].sum()

    save_pct = 1 - (goals / shots) if shots > 0 else float("nan")

    return {
        "Games Played": total_games,
        "Shots Faced": int(shots),
        "Goals Allowed": int(goals),
        "Expected Goals (xGA)": round(xga, 2),
        "Save %": f"{save_pct:.3f}",
        "Total GSAx": round(gsax, 2),
    }

def segment_goalie_fatigue(df: pd.DataFrame) -> pd.DataFrame:
    """Assign season fatigue tiers based on sequential game workload."""
    df = df.sort_values("games_played").reset_index(drop=True)

    n = len(df)

    if n >= 12:
        df["segment"] = pd.qcut(df.index, q=4, labels=["Q1", "Q2", "Q3", "Q4"])
    elif n >= 6:
        df["segment"] = pd.qcut(df.index, q=2, labels=["Early Season", "Late Season"])
    else:
        df["segment"] = "All Games"

    df["save_pct"] = 1 - (df["goals"] / df["xOnGoal"].clip(lower=1))
    df["GSAx"] = df["xGoals"] - df["goals"]

    return df

import numpy as np
import pandas as pd

def assign_rest_bucket(days: float) -> str:
    """Categorize rest days into discrete fatigue buckets."""
    if pd.isna(days):
        return np.nan
    if days <= 0:
        return "0 (B2B)"
    if days == 1:
        return "1 day"
    if days == 2:
        return "2 days"
    if days == 3:
        return "3 days"
    return "4+ days"


def summarize_rest_buckets(df: pd.DataFrame) -> pd.DataFrame:
    """Returns rest bucket summary with win%, xG%, and goal differential."""
    if df.empty:
        return pd.DataFrame(columns=["rest_bucket", "games", "win_pct", "xg_pct", "goal_diff_mean"])

    grouped = df.groupby("rest_bucket")
    summary = grouped.agg(
        games=("win", "count"),
        win_pct=("win", lambda x: x.mean() * 100),
        xg_pct=("xG%", "mean"),
        goal_diff_mean=("goal_diff", "mean")
    ).reset_index()

    order = ["0 (B2B)", "1 day", "2 days", "3 days", "4+ days"]
    summary["rest_bucket"] = pd.Categorical(summary["rest_bucket"], order, ordered=True)
    return summary.sort_values("rest_bucket")


def rank_rest_sensitivity(df: pd.DataFrame) -> pd.DataFrame:
    """Ranks teams by difference between tired (0–1 days) and rested (3+ days) win%."""
    rows = []
    for team, g in df.groupby("playerTeam"):
        buckets = g.groupby("rest_bucket")["win"].mean() * 100
        
        tired = buckets.reindex(["0 (B2B)", "1 day"]).dropna().mean()
        rested = buckets.reindex(["3 days", "4+ days"]).dropna().mean()

        if pd.isna(tired) or pd.isna(rested):
            continue

        rows.append({
            "Team": team,
            "Tired Win % (0–1 days)": tired,
            "Rested Win % (3+ days)": rested,
            "Rested – Tired (pp)": rested - tired
        })

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows).sort_values("Rested – Tired (pp)", ascending=False)

def compute_days_rest(df: pd.DataFrame) -> pd.DataFrame:
    """Compute days of rest based on consecutive game dates per team."""
    df = df.copy()

    # Ensure datetimes
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    # Sort so diff works properly
    df = df.sort_values(["playerTeam", "gameDate"]).reset_index(drop=True)

    # Compute rest time in days
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days

    return df
