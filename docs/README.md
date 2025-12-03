# 🏒 nhlRestEffects

**nhlRestEffects** is a Python package designed to analyze how schedule-related factors — particularly **rest days** and **back-to-back games** — impact NHL team performance.  
The package includes tools for data loading, cleaning, analysis, and visualization.

---

## 🚀 Features

- 📂 Load NHL team-level datasets
- 🧹 Clean & preprocess MoneyPuck-style data
- 📈 Analyze rest-based performance trends
- 📊 Generate visualizations for:
  - Expected goals (xG)
  - Rest-day effects
  - Back-to-back performance drops
- 🧪 Designed for research, analytics, and sports data science workflows

---

## 🔧 Installation

Clone the repository and install the package in editable mode:

```sh
git clone https://github.com/emclayburn/stat386_Final_Project.git
cd stat386_Final_Project
pip install -e .
```
--- 

📦 Package Structure

```sh
nhlRestEffects/
├── __init__.py
├── data_loader.py
├── cleaning.py
├── analysis.py
└── visualization.py
```

other supporting folders:

```sh
streamlit_app/    # Streamlit dashboard UI
data/             # Data files (not bundled in PyPI)
examples/         # Optional usage examples
```

---

🧠 Usage Examples

Import the package

```python
import nhlRestEffects
```

Load data for a specific team

```python
from nhlRestEffects import load_team_data

df = load_team_data("TBL")  # Tampa Bay Lightning
print(df.head())
```

Run a rest-based performance analysis

```python
from nhlRestEffects import analyze_rest_effects

results = analyze_rest_effects(df)
print(results)
```

Create a visual

```python
from nhlRestEffects import plot_rest_performance

plot_rest_performance(df, team="TBL")
```

---

📊 Streamlit Dashboard

The repository includes a Streamlit application using this package.

Run it with:

```sh
streamlit run streamlit_app/Home.py
```

---

# Tutorial

📘 Tutorial: How to Analyze NHL Rest Effects with nhlRestEffects

This tutorial walks through a complete analytics workflow using nhlRestEffects, from loading MoneyPuck data to visualizing rest-day performance trends. No prior setup is required beyond installing the package.

## 1️⃣ Load the Data

nhlRestEffects makes it easy to import and clean MoneyPuck team-level game data:
```python
import pandas as pd
from nhlRestEffects.data_loader import load_rest_data

df = load_rest_data("data/all_teams.csv")
df.head()
```

This automatically:

- Parses game dates

- Normalizes team abbreviations

- Computes expected goals percentage (xG%)

- Computes goal differential & win/loss

- Calculates rest days and assigns rest buckets

## 2️⃣ Understanding Rest Buckets

The package converts raw rest_days into NHL-style rest categories:

| rest_bucket | Meaning                    |
| ----------- | -------------------------- |
| `"0"`       | Back-to-back (0 days rest) |
| `"1"`       | 1 day rest                 |
| `"2"`       | 2 days rest                |
| `"3+"`      | 3 or more days rest        |


To see how these are created:

```python
df[["playerTeam", "gameDate", "rest_days", "rest_bucket"]].head()
```

## 3️⃣ Summarize Team Performance by Rest Level

Use the built-in summarizer to compare how a team performs at each rest level:

```python
from nhlRestEffects.analysis import summarize_rest_buckets

team = "STL"
team_df = df[df["playerTeam"] == team]

summary = summarize_rest_buckets(team_df)
summary
```

This provides rest-bucket averages for:

- xG%

- goals for

- goals against

- goal differential

- win rate

Example output:

| rest_bucket | xG%  | goals_for | goals_against |
| ----------- | ---- | --------- | ------------- |
| 0           | 47.8 | 2.41      | 3.12          |
| 1           | 51.3 | 2.77      | 2.66          |
| 2           | 52.1 | 2.91      | 2.55          |
| 3+          | 53.4 | 3.03      | 2.44          |

## 4️⃣ League-Wide Fatigue Sensitivity

