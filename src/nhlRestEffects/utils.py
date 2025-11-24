import pandas as pd

def clean_team_abbrev(abbrev: str) -> str:
    """Standardize NHL team abbreviations."""
    mapping = {
        "T.B.": "TBL", "TB": "TBL", "TAM": "TBL",
        "S.J.": "SJS", "SJ": "SJS", "SAN": "SJS",
        "N.J.": "NJD", "NJ": "NJD", "NJ DEVILS": "NJD",
        "L.A.": "LAK", "LA": "LAK", "LOS": "LAK",
        "M.T.L.": "MTL", "MTL.": "MTL",
        "N.Y.I.": "NYI", "N.Y.R.": "NYR",
        "W.P.G.": "WPG", "V.G.K.": "VGK",
    }

    abbrev = abbrev.strip()
    return mapping.get(abbrev, abbrev.replace(".", "").upper())


def get_team_logo_url(team_abbrev: str) -> str:
    """Return official NHL team logo URL."""
    clean = team_abbrev.replace(".", "").upper()
    return f"https://assets.nhle.com/logos/nhl/svg/{clean}_light.svg"


def get_headshot_url(player_id) -> str | None:
    """Return NHL headshot image URL from player ID."""
    if pd.isna(player_id):
        return None
    return f"https://assets.nhle.com/mugs/nhl/{int(player_id)}.png"