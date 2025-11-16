import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_goalie_shot_data(path="data/goalies_allseasons.csv"):
    """
    Expects a per-shot (or per-event) goalie dataset with at least:
      - name (goalie name)
      - season
      - situation
      - shot_x / shot_y (or xCord / yCord / x / y) for coordinates
      - optional: isGoal/goal flag
      - optional: xGoals (per shot xG)
    If coordinates aren't present, the page will show a warning.
    """
    df = pd.read_csv(path)

    # Try to parse dates if present
    if "gameDate" in df.columns:
        df["gameDate"] = pd.to_datetime(df["gameDate"], errors="coerce")

    return df


# Helper to find coordinate columns flexibly
def detect_coord_columns(df: pd.DataFrame):
    cand_x = ["shot_x", "xCord", "x", "xc", "xcoord"]
    cand_y = ["shot_y", "yCord", "y", "yc", "ycoord"]

    x_col = next((c for c in cand_x if c in df.columns), None)
    y_col = next((c for c in cand_y if c in df.columns), None)
    return x_col, y_col


# Helper to detect goal flag & xG column
def detect_goal_and_xg(df: pd.DataFrame):
    goal_candidates = ["isGoal", "goal", "is_goal", "goalFlag"]
    xg_candidates = ["xGoals", "xG", "shotXG", "xgoal"]

    goal_col = next((c for c in goal_candidates if c in df.columns), None)
    xg_col = next((c for c in xg_candidates if c in df.columns), None)

    return goal_col, xg_col


# ---------------------- DRAW RINK (MoneyPuck-ish) ----------------------
def draw_rink(ax):
    """
    Simple, MoneyPuck-style full-rink outline with center line and circles.
    Coordinates assumed to be roughly NHL standard:
        x in [-100, 100], y in [-42.5, 42.5]
    Offensive direction is to the RIGHT (positive x).
    """
    ax.set_xlim(-100, 100)
    ax.set_ylim(-42.5, 42.5)
    ax.set_aspect("equal")

    # Outer rink
    rink = plt.Rectangle(
        (-100, -42.5),
        200,
        85,
        linewidth=2,
        edgecolor="black",
        facecolor="white",
        zorder=0,
    )
    ax.add_patch(rink)

    # Center line
    ax.plot([0, 0], [-42.5, 42.5], color="red", linewidth=1.5, zorder=1)

    # "Blue lines" (approximate at x = +/- 25)
    ax.plot([25, 25], [-42.5, 42.5], color="blue", linewidth=1, alpha=0.6, zorder=1)
    ax.plot([-25, -25], [-42.5, 42.5], color="blue", linewidth=1, alpha=0.6, zorder=1)

    # Center circle
    center_circle = plt.Circle((0, 0), 15, fill=False, color="blue", linewidth=1, alpha=0.6)
    ax.add_patch(center_circle)

    # Faceoff circles (offensive/defensive zones, simplified)
    for x0 in [69, -69]:
        circle = plt.Circle((x0, 22), 15, fill=False, color="red", linewidth=0.8, alpha=0.5)
        ax.add_patch(circle)
        circle = plt.Circle((x0, -22), 15, fill=False, color="red", linewidth=0.8, alpha=0.5)
        ax.add_patch(circle)

    # Goal creases (just small rectangles near x = +/- 89)
    crease = plt.Rectangle((89, -4), 4, 8, linewidth=1, edgecolor="red", facecolor="none", alpha=0.8)
    ax.add_patch(crease)
    crease = plt.Rectangle((-93, -4), 4, 8, linewidth=1, edgecolor="red", facecolor="none", alpha=0.8)
    ax.add_patch(crease)

    ax.axis("off")


