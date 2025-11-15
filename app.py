import streamlit as st
from goalie_leaders import leaderboard_page
from goalie_model import model_page

pages = {
    "🏒 Back-to-Back Team Analysis": None,   # existing page
    "🥅 Goalie Leaderboard": leaderboard_page,
    "🤖 Predictive Model": model_page
}

choice = st.sidebar.radio("Navigation", list(pages.keys()))

if pages[choice] is not None:
    pages[choice]()
