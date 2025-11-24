# fetch_goalie_data.py

import itertools
from pathlib import Path

import pandas as pd
import requests
from io import StringIO


# Seasons you care about (MoneyPuck uses the first year of the season)
SEASONS = list(range(2016, 2025))   # 2016 = 2016–17, ..., 2024 = 2024–25

# 32 current team abbreviations (Arizona is ARI, Utah is UTA if/when added)
TEAMS = [
    "ANA", "ARI", "BOS", "BUF", "CAR", "CBJ", "CGY", "CHI",
    "COL", "DAL", "DET", "EDM", "FLA", "LAK", "MIN", "MTL",
    "NJD", "NSH", "NYI", "NYR", "OTT", "PHI", "PIT", "SEA",
    "SJS", "STL", "TBL", "TOR", "UTA", "VAN", "VGK", "WPG", "WSH",
]

BASE_URL = (
    "https://moneypuck.com/moneypuck/playerData/"
    "seasonSummary/{season}/regular/teams/goalies/{team}.csv"
)


def fetch_one(season: int, team: str) -> pd.DataFrame | None:
    url = BASE_URL.format(season=season, team=team)
    print(f"Fetching {season} {team} -> {url}")
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
    except Exception as e:
        print(f"  !! Skipping {season} {team}: {e}")
        return None

    df = pd.read_csv(StringIO(r.text))
    df["season"] = season
    df["team"] = team
    return df


def main():
    frames = []

    for season, team in itertools.product(SEASONS, TEAMS):
        df = fetch_one(season, team)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        raise RuntimeError("No data downloaded – check URLs or seasons/teams list")

    full = pd.concat(frames, ignore_index=True)

    # Make sure data folder exists
    data_dir = Path("data")
    data_dir.mkdir(exist_ok=True)

    out_path = data_dir / "goalies_allseasons.csv"
    full.to_csv(out_path, index=False)
    print(f"\nSaved combined goalie data to {out_path.resolve()}")


if __name__ == "__main__":
    main()

