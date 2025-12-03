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

🤝 Contributing

Pull requests are welcome!
If you find an issue, please open a bug report describing:
	•	What happened
	•	Steps to reproduce
	•	Expected behavior

---

📚 Roadmap
	•	☐ Publish to PyPI
	•	☐ Add CLI commands (e.g., nhlrest --team TBL)
	•	☐ Add predictive modeling (rest effect regression)
	•	☐ Add season-level summary generator

---

---

🧊 Credits

Created by Ethan Clayburn and McKay Lush for STAT 386 — Data Acquisition & Analytics.




