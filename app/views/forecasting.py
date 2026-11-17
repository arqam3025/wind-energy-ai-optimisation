"""Forecast research views derived only from saved forecasts and measurements."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from platform_data import CASES, get_table, planning_frame
from ui import chart, section_header, metrics

COLORS = {"actual": "#E4EEF8", "xgboost": "#56B4E9", "persistence": "#E69F00", "adaptive_one_sided": "#39D3B5", "fixed": "#E69F00"}


def render(context):
    section_header("PREDICTION RESEARCH", "AI Forecasting Lab", "Compare stored XGBoost forecasts with measured wind and persistence across six target horizons.")
    accuracy = get_table("forecast_metrics")
    coverage = get_table("uncertainty_coverage")
    horizon = int(context.get("horizon", 10))
    block_id = int(context["block_id"])
    bundle = context.get("bundle")
    policy = st.radio("Uncertainty policy", ["adaptive_one_sided", "fixed"],
                      format_func=CASES.get, horizontal=True,
                      index=1 if context["kind"] == "fixed" else 0, key="forecast_policy")
    st.caption("A downside path is a lower research bound. The shaded nominal-to-downside region is not a two-sided prediction interval, and nominal coverage is not guaranteed.")

    if bundle is not None:
        inputs = bundle.inputs
        step = min(max(int(context.get("step", 0)), 0), len(inputs)-1)
        h = horizon // 10
        targets = pd.to_datetime(inputs.timestamp) + pd.Timedelta(minutes=horizon)
        actual = inputs[f"actual_h{h}_kw"].to_numpy(float)
        forecast = np.maximum(0, inputs[f"xgboost_h{h}_kw"].to_numpy(float))
        persistence = inputs[f"persistence_h{h}_kw"].to_numpy(float)
        if policy == "adaptive_one_sided":
            margins = bundle.traces[policy][f"adaptive_margin_h{h}_kw"].to_numpy(float)
        else:
            constant = float(planning_frame(block_id, policy, step).iloc[h-1].margin_kw)
            margins = np.full(len(inputs), constant)
        lower = np.maximum(0, forecast-margins)
        errors = forecast-actual
        metrics([
            (f"{horizon}-min XGBoost MAE", f"{np.abs(errors).mean():,.2f} kW", "Selected block · all 144 origins"),
            ("XGBoost RMSE", f"{np.sqrt(np.mean(errors**2)):,.2f} kW", "Same origins and target times"),
            ("Persistence MAE", f"{np.abs(persistence-actual).mean():,.2f} kW", "Current power repeated forward"),
            ("Empirical lower coverage", f"{100*np.mean(actual>=lower):.2f}%", "Marginal, selected policy and block"),
        ])
        fig = go.Figure()
        for name, values, color, dash in [
            ("Actual wind", actual, COLORS["actual"], "solid"),
            ("Persistence", persistence, COLORS["persistence"], "dot"),
            ("XGBoost forecast", forecast, COLORS["xgboost"], "solid"),
        ]:
            fig.add_trace(go.Scatter(x=targets, y=values, name=name,
                mode="lines", line=dict(color=color, width=2, dash=dash),
                hovertemplate="%{x|%d %b %H:%M}<br>%{y:,.2f} kW<extra>%{fullData.name}</extra>"))
        fig.add_trace(go.Scatter(x=targets, y=lower, name="One-sided lower bound",
            mode="lines", line=dict(color=COLORS[policy], width=1.5, dash="dash"),
            fill="tonexty", fillcolor="rgba(57,211,181,0.10)",
            hovertemplate="%{x|%d %b %H:%M}<br>%{y:,.2f} kW<extra>Lower bound</extra>"))
        selected_target = targets.iloc[step]
        fig.add_shape(type="line", x0=selected_target, x1=selected_target, y0=0, y1=1,
                      yref="paper", line=dict(color="#F3C969", width=1, dash="dot"))
        fig.update_layout(title=f"Block {block_id} · {horizon}-minute predictions aligned to target time",
                          xaxis_title="Target time · dataset clock", yaxis_title="Generation (kW)", hovermode="x unified")
        chart(fig, "forecast_timeseries")
        st.caption("The cursor marks the selected origin's forecast target. This full-episode view is historical; later measured values are displayed for assessment, never supplied to the frozen dispatch decision.")

        path = planning_frame(block_id, policy, step)
        path_fig = go.Figure()
        for column, label, color, dash in [
            ("nominal_kw", "XGBoost nominal", COLORS["xgboost"], "solid"),
            ("downside_kw", "Downside scenario", COLORS[policy], "dash"),
            ("persistence_kw", "Persistence", COLORS["persistence"], "dot"),
            ("actual_kw", "Actual future targets · retrospective", COLORS["actual"], "solid"),
        ]:
            path_fig.add_trace(go.Scatter(x=path.horizon_minutes, y=path[column], name=label,
                mode="lines+markers", line=dict(color=color, dash=dash),
                hovertemplate="+%{x} min<br>%{y:,.2f} kW<extra>%{fullData.name}</extra>"))
        path_fig.update_layout(title=f"Six horizons from decision {inputs.timestamp.iloc[step]}",
                              xaxis_title="Forecast horizon (minutes)", yaxis_title="Generation (kW)")
        chart(path_fig, "forecast_six_horizons")
        export = pd.DataFrame({"target_time": targets, "actual_kw": actual,
            "xgboost_kw": forecast, "persistence_kw": persistence,
            "lower_bound_kw": lower, "margin_kw": margins, "policy": policy})
        st.download_button("Download selected forecast assessment CSV", export.to_csv(index=False).encode("utf-8"),
                           file_name=f"forecast_block_{block_id}_{horizon}min_{policy}.csv", mime="text/csv", key="forecast_download")
    else:
        st.info("Per-origin forecasts require the local evaluation input and paired trace files. Aggregate research accuracy and coverage remain available below.")
        if context.get("replay_error"):
            st.caption(context["replay_error"])

    st.markdown("### Frozen 49-block forecast assessment")
    left, right = st.columns(2)
    for column, metric, title in [(left, "mae_kw", "Mean absolute error"), (right, "rmse_kw", "Root mean squared error")]:
        with column:
            fig = go.Figure()
            for model, color in [("xgboost", COLORS["xgboost"]), ("persistence", COLORS["persistence"])]:
                part = accuracy.loc[accuracy.model.eq(model)].sort_values("horizon_minutes")
                fig.add_trace(go.Scatter(x=part.horizon_minutes, y=part[metric], mode="lines+markers",
                    name=model.title(), line=dict(color=color, width=2.5),
                    hovertemplate="%{x} min<br>%{y:,.2f} kW<extra>%{fullData.name}</extra>"))
            fig.update_layout(title=title, xaxis_title="Horizon (minutes)", yaxis_title="Error (kW)")
            chart(fig, f"forecast_{metric}")
    st.caption("XGBoost has higher MAE but lower RMSE than persistence at every horizon. The predictive result is mixed across error metrics; the dashboard performs no retraining or selection.")
    fig = go.Figure()
    for kind in ["adaptive_one_sided", "fixed"]:
        part = coverage.loc[coverage.controller.eq(kind)].groupby("horizon_minutes").lower_bound_coverage.mean()
        fig.add_trace(go.Scatter(x=part.index, y=100*part, name=CASES[kind], mode="lines+markers",
            line=dict(color=COLORS[kind], width=2.5), hovertemplate="%{x} min<br>%{y:.2f}%<extra>%{fullData.name}</extra>"))
    fig.add_hline(y=90, line_dash="dot", line_color="#8B9CB1")
    fig.update_layout(title="Empirical marginal lower-bound coverage", xaxis_title="Horizon (minutes)",
                      yaxis_title="Coverage (%)", yaxis=dict(range=[0, 100]))
    chart(fig, "forecast_coverage")
    with st.expander("Verified accuracy table and interpretation"):
        st.dataframe(accuracy[["model", "horizon_minutes", "mae_kw", "rmse_kw"]], hide_index=True, width="stretch")
        st.write("Serial dependence, static floors and the inherited fallback prevent a distribution-free or simultaneous six-horizon coverage guarantee. High coverage alone does not establish sharpness or operational value.")
