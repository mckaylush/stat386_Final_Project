# src/nhlRestEffects/__init__.py

from .data_loader import load_team_data, load_goalie_data, load_rest_data
from .utils import get_team_logo_url, get_headshot_url

# Only expose analysis functions after import (avoids circular import errors)
from .analysis import (
    add_rolling_metrics,
    summarize_back_to_backs,
    get_back_to_back_pairs,
    filter_goalie,
    summarize_goalie,
    segment_goalie_fatigue,
    assign_rest_bucket,
    summarize_rest_buckets,
    rank_rest_sensitivity,
    enrich_with_rest_metrics
)

__all__ = [
    "load_team_data",
    "load_goalie_data",
    "load_rest_data",
    "get_team_logo_url",
    "get_headshot_url",
    "add_rolling_metrics",
    "summarize_back_to_backs",
    "get_back_to_back_pairs",
    "filter_goalie",
    "summarize_goalie",
    "segment_goalie_fatigue",
    "assign_rest_bucket",
    "summarize_rest_buckets",
    "rank_rest_sensitivity",
    "enrich_with_rest_metrics",
]
