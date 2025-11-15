import streamlit as st
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score

@st.cache_data
def load_data():
    df = pd.read_csv("goalie_data.csv").dropna()
    df["save_percent"] = 1 - (df["goals"] / df["xGoals"])
    return df

def model_page():
    df = load_data()

    st.title("🤖 Goalie Performance Model")

    features = ["xGoals", "highDangerShots", "mediumDangerShots", "lowDangerShots", "games_played"]
    X = df[features]
    y = df["save_percent"]

    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X, y)

    predictions = model.predict(X)
    r2 = r2_score(y, predictions)

    st.write(f"📈 Model R² Score: **{r2:.3f}**")

    st.subheader("Feature Importance")
    importance = pd.DataFrame({"feature": features, "importance": model.feature_importances_})
    st.bar_chart(importance.set_index("feature"))

    st.subheader("Try A Prediction")
    user_input = {f: st.slider(f, float(df[f].min()), float(df[f].max())) for f in features}
    result = model.predict([list(user_input.values())])[0]

    st.success(f"Predicted Save %: **{result:.3f}**")
