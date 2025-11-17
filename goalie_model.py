import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score


# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_data():
    df = pd.read_csv("data/goalies_allseasons.csv")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df[df["xGoals"] > 0]

    # Target: Save %
    df["save_percent"] = 1 - (df["goals"] / df["xGoals"])
    df["save_percent"] = df["save_percent"].clip(0, 1)

    return df.dropna(subset=["save_percent"])


# ---------------------- MODEL PAGE ----------------------
def model_page():

    st.title("🤖 Predictive Goalie Performance Model")

    df = load_data()

    st.write("""
    This model predicts a goalie’s expected **save percentage** based on workload 
    and shot danger distribution.  
    It's meant to show whether statistical patterns can help forecast performance — 
    not to be perfectly accurate.
    """)

    # Features used
    features = ["xGoals", "highDangerShots", "mediumDangerShots", "lowDangerShots", "games_played"]
    df = df.dropna(subset=features)

    X = df[features].astype(float)
    y = df["save_percent"].astype(float)

    # Remove edge cases
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[mask], y[mask]

    # Train/Test split (quick, clean)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.25, random_state=42
    )

    # Model
    model = RandomForestRegressor(n_estimators=150, random_state=42)
    model.fit(X_train, y_train)

    # Evaluate
    predictions = model.predict(X_test)
    r2 = r2_score(y_test, predictions)

    st.subheader("📊 Model Performance")
    st.metric("R² Score", f"{r2:.3f}")

    st.caption("• 1.0 = perfect prediction, 0.0 = no predictive power  • In sports analytics, **0.25–0.50 R² is normal** due to randomness and variance.")

    # ---------------------- FEATURE IMPORTANCE ----------------------
    st.subheader("🔍 What Variables Matter Most?")

    importance = pd.DataFrame({
        "Feature": features,
        "Importance": model.feature_importances_
    }).sort_values("Importance", ascending=False)

    st.bar_chart(importance.set_index("Feature"))

    # ---------------------- INTERACTIVE PREDICTION ----------------------
    st.subheader("🎯 Try a Hypothetical Scenario")

    st.write("Adjust the sliders to simulate different shot patterns.")

    user_input = {}
    for f in features:
        user_input[f] = st.slider(
            f"{f}",
            float(df[f].min()),
            float(df[f].max()),
            float(df[f].median()),
            step=1.0,
        )

    user_df = pd.DataFrame([user_input])

    result = model.predict(user_df)[0]

    st.success(f"🧤 Predicted Save %: **{result:.3f}**")

    # Interpret prediction
    if result >= .930:
        st.info("🏆 Elite Goalie Projection")
    elif result >= .915:
        st.info("💪 Above Average Starter")
    elif result >= .900:
        st.info("😐 Average NHL Goalie")
    else:
        st.info("⚠️ Below NHL Starter Quality")

    st.caption("Prediction based on model patterns — not guaranteed performance.")
