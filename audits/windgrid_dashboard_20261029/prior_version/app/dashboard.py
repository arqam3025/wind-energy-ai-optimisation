"""Local historical replay of frozen wind-battery research; never a live controller."""
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import sys
import uuid

import numpy as np
import pandas as pd
import streamlit as st

APP_DIRECTORY = Path(__file__).resolve().parent
if str(APP_DIRECTORY) not in sys.path:
    sys.path.insert(0, str(APP_DIRECTORY))
from research_data import (ROOT, CONTROLLERS, available_blocks, load_table, load_replay,
                           interval_accounting, fixed_margins, aggregate_comparison)

st.set_page_config(page_title="Wind–battery research replay", page_icon="🌬️", layout="wide")
st.markdown("""<style>
.block-container {max-width: 1440px; padding-top: 2rem;}
[data-testid="stMetric"] {background: #eef5fa; border-radius: 10px; padding: .8rem 1rem;}
[data-testid="stMetricLabel"], [data-testid="stMetricValue"] {color: #12324a;}
</style>""", unsafe_allow_html=True)
st.caption("MSc Artificial Intelligence · wind-energy-ai-optimisation")
st.title("Wind–battery research replay")
st.write("Explore saved ten-minute forecasts, battery operation and grid-ramp outcomes from the frozen controller comparison.")
st.info("Historical offline replay and research simulation. This dashboard is not connected to a wind farm and cannot issue physical control commands.")
st.warning("Adaptive improves on fixed margins, but both MPC controllers have more aggregate ramp violations and exceedance than uncontrolled wind. These are retrospective results: earlier test-period inspection and block-6/block-7 target overlap prevent a clean confirmatory holdout claim.")

try:
    blocks = available_blocks()
    totals = load_table("aggregate_metrics").set_index("controller")
    metrics = load_table("block_metrics")
except (FileNotFoundError, ValueError, KeyError) as error:
    st.error(f"Research summaries could not be loaded: {error}")
    st.write("Restore the verified docs/tables_v2 research tables. A fresh clone does not contain private/local input data or per-interval simulation traces.")
    st.stop()

with st.sidebar:
    st.header("Replay controls")
    kind = st.selectbox("Controller", list(CONTROLLERS), format_func=CONTROLLERS.get, key="controller")
    block_id = st.selectbox("Evaluation block", blocks, format_func=lambda b: f"Block {b}", key="block_id")
    horizon = st.select_slider("Uncertainty horizon (minutes)", options=[10,20,30,40,50,60], value=10, key="horizon")
    st.caption("Block 6 is development and is excluded. All episodes reset the battery to 50% SOC; uncertainty history carries forward causally.")
    st.divider()
    st.caption("Frozen settings")
    st.write("2,000 kWh · 1,000 kW\n\nSOC 40–90% · efficiency 95% each way\n\n200 kW ramp threshold · six-step horizon\n\n100 kW stage-two primary allowance")

selected = metrics.loc[(metrics.controller == kind) & (metrics.block_id == block_id)].iloc[0]
cards = st.columns(4)
cards[0].metric("Block ramp violations", f"{int(selected.ramp_violations):,}")
cards[1].metric("Block exceedance sum", f"{selected.ramp_exceedance_kw:,.1f} kW")
cards[2].metric("Block throughput", f"{selected.throughput_kwh:,.1f} kWh")
cards[3].metric("Block conversion loss", f"{selected.conversion_losses_kwh:,.2f} kWh")
st.caption(f"{CONTROLLERS[kind]} · block {block_id} · frozen saved metrics. Ramp exceedance is a sum of power differences, not energy.")

try:
    inputs, traces = load_replay(block_id)
    replay_error = None
except (FileNotFoundError, ValueError, KeyError) as error:
    inputs, traces = None, None
    replay_error = str(error)

replay_tab, comparison_tab, forecast_tab, study_tab = st.tabs(["Historical replay", "Controller comparison", "Forecasts & uncertainty", "Study notes & rerun"])

