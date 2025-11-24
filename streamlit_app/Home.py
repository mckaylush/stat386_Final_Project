import streamlit as st

st.set_page_config(page_title="NHL Rest Study", layout="wide")

st.title("🏒 NHL Rest & Performance Study")

st.markdown("""
Welcome to the **Stat 386 Final Project Dashboard**, exploring how **rest affects NHL team performance**
from the 2016–2025 seasons using data from **MoneyPuck.com**.

---

### ❓ Research Question  
> **Does playing games with fewer rest days — especially back-to-back games — negatively affect NHL performance?**

This dashboard allows you to interactively explore:
- 📊 Team-level performance trends  
- 🧠 Goalie performance analytics  
- 🕸️ Side-by-side goalie skill comparisons  
- 🔁 Back-to-back vs non-back-to-back performance differences  
- ⏳ League-wide fatigue trends  

---

### 🚀 How to Use This App

👉 Use the sidebar on the left to select a page:

| Page | What it shows |
|-------|--------------|
| **Team Analysis** | Game-by-game expected goals, wins/losses, and rest markers |
| **Goalie Analytics** | Save%, GSAx, danger-level breakdowns |
| **Goalie Profile** | Compare goalies with visuals & downloadable report |
| **Fatigue Analysis** | League-wide rest patterns and outcome impact |
| **Rest Impact** | Summary metrics comparing rest-day buckets |

---

### 💡 Key Takeaways (so far)

- 🟥 Teams tend to underperform on the **second night of a back-to-back**  
- 🟩 Performance improves after **3–5 days of rest**  
- 😅 Goalies rarely play back-to-back games — fatigue mostly affects **team defense + shot quality allowed**  

---

If you're curious how the data was collected or processed, check the GitHub repository:

🔗 **https://github.com/emclayburn/stat386_Final_Project**
""")