Which teams suffer the most on low rest?
The package includes a ranking helper:

```python
from nhlRestEffects.analysis import rank_rest_sensitivity

ranking = rank_rest_sensitivity(df)
ranking.head()
```

This calculates:

```python
fatigue_score = xG%(3+ rest) − xG%(0 rest)
```

Teams with negative scores struggle in back-to-backs.
Teams with positive scores maintain performance under fatigue.

## 5️⃣ Visualizing Rest-Day Performance

The easiest way to generate a rest-bucket chart is with the visualization module:

```python
from nhlRestEffects.visualization import plot_rest_performance

plot_rest_performance(df, team="STL")
```

This chart includes:

- xG% at 0, 1, 2, and 3+ rest days

- A horizontal league-average line

- Clean labels and color palette

## 6️⃣ Back-to-Back Game Analysis

You can extract paired games from a back-to-back set:

```python
from nhlRestEffects.analysis import get_back_to_back_pairs

b2b_pairs = get_back_to_back_pairs(team_df)
b2b_pairs[:3]
```

Summarize performance across B2B sets:

```python
from nhlRestEffects.analysis import summarize_back_to_backs

b2b_summary = summarize_back_to_backs(team_df)
b2b_summary
```

Result shows:

| Game Type  | xG%  | Goals For | Goals Against |
| ---------- | ---- | --------- | ------------- |
| B2B Game 1 | 51.2 | 2.89      | 2.74          |
| B2B Game 2 | 47.8 | 2.33      | 3.22          |

## 7️⃣ Working With a Specific Season

To filter for a single year:

```python
year = "2022"
season_df = df[df["season"] == int(year)]
```

To analyze just the 2022 Blues:

```python
team_season_df = df[
    (df["playerTeam"] == "STL") & 
    (df["season"] == 2022)
]
```

Then you can run all the same summary functions on this subset.

## 8️⃣ Running the Streamlit Dashboard

The repository comes with a full interactive application built on the package.

Launch it with:

```bash
streamlit run streamlit_app/Home.py
```

The dashboard includes:

✔ Team-level performance
✔ Goalie comparison engine
✔ League-wide rest-impact analytics
✔ Back-to-back visualizer
✔ Rolling xG% & scoring trends

All powered by the same functions demonstrated above.

## 9️⃣ Full Example Workflow

Here is a complete pipeline from start to finish:

```python
from nhlRestEffects.data_loader import load_rest_data
from nhlRestEffects.analysis import (
    summarize_rest_buckets,
    rank_rest_sensitivity,
    get_back_to_back_pairs,
    summarize_back_to_backs
)
from nhlRestEffects.visualization import plot_rest_performance

# Load
df = load_rest_data("data/all_teams.csv")

# Pick team
team = "TBL"
team_df = df[df["playerTeam"] == team]

# Summaries
rest_summary = summarize_rest_buckets(team_df)
fatigue = rank_rest_sensitivity(df)
b2b = summarize_back_to_backs(team_df)

# Plot
plot_rest_performance(df, team=team)
```

## ✅ Summary

With nhlRestEffects, you can:

- Load & clean NHL data

- Compute rest-day performance trends

- Evaluate back-to-back fatigue

- Visualize team & league-wide rest effects

- Use a full Streamlit dashboard for exploration

This tutorial provides all the essential tools to replicate & extend the analysis from the STAT 386 final project.

--- 

## Project Report

You can read the full report here:  
[📄 Final Report](https://emclayburn.github.io/stat386_Final_Project/docs/Final_Report.html)

--- 

## 🤝 Contributing

Pull requests are welcome!
If you find an issue, please open a bug report describing:
	•	What happened
	•	Steps to reproduce
	•	Expected behavior

---

## 📚 Roadmap

- Publish to PyPI
- Add CLI commands (e.g., nhlrest --team TBL)
- Add predictive modeling (rest effect regression)
- Add season-level summary generator

---

## 🧊 Credits

Created by Ethan Clayburn and McKay Lush for STAT 386 — Data Acquisition & Analytics.




