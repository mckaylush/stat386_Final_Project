import streamlit as st
from rest_impact import rest_impact_page
from back_to_back import back_to_back_page
from goalie_analytics import goalie_analytics_page
from goalie_fatigue import goalie_fatigue_page
from goalie_profile import goalie_profile_page


pages = {
    "🏒 Team Back-to-Back Analysis": back_to_back_page,
    "🥵 Fatigue Impact Analysis": goalie_fatigue_page,
    "🎯 Goalie Analytics": goalie_analytics_page,
    "🥅 Goalie Skill Chart": goalie_profile_page,
    "⏱️ Rest Impact Dashboard": rest_impact_page,
}


choice = st.sidebar.radio("Navigation", list(pages.keys()))


pages[choice]()
