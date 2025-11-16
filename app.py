import streamlit as st
from goalie_leaders import leaderboard_page
from goalie_model import model_page
from back_to_back import back_to_back_page


pages = {
    "🏒 Back-to-Back Team Analysis": back_to_back_page,
    "🥅 Goalie Leaderboard": leaderboard_page,
    "🤖 Predictive Model": model_page
}

choice = st.sidebar.radio("Navigation", list(pages.keys()))


pages[choice]()
