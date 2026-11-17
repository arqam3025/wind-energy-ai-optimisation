"""Grid-ramp comparison including the measured no-battery reference."""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from platform_data import CASES, get_table, interval_frame, comparisons
from ui import chart, section_header, metrics

COLORS = {"adaptive_one_sided":"#39D3B5","fixed":"#E69F00","uncontrolled":"#AABACE"}


def _events(frame):
    data=frame.copy()
    data["uncontrolled_exceedance_kw"]=np.maximum(0,data.uncontrolled_ramp_kw-200)
    data["exceedance_change_kw"]=data.ramp_exceedance_kw-data.uncontrolled_exceedance_kw
    data["introduced_violation"]=data.ramp_violation & (data.uncontrolled_ramp_kw<=200.001)
    data["removed_violation"]=(~data.ramp_violation) & (data.uncontrolled_ramp_kw>200.001)
    data["delta_net_injection_kw"]=np.diff(np.r_[0.,data.discharge_kw.to_numpy()-data.charge_kw.to_numpy()-data.curtailment_kw.to_numpy()])
    return data


def render(context):
    section_header("REALISED GRID BEHAVIOUR", "Grid Stability Lab", "Compare magnitude, frequency and exceedance separately. An improvement versus another MPC is not automatically an improvement over uncontrolled wind.")
    block_id=int(context["block_id"])
    kind=context["kind"]
    frame=context.get("frame")
    if frame is None:
        st.info("Interval-level ramp diagnostics require the local paired traces and forecast inputs. Aggregate case comparisons remain available below.")
        if context.get("replay_error"):
            st.caption(context["replay_error"])
    else:
        frames={case:_events(interval_frame(block_id,case)) for case in CASES}
        data=frames[kind]
        metrics([
            ("Block violations", f"{int(data.ramp_violation.sum())}", "> 200.001 kW absolute change"),
            ("Block exceedance sum", f"{data.ramp_exceedance_kw.sum():,.2f} kW", "Sum of max(|Δexport| − 200, 0)"),
            ("Introduced / removed", f"{int(data.introduced_violation.sum())} / {int(data.removed_violation.sum())}", "Relative to uncontrolled at same target"),
            ("Exceedance vs uncontrolled", f"{data.exceedance_change_kw.sum():+,.2f} kW", "Positive means deterioration"),
        ])
        mode=st.radio("Ramp display",["Absolute","Signed"],horizontal=True,key="grid_ramp_mode")
        fig=go.Figure()
        for case,label in CASES.items():
            item=frames[case]
            values=item.absolute_grid_ramp_kw if mode=="Absolute" else item.signed_grid_ramp_kw
            fig.add_trace(go.Scatter(x=item.timestamp,y=values,name=label,mode="lines",line=dict(color=COLORS[case],width=2),
                                    hovertemplate="%{x|%d %b %H:%M}<br>%{y:+,.2f} kW<extra>%{fullData.name}</extra>"))
        fig.add_hline(y=200,line_dash="dot",line_color="#F08080")
        if mode=="Signed":fig.add_hline(y=-200,line_dash="dot",line_color="#F08080")
        fig.update_layout(title=f"Block {block_id} · {mode.lower()} ten-minute changes",xaxis_title="Target time · dataset clock",yaxis_title=f"{mode} ramp (kW)",hovermode="x unified")
        chart(fig,"grid_ramp_comparison")
        st.caption("All three cases use 144 identical target transitions, including origin wind to first output. Previous export follows each case's own trajectory. No cross-episode transition is scored. The count tolerance is 0.001 kW; exceedance itself starts at 200 kW.")

        fig=go.Figure()
        for case in ["adaptive_one_sided","fixed"]:
            item=frames[case]
            fig.add_trace(go.Bar(x=item.timestamp,y=item.exceedance_change_kw,name=CASES[case],marker_color=COLORS[case],
                                hovertemplate="%{x|%d %b %H:%M}<br>%{y:+,.2f} kW<extra>Controlled − uncontrolled exceedance</extra>"))
        fig.add_hline(y=0,line_color="#8B9CB1")
        fig.update_layout(title="Where MPC improves or worsens exceedance",xaxis_title="Target time · dataset clock",yaxis_title="Controlled − uncontrolled exceedance (kW)",barmode="group")
        chart(fig,"grid_exceedance_delta")
        st.caption("Negative bars improve exceedance; positive bars worsen it. Each transition can be influenced by both current action and the preceding injection.")

        st.markdown("### Event investigation")
        choice=st.radio("Transition filter",["All transitions","MPC worsens","MPC improves","Introduced violations","Removed violations"],horizontal=True,key="grid_event_filter")
        if choice=="MPC worsens":filtered=data.loc[data.exceedance_change_kw>1e-6]
        elif choice=="MPC improves":filtered=data.loc[data.exceedance_change_kw<-1e-6]
        elif choice=="Introduced violations":filtered=data.loc[data.introduced_violation]
        elif choice=="Removed violations":filtered=data.loc[data.removed_violation]
        else:filtered=data
        if kind=="uncontrolled":st.caption("The uncontrolled reference has zero controlled-minus-uncontrolled change by definition. Select an MPC case to investigate introduced or removed violations.")
        if filtered.empty:
            st.info("No transitions match this filter for the selected case and episode.")
        else:
            default=int(context.get("step",0))
            options=filtered.index.tolist()
            index=options.index(default) if default in options else 0
            event=st.selectbox("Inspect target interval",options,index=index,
                               format_func=lambda i:f"{i+1:03d} · {data.loc[i,'timestamp']} · Δexceedance {data.loc[i,'exceedance_change_kw']:+.2f} kW",
                               key="grid_event")
            row=data.loc[event]
            metrics([
                ("Wind change",f"{row.wind_ramp_kw:+,.2f} kW","Measured target-to-target change"),
                ("Injection change",f"{row.delta_net_injection_kw:+,.2f} kW","Δ(discharge − charge − curtailment)"),
                ("Grid change",f"{row.signed_grid_ramp_kw:+,.2f} kW","Exact sum of the two changes"),
            ])
            window=slice(max(0,int(event)-5),min(len(data),int(event)+6))
            fig=go.Figure()
            for case,label in CASES.items():
                part=frames[case].iloc[window]
                fig.add_trace(go.Scatter(x=part.timestamp,y=part.grid_export_kw,name=label,mode="lines+markers",
                                        line=dict(color=COLORS[case],width=2)))
            fig.add_shape(type="line",x0=row.timestamp,x1=row.timestamp,y0=0,y1=1,yref="paper",line=dict(color="#D88BFF",dash="dot"))
            fig.update_layout(title="Actual event window · no simulation restart",xaxis_title="Target time · dataset clock",yaxis_title="Grid export (kW)")
            chart(fig,"grid_event_window")
        columns=["timestamp","wind_ramp_kw","signed_grid_ramp_kw","delta_net_injection_kw","ramp_exceedance_kw","exceedance_change_kw","introduced_violation","removed_violation","charge_kw","discharge_kw","soc_percent"]
        with st.expander("Filtered event table and export"):
            st.dataframe(filtered[columns],hide_index=True,width="stretch")
            st.download_button("Download selected ramp-event CSV",filtered[columns].to_csv(index=False).encode("utf-8"),
                               file_name=f"grid_events_block_{block_id}_{kind}.csv",mime="text/csv",key="grid_event_download")

    st.markdown("### All 49 frozen episodes · baseline matters")
    st.dataframe(comparisons(),width="stretch")
    st.warning("Both MPC controllers have more aggregate violations and summed exceedance than uncontrolled wind, while reducing the maximum ramp. These retrospective outcomes do not establish grid-code compliance, universal grid stability improvement, or a guaranteed operating envelope.")
    blocks=get_table("block_metrics")
    baseline=get_table("uncontrolled_wind_baseline").set_index("block_id")
    outcome=st.selectbox("Episode outcome",["ramp_exceedance_kw","ramp_violations"],
                         format_func=lambda x:"Summed exceedance (kW)" if x=="ramp_exceedance_kw" else "Violation count",key="grid_block_outcome")
    fig=go.Figure()
    for case in ["adaptive_one_sided","fixed"]:
        part=blocks.loc[blocks.controller.eq(case)].set_index("block_id").sort_index()
        delta=part[outcome]-baseline.loc[part.index,outcome]
        fig.add_trace(go.Bar(x=part.index,y=delta,name=CASES[case],marker_color=COLORS[case]))
    fig.add_hline(y=0,line_color="#8B9CB1")
    fig.update_layout(title="Episode deterioration / improvement versus uncontrolled",xaxis_title="Evaluation block · block 6 excluded",
                      yaxis_title="Difference (kW)" if outcome=="ramp_exceedance_kw" else "Difference (violations)",barmode="group")
    chart(fig,"grid_block_changes")
