import streamlit as st
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error
import matplotlib.pyplot as plt


# ---------------------- LOAD DATA ----------------------
@st.cache_data
def load_data():
    df = pd.read_csv("data/goalies_allseasons.csv")

    df = df.replace([np.inf, -np.inf], np.nan)
    df = df[df["xGoals"] > 0]

    df["save_percent"] = 1 - (df["goals"] / df["xGoals"])
    df["save_percent"] = df["save_percent"].clip(0, 1)

    return df.dropna(subset=["save_percent"])


# ---------------------- PAGE ----------------------
def model_page():

    st.title("🤖 Predicting Goalie Save Percentage")

    df = load_data()

    features = ["xGoals", "highDangerShots", "mediumDangerShots", "lowDangerShots", "games_played"]
    df = df.dropna(subset=features)

    X = df[features].astype(float)
    y = df["save_percent"].astype(float)

    # Remove any odd remaining values
    mask = np.isfinite(X).all(axis=1) & np.isfinite(y)
    X, y = X[mask], y[mask]


    # ---------------------- MODEL ----------------------
    model = RandomForestRegressor(n_estimators=300, random_state=42)

    # Cross-validation score
    cv_scores = cross_val_score(model, X, y, cv=5, scoring="r2")
    model.fit(X, y)

    st.write(f"📈 Cross-Validated R²: **{cv_scores.mean():.3f}** (± {cv_scores.std():.3f})")


    # ---------------------- FEATURE IMPORTANCE ----------------------
    st.subheader("🔍 What Impacts Save % Most?")
    importance = pd.DataFrame({
        "feature": features,
        "importance": model.feature_importances_
    }).sort_values("importance", ascending=False)

    st.bar_chart(importance.set_index("feature"))


    # ---------------------- EFFECT PLOTS ----------------------
    st.subheader("📊 How Inputs Affect Predictions (Partial Dependence Trends)")

    for feat in features:
        grid = np.linspace(df[feat].quantile(.05), df[feat].quantile(.95), 50)
        temp = X.copy()
        preds = []

        for val in grid:
            temp[feat] = val
            preds.append(model.predict(temp).mean())

        plt.figure(figsize=(6,4))
        plt.plot(grid, preds)
        plt.title(f"Effect of {feat} on Save %")
        plt.xlabel(feat)
        plt.ylabel("Predicted Save %")

        st.pyplot(plt)


    # ---------------------- USER PREDICTION ----------------------
    st.subheader("🎯 Test a Hypothetical Goalie")

    inputs = {}
    for f in features:
        inputs[f] = st.number_input(
            f,
            value=float(df[f].median()),
            min_value=float(df[f].quantile(.05)),
            max_value=float(df[f].quantile(.95))
        )

    prediction = model.predict(pd.DataFrame([inputs]))[0]

    st.success(f"Predicted Save %: **{prediction:.3f}**")

    # Interpretation
    if prediction > 0.93:
        tier = "🥇 Elite Starter Level"
    elif prediction > 0.915:
        tier = "🥈 Above-Average NHL Starter"
    elif prediction > 0.900:
        tier = "🥉 Average Goalie Performance"
    else:
        tier = "⚠️ Below NHL Starter Level"

    st.info(tier)