with replay_tab:
    st.subheader(f"{CONTROLLERS[kind]} · block {block_id}")
    if replay_error:
        st.warning("Per-interval replay is unavailable. Verified aggregate and per-block summary views remain available.")
        st.caption(replay_error)
    else:
        trace = interval_accounting(inputs, traces[kind])
        st.caption(f"Target times: {trace.timestamp.iloc[0]} to {trace.timestamp.iloc[-1]} · dataset clock, timezone unspecified.")
        chart = trace.set_index("timestamp")
        export = pd.DataFrame({"Wind generation": chart.wind_generation_kw, "Grid export": chart.grid_export_kw})
        st.line_chart(export, y_label="Power (kW)", x_label="Target time", color=["#7a8793", "#0072b2"])
        left, right = st.columns(2)
        with left:
            st.markdown("**Battery power**")
            st.line_chart(chart[["charge_kw", "discharge_kw", "battery_net_power_kw"]].rename(columns={"charge_kw":"Charging", "discharge_kw":"Discharging", "battery_net_power_kw":"Net battery (discharge − charge)"}), y_label="Power (kW)", x_label="Target time")
        with right:
            st.markdown("**Stored energy state**")
            soc = pd.DataFrame({"SOC": chart.soc_percent, "Minimum":40., "Maximum":90.})
            st.line_chart(soc, y_label="SOC (%)", x_label="Target time", color=["#009e73", "#999999", "#cc7979"])
        st.markdown("**Realised grid ramps and uncontrolled wind reference**")
        ramp = pd.DataFrame({"Controlled absolute ramp": chart.absolute_grid_ramp_kw, "Uncontrolled absolute ramp": chart.uncontrolled_ramp_kw, "Threshold":200.})
        st.line_chart(ramp, y_label="Absolute power change (kW)", x_label="Target time")
        st.caption("144 transitions per block, including current wind at the initial origin to the first controlled export. Violations use >200.001 kW; exceedance sums max(ramp − 200, 0). No cross-episode transition is scored.")
        st.download_button("Download selected interval replay CSV", trace.to_csv(index=False).encode("utf-8"), file_name=f"historical_{kind}_block_{block_id}.csv", mime="text/csv", key="download_replay")
        with st.expander("Interval values and violation flags"):
            st.dataframe(trace, hide_index=True, width="stretch")

with comparison_tab:
    st.subheader("Same episodes, different frozen uncertainty policies")
    comparison = aggregate_comparison()
    st.dataframe(comparison, width="stretch")
    st.caption("Aggregate: 49 blocks and 7,056 transitions per controller. Terminal-adjusted export values hypothetical restoration of initial storage: surplus ×0.95; deficit ÷0.95. It is not realised export, revenue or a simulated restoration trajectory.")
    fixed, adaptive = totals.loc["fixed"], totals.loc["adaptive_one_sided"]
    st.write(f"Adaptive versus fixed: **{100*(1-adaptive.throughput_kwh/fixed.throughput_kwh):.2f}% lower throughput**, **{100*(1-adaptive.conversion_losses_kwh/fixed.conversion_losses_kwh):.2f}% lower modeled conversion losses**, **{100*(1-adaptive.ramp_exceedance_kw/fixed.ramp_exceedance_kw):.2f}% lower summed exceedance**, and **{int(fixed.ramp_violations-adaptive.ramp_violations)} fewer violations**.")
    st.write(f"Actual adaptive export is {(adaptive.export_kwh-fixed.export_kwh)/1000:+.3f} MWh different; hypothetical terminal-adjusted export is {(adaptive.terminal_adjusted_export_kwh-fixed.terminal_adjusted_export_kwh)/1000:+.3f} MWh different.")
    block_comparison = metrics.loc[metrics.block_id.eq(block_id), ["controller","ramp_violations","ramp_exceedance_kw","throughput_kwh","conversion_losses_kwh","export_kwh","terminal_adjusted_export_kwh","curtailment_kwh","terminal_energy_delta_kwh"]].copy()
    block_comparison.controller = block_comparison.controller.map(CONTROLLERS)
    st.markdown(f"**Block {block_id}: paired saved outcomes**")
    st.dataframe(block_comparison.set_index("controller"), width="stretch")
    differences = load_table("paired_differences").set_index("block_id")
    st.markdown("**Adaptive minus fixed, by block**")
    metric = st.selectbox("Paired outcome", ["throughput_kwh","ramp_exceedance_kw","ramp_violations","conversion_losses_kwh","terminal_adjusted_export_kwh"], key="paired_metric")
    st.bar_chart(differences[[metric]], x_label="Evaluation block", y_label=metric.replace("_", " "), color="#0072b2")
    st.caption("Negative favours adaptive for throughput, losses, exceedance and violation count; positive favours adaptive for adjusted export. Day-to-day outcomes are dependent. Aggregate ramp improvement does not establish consistent or statistically significant superiority.")
    st.download_button("Download aggregate comparison CSV", comparison.to_csv().encode("utf-8"), file_name="frozen_controller_comparison.csv", mime="text/csv", key="download_comparison")

