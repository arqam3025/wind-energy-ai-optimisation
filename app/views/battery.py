"""Battery activity and inventory accounting; no degradation/lifetime inference."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from platform_data import CASES, get_table, interval_frame, energy_metrics
from ui import chart, section_header, metrics

COLORS = {"adaptive_one_sided": "#39D3B5", "fixed": "#E69F00", "uncontrolled": "#AABACE"}


def _account(frame):
    values = energy_metrics(frame)
    return {"Charge (kWh AC)": values["charge_kwh"], "Discharge (kWh AC)": values["discharge_kwh"],
            "Throughput (kWh AC)": values["throughput_kwh"], "Conversion loss (kWh)": values["conversion_losses_kwh"],
            "Actual export (kWh)": values["export_kwh"], "Wind energy (kWh)": values["wind_kwh"],
            "Curtailment (kWh)": values["curtailment_kwh"], "Inventory change (kWh stored)": values["inventory_change_kwh"],
            "Hypothetical adjusted export (kWh)": values["terminal_adjusted_export_kwh"],
            "AC EFC proxy": values["efc_proxy"], "Conservation residual (kWh)": values["energy_balance_residual_kwh"]}


def render(context):
    section_header("STORAGE PERFORMANCE", "Battery Analytics", "Separate AC-side cycling exposure, conversion losses and stored inventory from actual grid energy.")
    block_id = int(context["block_id"])
    kind = context["kind"]
    frame = context.get("frame")
    totals = get_table("aggregate_metrics").set_index("controller")
    if frame is None:
        st.info("SOC distributions and interval accounting require local replay files. Frozen aggregate energy results remain available below.")
        if context.get("replay_error"):
            st.caption(context["replay_error"])
    else:
        values = _account(frame)
        metrics([
            ("Block throughput", f"{values['Throughput (kWh AC)']:,.2f} kWh", "Charge + discharge · AC side"),
            ("Modelled conversion loss", f"{values['Conversion loss (kWh)']:,.2f} kWh", "Fixed 95% efficiencies"),
            ("Equivalent-full-cycle proxy", f"{values['AC EFC proxy']:.4f}", "AC throughput / (2 × 2,000 kWh)"),
            ("Terminal inventory change", f"{values['Inventory change (kWh stored)']:+,.2f} kWh", "Relative to episode initial energy"),
        ])
        st.caption(f"Metrics cover the full saved block {block_id}; the replay cursor does not change the episode totals. The EFC value is an explicitly defined AC-throughput proxy, not measured cycles, degradation, remaining useful life or a lifetime benefit.")
        if kind == "uncontrolled":
            st.info("The uncontrolled reference contains no battery. Its battery flows and throughput are zero by definition; SOC and battery stored-energy trajectory are not applicable.")
        else:
            left, right = st.columns([1.4, 1])
            with left:
                fig = go.Figure(go.Scatter(x=frame.timestamp, y=frame.soc_percent,
                    name="Recorded SOC", line=dict(color=COLORS[kind], width=2.5),
                    hovertemplate="%{x|%d %b %H:%M}<br>SOC %{y:.3f}%<extra></extra>"))
                fig.add_hline(y=40, line_dash="dash", line_color="#F08080")
                fig.add_hline(y=90, line_dash="dash", line_color="#F08080")
                fig.add_hline(y=50, line_dash="dot", line_color="#8B9CB1")
                fig.update_layout(title="SOC trajectory · hard limits and soft reserve", xaxis_title="Target time · dataset clock",
                                  yaxis_title="SOC (%)", yaxis=dict(range=[35,95]))
                chart(fig, "battery_soc")
            with right:
                fig = go.Figure(go.Histogram(x=frame.soc_percent, xbins=dict(start=40,end=90,size=2),
                    name="Saved intervals", marker_color=COLORS[kind], hovertemplate="SOC bin %{x}%<br>%{y} intervals<extra></extra>"))
                fig.update_layout(title="SOC distribution · selected episode", xaxis_title="SOC (%)", yaxis_title="Intervals")
                chart(fig, "battery_soc_distribution")
            st.caption("Hard SOC limits are 40–90%. The 50% line corresponds to the soft 1,000 kWh reserve/reference; it is not an additional hard lower bound.")

        flow = go.Figure()
        for label, column, color in [("Cumulative throughput", "cumulative_throughput_kwh", COLORS[kind]),
                                      ("Cumulative conversion loss", "cumulative_loss_kwh", "#D88BFF")]:
            flow.add_trace(go.Scatter(x=frame.timestamp, y=frame[column], name=label, mode="lines",
                line=dict(color=color, width=2.5), hovertemplate="%{x|%d %b %H:%M}<br>%{y:,.3f} kWh<extra>%{fullData.name}</extra>"))
        flow.update_layout(title="Accumulated battery activity", xaxis_title="Target time · dataset clock", yaxis_title="Energy (kWh)")
        chart(flow, "battery_cumulative_energy")

        fig = go.Figure(go.Waterfall(orientation="v", measure=["absolute","relative","relative","relative","relative","total"],
            x=["Wind input", "− Actual export", "− Curtailment", "− Conversion loss", "− Inventory change", "Residual"],
            y=[values["Wind energy (kWh)"],-values["Actual export (kWh)"],-values["Curtailment (kWh)"],-values["Conversion loss (kWh)"],-values["Inventory change (kWh stored)"],0],
            connector=dict(line=dict(color="#62758C")), increasing=dict(marker=dict(color="#39D3B5")),
            decreasing=dict(marker=dict(color="#E69F00")), totals=dict(marker=dict(color="#56B4E9")),
            hovertemplate="%{x}<br>%{y:,.5f} kWh<extra></extra>"))
        fig.update_layout(title="Physical episode energy conservation", yaxis_title="Energy balance (kWh)")
        chart(fig, "battery_energy_waterfall")
        st.caption(f"Wind − actual export − curtailment − conversion loss − inventory change = {values['Conservation residual (kWh)']:+.3e} kWh. Depletion is a negative inventory change and therefore adds an inventory contribution in this balance.")
        with st.expander("Full episode accounting and CSV export"):
            accounting = pd.DataFrame({"Quantity": list(values), "Value": list(values.values())})
            st.dataframe(accounting, hide_index=True, width="stretch")
            st.download_button("Download battery accounting CSV", accounting.to_csv(index=False).encode("utf-8"),
                               file_name=f"battery_accounting_block_{block_id}_{kind}.csv", mime="text/csv", key="battery_download")

        energy = []
        for case, label in CASES.items():
            item = _account(interval_frame(block_id,case))
            energy.append({"Case":label,"Actual export (kWh)":item["Actual export (kWh)"],
                           "Hypothetical adjusted export (kWh)":item["Hypothetical adjusted export (kWh)"],
                           "Inventory change (kWh stored)":item["Inventory change (kWh stored)"],
                           "Curtailment (kWh)":item["Curtailment (kWh)"]})
        st.markdown("### Same episode · export and inventory")
        st.dataframe(pd.DataFrame(energy).set_index("Case"), width="stretch")

    st.markdown("### Complete frozen comparison · battery energy")
    fig = go.Figure()
    for column,label,color in [("throughput_kwh","AC throughput","#56B4E9"),
                               ("conversion_losses_kwh","Modelled conversion loss","#D88BFF"),
                               ("curtailment_kwh","Curtailment","#E69F00")]:
        fig.add_trace(go.Bar(x=[CASES[k] for k in totals.index],y=totals[column]/1000,name=label,marker_color=color,
                            hovertemplate="%{x}<br>%{y:,.6f} MWh<extra>%{fullData.name}</extra>"))
    fig.update_layout(barmode="group", yaxis_title="Energy (MWh)", title="49-block aggregate AC energy totals")
    chart(fig, "battery_aggregate_energy")
    blocks = get_table("block_metrics")
    fig = go.Figure()
    for case in ["adaptive_one_sided","fixed"]:
        item=blocks.loc[blocks.controller.eq(case)].sort_values("block_id")
        fig.add_trace(go.Bar(x=item.block_id,y=item.terminal_energy_delta_kwh,name=CASES[case],marker_color=COLORS[case]))
    fig.add_hline(y=0,line_color="#8B9CB1")
    fig.update_layout(title="Episode terminal stored-energy inventory",xaxis_title="Evaluation block · block 6 excluded",
                      yaxis_title="Final minus initial energy (kWh stored)",barmode="group")
    chart(fig, "battery_terminal_inventory")
    st.warning("Actual grid export and hypothetical terminal-SOC-adjusted export answer different questions. Adjustment values restoration to the initial inventory using efficiencies; it does not simulate restoration feasibility, future ramps, revenue or extra generated energy.")
