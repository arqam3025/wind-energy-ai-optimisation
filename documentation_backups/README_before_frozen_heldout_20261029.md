# AI-Powered Wind Energy Forecasting and Battery Storage Optimisation

**Research status:** Active MSc Artificial Intelligence research.

## Overview

This project investigates how machine learning, wind power forecasting, uncertainty estimation, and model predictive control (MPC) can support battery energy storage operation and improve grid export stability.

The research combines artificial intelligence with electrical engineering and renewable energy optimisation.

## Research Objectives

1. Forecast wind power generation using machine learning.
2. Evaluate multi-step forecasting accuracy and uncertainty.
3. Model battery charging, discharging, and state of charge.
4. Develop forecast-informed and uncertainty-aware MPC controllers.
5. Compare controller performance against baseline strategies.
6. Investigate grid-ramp violations and battery energy constraints.

## Implemented Components

### Wind Power Forecasting
- Time-series data preparation and feature engineering
- Persistence forecasting baselines
- XGBoost forecasting experiments
- Multi-step forecasting and chronological evaluation

### Forecast Uncertainty
- Forecast error analysis
- Horizon-dependent uncertainty calibration
- Nominal and downside forecast scenarios

### Battery Optimisation
- Battery energy storage simulation
- Nominal and uncertainty-aware MPC
- Battery-ramp-aware MPC
- Energy-reserve MPC
- Grid-priority MPC
- Combined uncertainty-reserve grid-priority MPC

## Battery Development Configuration

| Parameter | Value |
| --- | --- |
| Battery capacity | 2,000 kWh |
| Maximum charge/discharge power | 1,000 kW |
| SOC limits | 40–90% |
| Charging/discharging efficiency | 95% |
| Control interval | 10 minutes |
| Prediction horizon | 6 intervals |
| Grid-ramp threshold | 200 kW |

These are research simulation assumptions, not specifications for a commissioned battery installation.

## Preliminary Experimental Results

The following results are from development Block 2, containing 144 observations and 143 within-block grid-ramp transitions.

| Controller | Ramp violations | Total exceedance (kW) |
| --- | ---: | ---: |
| Nominal MPC | 63 | 10,900.590 |
| Risk-weighted MPC (0.5) | 68 | 11,258.455 |
| Combined uncertainty-reserve grid-priority MPC | 67 | 11,285.412 |

These preliminary results show that additional uncertainty and reserve objectives do not automatically improve performance. Controller development and evaluation are ongoing.

**These are not final held-out test results.**

## Evaluation Metrics

- Forecast MAE and RMSE
- Mean and maximum grid-power ramp
- Grid-ramp threshold violations
- Total ramp exceedance
- Battery energy throughput
- State-of-charge behaviour

## Technologies

Python, Pandas, NumPy, Scikit-learn, XGBoost, CVXPY, optimisation solvers, Matplotlib, Git and GitHub.

## Repository Contents

- `scripts/` — forecasting, simulation, MPC and analysis code
- `requirements.txt` — Python dependencies
- `.gitignore` — excludes local datasets, models and generated results

Local datasets and generated outputs are not included by default. Full reproduction instructions are still being prepared.

## Current Research Status

Forecasting, uncertainty estimation and multiple MPC controllers have been implemented. Further controller development, comparison and final held-out evaluation remain in progress.

## Author

**Raja Arqam Abdullah**

MSc Artificial Intelligence — Teesside University

BSc Electrical Engineering

## Licence

No open-source licence has yet been selected.