# 🏒 NHL Back-to-Back Performance Analysis

This Streamlit app explores whether **rest days influence NHL team performance** using multi-season play-by-play data from **MoneyPuck.com**.

The project includes data cleaning, feature engineering, visualization, and comparative analysis tools designed for fans, analysts, and data scientists.

---

## 🚨 Research Question

> **Does the amount of rest between games affect team performance in the NHL?**

With teams facing tight travel schedules, especially during back-to-back matchups, understanding fatigue effects may reveal competitive advantages and strategic insights.

---

## 📊 Key Features

| Feature | Description |
|--------|-------------|
| **Team Back-to-Back Dashboard** | Explore how rest days affect expected goals, goals scored, and win rate across seasons. |
| **Goalie Analytics Page** | Compare individual goaltenders across save types, goals saved above expected, and game situations. |
| **Skill Comparison Tool** | Side-by-side bar visualizations comparing two goalies to league averages. |
| **PDF Reporting** | Export customizable goalie comparisons into a formatted PDF report. |
| **Interactive Filters** | Filter by season, team, home/away, and game situation. |

---

## 🧠 Data Sources

All analytics are powered by publicly available NHL tracking data from:  
📍 **https://moneypuck.com**

Raw data includes:

- Expected goals (xG)
- Shot danger ratings (low / medium / high)
- Goalie and skater performance metrics
- Game-level context including travel and rest days

---

## 🧪 Methods & Processing

Key preprocessing and modeling steps:

- Standardized team abbreviations (e.g., `"N.J." → "NJD"`)
- Engineered rest-day classification (`0 days`, `1 day`, `2+ days`)
- Rolled averages to smooth game-to-game volatility
- Evaluated predictive modeling (Random Forest), ultimately excluded based on weak signal (R² ≈ 0.34)

---

## 🔍 Results Summary

- Teams generally perform **worse on the second game of a back-to-back**, showing reduced expected goals and win percentage.
- The effect varies by season and team, but the trend is consistent league-wide.
- Goaltenders rarely play back-to-back games, meaning **fatigue patterns are stronger at the team level than individual level**.

---

## 🚀 How to Run Locally

```bash
# 1. Clone repository
git clone https://github.com/YOUR-USERNAME/YOUR-REPO.git
cd YOUR-REPO

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Streamlit
streamlit run app.py
```
## 📁 Project Structure

📦 NHL-Rest-Analysis
 ┣ 📁 data/                 → CSV files cleaned from MoneyPuck
 ┣ 📁 pages/                → Streamlit multi-page modules
 ┣ app.py                  → Main navigation controller
 ┣ goalie_analytics.py     → Goalie evaluation tools
 ┣ goalie_profile.py       → Comparison + report export
 ┣ back_to_back.py         → Team fatigue analysis dashboard
 ┣ requirements.txt
 ┗ README.md   ← (You are here)


## 📘 Future Improvements
Add travel distance modeling

Include machine learning rest impact predictions

Add shot map visualization using rink coordinates

## 👤 Author
Ethan Clayburn
📍 Brigham Young University — Statistics/Data Science

If you'd like to discuss sports analytics, NHL models, or project collaborations — reach out!

