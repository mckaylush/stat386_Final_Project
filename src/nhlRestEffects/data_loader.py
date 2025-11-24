import pandas as pd
from .utils import clean_team_abbrev

def load_team_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)
    df["opposingTeam"] = df["opposingTeam"].apply(clean_team_abbrev)

    df = df[(df["position"] == "Team Level") & (df["situation"] == "all")].copy()

    df["gameDate"] = pd.to_datetime(df["gameDate"], format="%Y%m%d")
    df = df[df["gameDate"].dt.year >= 2016]

    df = df.sort_values(by=["playerTeam", "gameDate"]).reset_index(drop=True)

    df.rename(columns={"xGoalsFor": "xGF", "xGoalsAgainst": "xGA"}, inplace=True)
    df["xG%"] = (df["xGF"] / (df["xGF"] + df["xGA"])) * 100

    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days
    df["back_to_back"] = (df["days_rest"] == 1).fillna(False)

    df["win"] = df["goalsFor"] > df["goalsAgainst"]

    df["season_label"] = df["season"].astype(str)

    return df


def load_goalie_data(path="data/goalies_allseasons.csv") -> pd.DataFrame:
    df = pd.read_csv(path)

    if "gameDate" in df.columns:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="ignore")

    return df

from .utils import clean_team_abbrev
from .analysis import assign_rest_bucket

def load_rest_data(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)

    df["playerTeam"] = df["playerTeam"].apply(clean_team_abbrev)
    df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")
    df = df.dropna(subset=["gameDate"])

    df = df[(df["position"] == "Team Level") & (df["situation"] == "all")].copy()

    df["xG%"] = df["xGoalsFor"] / (df["xGoalsFor"] + df["xGoalsAgainst"]) * 100
    df["goal_diff"] = df["goalsFor"] - df["goalsAgainst"]
    df["win"] = df["goalsFor"] > df["goalsAgainst"]

    df = df.sort_values(["playerTeam", "gameDate"])
    df["rest_days"] = df.groupby("playerTeam")["gameDate"].diff().dt.days
    df["rest_bucket"] = df["rest_days"].apply(assign_rest_bucket)

    return df.dropna(subset=["rest_bucket"])

import pandas as pd
import numpy as np

def enrich_with_rest_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()

    rename_map = {
    "xGoalsPercentage": "xG%",
    "goalsFor": "goalsFor",
    "goalsAgainst": "goalsAgainst"
    }
    df = df.rename(columns=rename_map)

    # Ensure sorting by team + date
    df["gameDate"] = pd.to_datetime(df["gameDate"])
    df = df.sort_values(["playerTeam", "gameDate"])

    # Compute days rest by team
    df["days_rest"] = df.groupby("playerTeam")["gameDate"].diff().dt.days.fillna(3)

    # Assign rest buckets
    df["rest_bucket"] = df["days_rest"].apply(lambda d:
        "0 (B2B)" if d <= 0 else
        "1 day" if d == 1 else
        "2 days" if d == 2 else
        "3 days" if d == 3 else
        "4+ days"
    )

    # Compute win column
    df["win"] = (df["goalsFor"] > df["goalsAgainst"]).astype(int)

    # Compute goal differential
    df["goal_diff"] = df["goalsFor"] - df["goalsAgainst"]

    # Compute xG%
    if "xGoalsFor" in df.columns and "xGoalsAgainst" in df.columns:
        df["xG%"] = df["xGoalsFor"] / (df["xGoalsFor"] + df["xGoalsAgainst"])
    else:
        df["xG%"] = np.nan

    return df
