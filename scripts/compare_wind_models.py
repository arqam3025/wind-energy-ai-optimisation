
import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error
from xgboost import XGBRegressor

DATA_PATH = "data/processed/wind_forecasting_10min.csv"

df = pd.read_csv(
    DATA_PATH,
    parse_dates=["timestamp", "target_timestamp"],
)

df = df.sort_values("timestamp").reset_index(drop=True)

features = [
    "power_kw",
    "wind_speed",
    "wind_direction",
]

target = "target_power_kw"

n = len(df)
train_end = int(n * 0.70)
validation_end = int(n * 0.85)

# Exclude training/validation rows whose target timestamps
# overlap the beginning of the next period.
train = df.iloc[:train_end].copy()
validation = df.iloc[train_end:validation_end].copy()

train = train[
    train["target_timestamp"]
    < validation["timestamp"].min()
]

test_start = df.iloc[validation_end]["timestamp"]

validation = validation[
    validation["target_timestamp"] < test_start
]

X_train = train[features]
y_train = train[target]

X_val = validation[features]
y_val = validation[target]


def evaluate(name, predictions):
    mae = mean_absolute_error(y_val, predictions)
    rmse = np.sqrt(mean_squared_error(y_val, predictions))

    print(f"\n{name}")
    print(f"MAE:  {mae:.3f} kW")
    print(f"RMSE: {rmse:.3f} kW")


print("=" * 60)
print("WIND FORECASTING MODEL COMPARISON")
print("=" * 60)

print("Training observations:", len(train))
print("Validation observations:", len(validation))

# Model 1: Persistence baseline
evaluate(
    "Persistence baseline",
    validation["power_kw"],
)

# Model 2: Random Forest
rf = RandomForestRegressor(
    n_estimators=200,
    min_samples_leaf=3,
    random_state=42,
    n_jobs=-1,
)

rf.fit(X_train, y_train)

evaluate(
    "Random Forest",
    rf.predict(X_val),
)

# Model 3: XGBoost
xgb = XGBRegressor(
    n_estimators=300,
    max_depth=4,
    learning_rate=0.05,
    subsample=0.8,
    colsample_bytree=0.9,
    objective="reg:squarederror",
    random_state=42,
    n_jobs=-1,
)

xgb.fit(X_train, y_train)

evaluate(
    "XGBoost",
    xgb.predict(X_val),
)

print("\nTest period remains reserved.")