with forecast_tab:
    st.subheader("Point forecasts and empirical lower-bound coverage")
    accuracy = load_table("forecast_metrics")
    left, right = st.columns(2)
    with left:
        st.line_chart(accuracy.pivot(index="horizon_minutes", columns="model", values="mae_kw"), x_label="Forecast horizon (minutes)", y_label="MAE (kW)")
    with right:
        st.line_chart(accuracy.pivot(index="horizon_minutes", columns="model", values="rmse_kw"), x_label="Forecast horizon (minutes)", y_label="RMSE (kW)")
    st.caption("XGBoost has higher MAE and lower RMSE than persistence at every horizon. Forecast superiority depends on the error metric; no retraining or held-out tuning is performed.")
    coverage = load_table("uncertainty_coverage")
    cov = coverage.groupby(["horizon_minutes","controller"]).lower_bound_coverage.mean().unstack()
    st.line_chart(cov.rename(columns=CONTROLLERS), x_label="Forecast horizon (minutes)", y_label="Empirical lower-bound coverage")
    st.caption("Coverage is marginal empirical coverage of max(0, forecast − margin). Serial dependence, static floors and fallback prevent a distribution-free or simultaneous six-horizon guarantee. Nominal 90% is a reference, not an established guarantee.")
    if traces is not None:
        h = horizon//10
        margin_view = pd.DataFrame(index=traces["adaptive_one_sided"].timestamp)
        margin_view["Adaptive one-sided margin"] = traces["adaptive_one_sided"][f"adaptive_margin_h{h}_kw"].to_numpy()
        fixed = fixed_margins()
        if fixed is not None:
            margin_view["Fixed margin"] = fixed[h-1]
        st.markdown(f"**Block {block_id}: {horizon}-minute margins used at each decision**")
        margin_view.index = margin_view.index - pd.Timedelta(minutes=10)
        st.line_chart(margin_view, x_label="Decision time", y_label="Margin (kW)")
        if kind == "adaptive_one_sided":
            st.caption("Signed residuals enter the 144-sample rolling window only when their target time is strictly earlier than the decision. Targets equal to the decision are excluded. Static floors are active for most decisions.")
    st.dataframe(accuracy, hide_index=True, width="stretch")
    st.download_button("Download forecast accuracy CSV", accuracy.to_csv(index=False).encode("utf-8"), file_name="frozen_forecast_accuracy.csv", mime="text/csv", key="download_forecast")

with study_tab:
    st.subheader("Interpretation and provenance")
    st.write("The preferred controller was chosen on development data. Existing evaluation episodes were inspected before the freeze; block 6 is excluded, but five of its development target timestamps overlap block 7. These results support a retrospective frozen comparison, not independent confirmatory testing.")
    st.write("The primary objective minimises predicted scenario-weighted ramp exceedance. Stage two permits 100 kW above that optimum while minimising the frozen operational objective. Forecast error, reserve/terminal penalties and battery actions can worsen realised ramps. Physical feasibility does not imply better ramp mitigation.")
    st.write("Battery models use fixed efficiencies and omit ageing, thermal dynamics, auxiliary loads and state-estimation error. Lower throughput is not a quantified lifetime benefit. Each block starts at 50% SOC; uncertainty history is causal and is not reset with the battery.")
    st.code("b007aa5c57b5610ea75663d592b92816598c15658ed21bf0fcd99c107859895a", language=None)
    st.caption("Expected SHA256 of the frozen development manifest. Full source/input checks occur in the simulation runner; the dashboard reads saved artifacts.")
    st.markdown("**Local source documents**")
    st.write("docs/paper_submission_draft.md · docs/grid_ramp_diagnostic.md · docs/methodology.md · docs/reproducibility.md · audits/publication_readiness_20261029/report.md")
    with st.expander("Optional: rerun the frozen controllers for this block"):
        st.write("This launches the existing frozen runner with unchanged parameters in a new directory. It needs all local input/calibration/development artifacts and may take several minutes. It never replaces the historical view above and cannot operate a physical battery.")
        st.code(f".venv/Scripts/python.exe scripts/run_frozen_heldout.py --run my_unique_replay --blocks {block_id}", language="powershell")
        if st.button("Run isolated frozen block replay", key="rerun_frozen"):
            run_name = "dashboard_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S") + "_" + uuid.uuid4().hex[:8]
            with st.spinner("Solving both frozen controllers. Results will be saved separately…"):
                completed = subprocess.run([sys.executable, str(ROOT/"scripts/run_frozen_heldout.py"), "--run", run_name, "--blocks", str(block_id)], cwd=ROOT, capture_output=True, text=True)
            if completed.returncode == 0:
                st.success(f"Requested block replay completed in results/frozen_heldout/{run_name}. This is one paired block, not a new full evaluation.")
            else:
                st.error("The frozen replay did not complete. Existing research outputs are unchanged; inspect the new run logs and input requirements.")
            st.code((completed.stdout + "\n" + completed.stderr)[-12000:], language=None)
