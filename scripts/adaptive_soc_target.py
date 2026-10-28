
def calculate_adaptive_soc_target(
    current_power_kw,
    forecast_60min_kw
):
    predicted_change_kw = (
        forecast_60min_kw - current_power_kw
    )

    if predicted_change_kw < -500:
        return 60.0

    elif predicted_change_kw > 500:
        return 40.0

    else:
        return 50.0


if __name__ == "__main__":

    test_cases = [
        (3000, 2000),
        (2000, 3000),
        (2000, 2100),
    ]

    for current, forecast in test_cases:
        target = calculate_adaptive_soc_target(
            current,
            forecast
        )

        print(
            f"Current: {current} kW | "
            f"Forecast: {forecast} kW | "
            f"Target SOC: {target}%"
        )
