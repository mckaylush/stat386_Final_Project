def clean_goalie_df(df):
    df = df.copy()
    df.rename(columns={
        "name": "player",
        "games_played": "games",
        "ongoal": "shots_on_goal",
        "xGoals": "expected_goals",
        "goals": "goals_allowed",
    }, inplace=True)

    df["save_pct"] = 1 - (df["goals_allowed"] / df["shots_on_goal"]).fillna(0)
    df["expected_save_pct"] = 1 - (df["expected_goals"] / df["shots_on_goal"]).fillna(0)
    df["GSAx"] = df["expected_goals"] - df["goals_allowed"]

    return df
