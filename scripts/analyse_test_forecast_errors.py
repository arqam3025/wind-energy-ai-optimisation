
import numpy as np
import pandas as pd

df = pd.read_csv(
    "results/wind_xgboost_test_predictions.csv",
    parse_dates=["timestamp", "target_timestamp"],
)

actual = df["actual_power_kw"].to_numpy()

models = {
    "Persistence": df[
        "persistence_prediction_kw"
    ].to_numpy(),
    "XGBoost": df[
        "xgboost_prediction_kw"
    ].to_numpy(),
}

print("=" * 60)
print("HELD-OUT WIND FORECAST ERROR ANALYSIS")
print("=" * 60)

for name, predictions in models.items():
    errors = predictions - actual
    absolute_errors = np.abs(errors)

    print(f"\n{name}")
    print(
        f"Mean absolute error: "
        f"{absolute_errors.mean():.3f} kW"
    )
    print(
        f"Median absolute error: "
        f"{np.median(absolute_errors):.3f} kW"
    )
    print(
        f"90th percentile absolute error: "
        f"{np.percentile(absolute_errors, 90):.3f} kW"
    )
    print(
        f"95th percentile absolute error: "
        f"{np.percentile(absolute_errors, 95):.3f} kW"
    )
    print(
        f"Maximum absolute error: "
        f"{absolute_errors.max():.3f} kW"
    )
    print(
        f"Errors above 200 kW: "
        f"{np.sum(absolute_errors > 200)}"
    )
    print(
        f"Errors above 500 kW: "
        f"{np.sum(absolute_errors > 500)}"
    )

persistence_error = np.abs(
    models["Persistence"] - actual
)

xgboost_error = np.abs(
    models["XGBoost"] - actual
)

print("\nPaired forecast comparison:")

print(
    "XGBoost better intervals:",
    int(np.sum(xgboost_error < persistence_error))
)

print(
    "Persistence better intervals:",
    int(np.sum(persistence_error < xgboost_error))
)

print(
    "Equal-error intervals:",
    int(np.sum(
        np.isclose(xgboost_error, persistence_error)
    ))
)

print("\nAnalysis completed.")