# ---------------------- PAGE FUNCTION ----------------------
def goalie_shotmap_page():
    st.title("📍 NHL Goalie Shot Maps")

    df = load_goalie_shot_data()

    # Detect coordinate columns
    x_col, y_col = detect_coord_columns(df)
    if x_col is None or y_col is None:
        st.error(
            "Shot coordinates not found in the data.\n\n"
            "I looked for columns like `shot_x/shot_y`, `xCord/yCord`, or `x/y`."
        )
        st.info("Once your shot-level dataset has coordinates, this page will start working automatically.")
        return

    goal_col, xg_col = detect_goal_and_xg(df)

    # ---------------------- SIDEBAR FILTERS ----------------------
    st.sidebar.header("Shot Map Filters")

    goalies = sorted(df["name"].dropna().unique())
    seasons = sorted(df["season"].dropna().unique()) if "season" in df.columns else []
    situations = sorted(df["situation"].dropna().unique()) if "situation" in df.columns else []

    selected_goalie = st.sidebar.selectbox("Goalie", goalies)
    selected_season = st.sidebar.selectbox("Season", ["All Seasons"] + seasons) if seasons else "All Seasons"
    selected_situation = st.sidebar.selectbox("Situation", ["All"] + situations) if situations else "All"

    view_mode = st.sidebar.radio("View Mode", ["Scatter", "Heatmap"])
    shot_filter = st.sidebar.radio("Shot Type Filter", ["All Shots", "Goals Only", "High-Danger Only"])

    # ---------------------- FILTER DATA ----------------------
    g = df[df["name"] == selected_goalie].copy()

    if selected_season != "All Seasons" and "season" in g.columns:
        g = g[g["season"] == selected_season]

    if selected_situation != "All" and "situation" in g.columns:
        g = g[g["situation"] == selected_situation]

    # Basic sanity check
    if g.empty:
        st.warning("No shots found for this goalie with the selected filters.")
        return

    # Filter on shot type
    # Assume we might have 'shotDanger' or danger counts; best effort:
    if shot_filter == "Goals Only" and goal_col is not None:
        g = g[g[goal_col] == 1]
    elif shot_filter == "High-Danger Only":
        if "shotDanger" in g.columns:
            g = g[g["shotDanger"].str.lower() == "high"]
        elif "highDangerShots" in g.columns:
            # If only aggregated high-danger counts exist, we can't filter per shot, so just warn:
            st.info(
                "High-danger only filter requested, but no per-shot danger labels found.\n"
                "Showing all shots instead."
            )

    if g.empty:
        st.warning("No shots remaining after applying shot-type filter.")
        return

    # Build arrays
    xs = g[x_col].astype(float)
    ys = g[y_col].astype(float)

    # xG for sizing
    if xg_col is not None:
        xg = g[xg_col].astype(float)
        # normalize to reasonable marker sizes
        min_size = 20
        max_size = 200
        if xg.max() > 0:
            sizes = min_size + (xg / xg.max()) * (max_size - min_size)
        else:
            sizes = np.full_like(xg, (min_size + max_size) / 2)
    else:
        sizes = np.full(len(g), 60.0)

    # Colors: default blue for non-goals, red for goals if flag exists
    if goal_col is not None:
        colors = np.where(g[goal_col].astype(int) == 1, "red", "blue")
    else:
        colors = "blue"

    # ---------------------- HEADER / TEXT ----------------------
    st.subheader(f"Shot Map for {selected_goalie}")

    desc_bits = [f"Mode: **{view_mode}**"]
    if selected_season != "All Seasons":
        desc_bits.append(f"Season: **{selected_season}**")
    if selected_situation != "All":
        desc_bits.append(f"Situation: **{selected_situation}**")
    desc_bits.append(f"Shots shown: **{len(g)}**")

    st.markdown(" • ".join(desc_bits))

    # ---------------------- PLOT ----------------------
    fig, ax = plt.subplots(figsize=(10, 5))
    draw_rink(ax)

    if view_mode == "Scatter":
        # Scatter only, xG-sized circles
        ax.scatter(xs, ys, s=sizes, c=colors, alpha=0.7, edgecolor="black", linewidth=0.3)

    else:  # Heatmap
        # Use hexbin-style density, with offensive direction to the right
        hb = ax.hexbin(xs, ys, gridsize=30, cmap="Reds", mincnt=1, alpha=0.8)
        cb = fig.colorbar(hb, ax=ax, shrink=0.8)
        cb.set_label("Shot Density")

    ax.set_title("Offensive Direction →", fontsize=12, loc="right")
    st.pyplot(fig)

    st.markdown("---")
    st.caption("Data source: MoneyPuck.com • Rink is approximate, MoneyPuck-style full rink.")
