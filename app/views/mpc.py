"""Explore saved MPC inputs and first commands without inventing solver plans."""
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from platform_data import CASES, get_table, interval_frame, planning_frame
from ui import chart, section_header, metrics

COLORS = {"adaptive_one_sided": "#39D3B5", "fixed": "#E69F00", "uncontrolled": "#AABACE"}


def render(context):
    section_header("DISPATCH AUDIT", "MPC Decision Explorer", "Inspect recorded requests and scenario inputs at a historical decision. Planned six-step actions are not present in the archived traces.")
    bundle = context.get("bundle")
    block_id = int(context["block_id"])
    if bundle is None:
        st.info("Decision-level inspection needs the local input and paired controller traces. Saved episode comparison metrics remain available.")
        if context.get("replay_error"):
            st.caption(context["replay_error"])
        saved = get_table("block_metrics")
        st.dataframe(saved.loc[saved.block_id.eq(block_id)], hide_index=True, width="stretch")
        return
    step = min(max(int(context.get("step", 0)), 0), len(bundle.inputs)-1)
    default = "fixed" if context["kind"] == "fixed" else "adaptive_one_sided"
    policy = st.radio("MPC uncertainty configuration", ["adaptive_one_sided", "fixed"],
                      index=1 if default == "fixed" else 0, format_func=CASES.get,
                      horizontal=True, key="mpc_policy")
    if context["kind"] == "uncontrolled":
        st.caption("Uncontrolled wind has no optimiser. Choose an MPC configuration below to inspect its saved decision; the three-case comparison still includes the no-battery reference.")
    frame = interval_frame(block_id, policy)
    row = frame.iloc[step]
    logged = bundle.traces[policy].iloc[step]
    metrics([
        ("Decision origin", str(bundle.inputs.timestamp.iloc[step]), "Dataset clock · timezone unconfirmed"),
        ("Energy before action", f"{row.energy_before_kwh:,.2f} kWh", "Reconstructed from recorded SOC and flows"),
        ("Actual export", f"{row.grid_export_kw:,.2f} kW", "Target interval · after physical execution"),
        ("Actual ramp exceedance", f"{row.ramp_exceedance_kw:,.2f} kW", "Realised first interval, not a solver objective"),
    ])
    paths = planning_frame(block_id, policy, step)
    reveal = st.toggle("Overlay actual future targets for retrospective assessment", value=False, key="mpc_reveal_actual")
    fig = go.Figure()
    for field, label, color, dash in [
        ("nominal_kw", "Nominal scenario", "#56B4E9", "solid"),
        ("downside_kw", "Downside scenario", COLORS[policy], "dash"),
    ]:
        fig.add_trace(go.Scatter(x=paths.horizon_minutes, y=paths[field], name=label, mode="lines+markers",
                                line=dict(color=color, width=2.5, dash=dash),
                                hovertemplate="+%{x} min<br>%{y:,.2f} kW<extra>%{fullData.name}</extra>"))
    if reveal:
        fig.add_trace(go.Scatter(x=paths.horizon_minutes, y=paths.actual_kw, name="Actual targets · retrospective",
            mode="lines+markers", line=dict(color="#E4EEF8", width=2),
            hovertemplate="+%{x} min<br>%{y:,.2f} kW<extra>Not known at decision</extra>"))
    fig.update_layout(title="Six-step scenario inputs", xaxis_title="Horizon (minutes)", yaxis_title="Wind generation (kW)")
    chart(fig, "mpc_scenario_inputs")
    st.caption("Scenario inputs are reconstructed from saved XGBoost forecasts and the recorded adaptive margin or fixed calibration margin. This is not a logged optimal trajectory. Equal scenario weights are 0.5 / 0.5.")

    left, right = st.columns([1.1, 1])
    with left:
        fig = go.Figure()
        actions = ["Charge", "Discharge", "Curtailment"]
        fig.add_trace(go.Bar(x=actions, y=[logged.committed_charge_kw, logged.committed_discharge_kw, logged.committed_curtailment_kw],
                            name="Committed request · logged", marker_color="#56B4E9"))
        fig.add_trace(go.Bar(x=actions, y=[row.charge_kw, row.discharge_kw, row.curtailment_kw],
                            name="Realised first action · logged", marker_color=COLORS[policy]))
        fig.update_layout(title="First command and physical execution", barmode="group", yaxis_title="Power (kW)")
        chart(fig, "mpc_first_commands")
    with right:
        st.markdown("### Implemented constraints")
        st.dataframe(pd.DataFrame([
            ["Battery energy", "800–1,800 kWh", f"{row.energy_end_kwh:,.2f} kWh after action"],
            ["Battery power", "1,000 kW each direction", "Binary operating mode"],
            ["Charging source", "Available wind only", "No grid charging"],
            ["Soft reserve target", "1,000 kWh", "Penalty, not an extra hard lower bound"],
            ["Ramp reference", "200 kW / ten-minute change", "Soft predicted exceedance objective"],
            ["Primary allowance", "100 kW aggregate", "Weighted sum over all six steps"],
        ], columns=["Quantity", "Frozen setting", "Interpretation"]), hide_index=True, width="stretch")
    if "newest_residual_target" in logged.index:
        st.caption(f"Newest eligible residual target recorded at this decision: {logged.newest_residual_target}. The target must be strictly earlier than the decision origin.")

    comparison = []
    for kind, label in CASES.items():
        current = interval_frame(block_id, kind).iloc[step]
        comparison.append({"Case": label, "Export (kW)": current.grid_export_kw,
                           "Charge (kW)": current.charge_kw, "Discharge (kW)": current.discharge_kw,
                           "Curtailment (kW)": current.curtailment_kw,
                           "SOC (%)": current.soc_percent, "Absolute ramp (kW)": current.absolute_grid_ramp_kw,
                           "Exceedance (kW)": current.ramp_exceedance_kw})
    st.markdown("### Same target interval · all three cases")
    st.dataframe(pd.DataFrame(comparison).set_index("Case"), width="stretch")
    st.caption("No-battery actions are zero by definition and its SOC is not applicable. The controllers can have different prior exports and stored energy by this decision; comparison uses their own recorded trajectories.")

    with st.expander("Derived first-step scenario ramp assessment"):
        previous = float(row.grid_export_kw-row.signed_grid_ramp_kw)
        derived = []
        for field, label in [("nominal_kw", "Nominal"), ("downside_kw", "Downside")]:
            wind = float(paths[field].iloc[0])
            charge = min(float(logged.committed_charge_kw), wind)
            curtail = min(float(logged.committed_curtailment_kw), max(0, wind-charge))
            export = wind-charge-curtail+float(logged.committed_discharge_kw)
            ramp = export-previous
            derived.append({"Scenario": label, "Derived export (kW)": export,
                            "Derived signed ramp (kW)": ramp, "Derived first exceedance (kW)": max(0, abs(ramp)-200)})
        st.dataframe(pd.DataFrame(derived), hide_index=True, width="stretch")
        st.caption("These algebraic reconstructions use logged first requests and scenario wind. They are not stored solver internals, the full-horizon stage-one optimum, or stage-two achieved primary cost. Original logs do not expose those values.")
    st.info("Unavailable in the archived experiment: six-step planned charge/discharge/SOC trajectories, stage-one and stage-two objective values, optimality gaps and per-decision solve times. WindGrid does not fabricate them. The six-step planning display therefore shows input paths and the first recorded action only.")
    st.download_button("Download current scenario inputs CSV", paths.to_csv(index=False).encode("utf-8"),
                       file_name=f"scenario_inputs_block_{block_id}_step_{step}_{policy}.csv", mime="text/csv", key="mpc_path_download")
