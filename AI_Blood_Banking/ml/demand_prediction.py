import pandas as pd
from sklearn.ensemble import RandomForestRegressor
import joblib
import os


# -----------------------------------
# Load Dataset
# -----------------------------------

data_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "data",
    "blood_demand.csv"
)

df = pd.read_csv(data_path)


# -----------------------------------
# Prepare Data
# -----------------------------------

df["date"] = pd.to_datetime(df["date"])

df["day"] = df["date"].dt.day
df["month"] = df["date"].dt.month
df["day_of_week"] = df["date"].dt.dayofweek


# Convert blood groups into numbers
blood_groups = {
    "A+": 1,
    "A-": 2,
    "B+": 3,
    "B-": 4,
    "AB+": 5,
    "AB-": 6,
    "O+": 7,
    "O-": 8
}

df["blood_group_code"] = df["blood_group"].map(blood_groups)


# -----------------------------------
# Features and Target
# -----------------------------------

X = df[
    [
        "day",
        "month",
        "day_of_week",
        "blood_group_code"
    ]
]

y = df["demand"]


# -----------------------------------
# Train Machine Learning Model
# -----------------------------------

model = RandomForestRegressor(
    n_estimators=100,
    random_state=42
)

model.fit(X, y)


# -----------------------------------
# Save Model
# -----------------------------------

model_path = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "models",
    "demand_model.pkl"
)

os.makedirs(
    os.path.dirname(model_path),
    exist_ok=True
)

joblib.dump(model, model_path)


print("Demand prediction model trained successfully!")
print("Model saved at:")
print(model_path)


# -----------------------------------
# Prediction Function
# -----------------------------------

def predict_demand(blood_group, date):

    date = pd.to_datetime(date)

    blood_group = blood_group.upper()

    if blood_group not in blood_groups:
        raise ValueError("Invalid blood group")

    input_data = pd.DataFrame(
        [[
            date.day,
            date.month,
            date.dayofweek,
            blood_groups[blood_group]
        ]],
        columns=[
            "day",
            "month",
            "day_of_week",
            "blood_group_code"
        ]
    )

    prediction = model.predict(input_data)

    return round(prediction[0])


# -----------------------------------
# Test Prediction
# -----------------------------------

if __name__ == "__main__":

    predicted_units = predict_demand(
        "A+",
        "2025-02-01"
    )

    print(
        "Predicted A+ blood demand:",
        predicted_units,
        "units"
    )