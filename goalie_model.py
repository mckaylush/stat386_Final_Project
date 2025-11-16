import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score

# ---------------------- DATA LOADER ----------------------
@st.cache_data
def load_data():
    df = pd.read_csv("data/goalies_allseasons.csv")

    # Ensure numeric columns only
    df = df.replace([np.inf, -np.inf], np.nan).dropna()

    # Create save percentage metric
    df["save_percent"] = 1 - (df["goals"] / df["xGoals"]).clip(0, 1)

    return df


# ---------------------- PAGE UI ----------------------
def model_page():
    st.title("🤖 NHL Goalie Performance Model")

    df = load_data()

    # Features to train on
    features = ["xGoals", "highDangerShots", "mediumDangerShots", "lowDangerShots", "games_played"]
    
    X = df[features]
    y = df["save_percent"]

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=42)

    # Model
    model = RandomForestRegressor(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    predictions = model.predict(X_test)
    r2 = r2_score(y_test, predictions)

    st.write(f"📈 Model R² Score: **{r2:.3f}**")
    st.caption("R² closer to 1 means better predictive accuracy.")

    # ---------------------- FEATURE IMPORTANCE ----------------------
    st.subheader("🔍 Feature Importance")

    importance = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    st.bar_chart(importance.set_index("feature"))

    # ---------------------- USER INTERACTIVE PREDICTIONS ----------------------
    st.subheader("🎯 Try a Prediction")

    user_input = {}
    for f in features:
        user_input[f] = st.slider(
            f,
            float(df[f].min()),
            float(df[f].max()),
            float(df[f].median())
        )

    user_df = pd.DataFrame([user_input])
    result = model.predict(user_df)[0]

    st.success(f"🧤 Predicted Save %: **{result:.3f}**")



