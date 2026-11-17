"""Command Center and time-step digital twin over recorded research outputs."""
import time
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from platform_data import CASES,ArtifactError,comparisons,energy_metrics
from ui import section_header,metrics,chart,line_chart,info_note,COLORS

def power_flow(row,kind,key):
    wind=float(row.wind_generation_kw);charge=float(row.charge_kw)
    discharge=float(row.discharge_kw);curtail=float(row.curtailment_kw)
    direct=max(0,wind-charge-curtail)
    fig=go.Figure(go.Sankey(arrangement='fixed',node={
        'label':['Wind generation','Battery','Grid export','Curtailment'],
        'color':[COLORS['wind'],COLORS['charge'],COLORS['grid'],COLORS['loss']],
        'x':[.03,.49,.96,.49],'y':[.20,.10,.20,.80],
        'pad':28,'thickness':18,'line':{'color':'#304559','width':1}},link={
        'source':[0,0,1,0],'target':[2,1,2,3],
        'value':[direct,charge,discharge,curtail],
        'label':['Direct wind export','Charging','Discharging','Curtailed wind'],
        'color':['rgba(157,173,192,.35)','rgba(105,167,255,.45)','rgba(36,211,186,.45)','rgba(236,139,164,.45)'],
        'hovertemplate':'%{label}: %{value:,.2f} kW<extra></extra>'}))
    fig.update_layout(title='Recorded turbine → battery → grid power flow',height=310)
    chart(fig,key)
    st.caption('Flow widths are instantaneous interval power (kW), not energy or live telemetry. '
               +('Uncontrolled is the calculated no-battery reference; SOC is not applicable.' if kind=='uncontrolled' else 'Battery state is the recorded post-interval SOC.'))

def _row_metrics(frame,step,kind):
    row=frame.iloc[step]
    metrics([('Wind generation',f'{row.wind_generation_kw:,.1f} kW','Observed target power'),
        ('Grid export',f'{row.grid_export_kw:,.1f} kW','Recorded or calculated no-battery export'),
        ('Battery SOC','N/A' if kind=='uncontrolled' else f'{row.soc_percent:.2f}%','Post-interval state'),
        ('Absolute grid ramp',f'{row.absolute_grid_ramp_kw:,.1f} kW','10-minute difference; threshold 200 kW')])
    return row

def command_center(context):
    section_header('Operations / historical research','Command Center',
        'One shared replay state connects the turbine, storage and grid views. Every value comes from saved outputs or the explicit uncontrolled reference.')
    frame=context.get('frame')
    if frame is None:
        st.warning(context.get('replay_error') or 'Select an available recorded block to inspect interval state.')
        try:st.dataframe(comparisons(),width='stretch')
        except ArtifactError as error:st.error(str(error))
        return
    step=context['step'];kind=context['kind'];row=_row_metrics(frame,step,kind)
    st.caption(f'{CASES[kind]} · block {context["block_id"]} · recorded interval {step+1}/144 · target {row.timestamp}')
    power_flow(row,kind,'command_flow')
    left,right=st.columns([1.7,1])
    with left:
        line_chart(frame,{'wind_generation_kw':'Uncontrolled wind','grid_export_kw':'Selected export'},
            'Episode power profile','Power (kW)','command_profile')
    with right:
        st.subheader('Replay state')
        st.write(f'**Decision:** {row.decision_time}')
        st.write(f'**Target:** {row.timestamp}')
        st.write(f'**Charging / discharging:** {row.charge_kw:,.2f} / {row.discharge_kw:,.2f} kW')
        st.write(f'**Curtailment:** {row.curtailment_kw:,.2f} kW')
        status='Threshold exceeded' if row.ramp_violation else 'Within displayed ramp threshold'
        (st.warning if row.ramp_violation else st.info)(status)
        st.caption('This status is one retrospective transition; it does not certify grid compliance.')
    st.subheader('Event timeline')
    events=frame.loc[frame.ramp_violation].copy()
    if len(events):
        options=events.index.astype(int).tolist()
        def jump():
            st.session_state.time_step=int(st.session_state.command_event)
            st.session_state.playing=False
        st.selectbox('Jump to recorded violation',options,index=None,
            format_func=lambda i:f'Interval {i+1:03d} · {frame.iloc[i].timestamp} · {frame.iloc[i].absolute_grid_ramp_kw:,.1f} kW',
            key='command_event',on_change=jump)
        fig=go.Figure(go.Scatter(x=events.timestamp,y=events.absolute_grid_ramp_kw,mode='markers',
            name='Recorded violations',marker={'size':8,'color':COLORS['violation']},
            hovertemplate='%{x}<br>Absolute ramp %{y:.2f} kW<extra></extra>'))
        fig.add_hline(y=200,line_dash='dash',line_color=COLORS['muted'])
        fig.update_layout(height=260,yaxis_title='Absolute ramp (kW)',xaxis_title='Target time')
        chart(fig,'command_events')
        st.dataframe(events[['timestamp','absolute_grid_ramp_kw','ramp_exceedance_kw','charge_kw','discharge_kw']].rename(columns={
            'absolute_grid_ramp_kw':'Ramp (kW)','ramp_exceedance_kw':'Exceedance (kW)','charge_kw':'Charge (kW)','discharge_kw':'Discharge (kW)'}),hide_index=True,width='stretch')
    else:st.info('No violations in this recorded block for the selected case.')

def _change_step(amount,n):
    st.session_state.pending_step=max(0,min(n-1,int(st.session_state.time_step)+amount))
    st.session_state.playing=False
    st.rerun(scope='app')

def digital_twin(context):
    section_header('Operations / recorded digital twin','Digital Twin',
        'Play back the saved simulation in ten-minute steps. Playback changes the viewing cursor; it does not rerun the controller or generate new measurements.')
    if context.get('frame') is None:
        st.warning(context.get('replay_error') or 'Local interval artifacts are required for the digital twin.')
        return
    @st.fragment(run_every=.5 if st.session_state.get('playing',False) else None)
    def workspace():
        n=len(context['frame']);step=int(st.session_state.time_step)
        if st.session_state.get('playing',False):
            now=time.monotonic()
            if now-st.session_state.get('last_tick',now)>=float(st.session_state.playback_speed):
                st.session_state.pending_step=min(n-1,step+1)
                st.session_state.last_tick=now
                if step+1>=n-1:st.session_state.playing=False
                st.rerun(scope='app')
        controls=st.columns([1,1,1,1,1,2.2])
        if controls[0].button('Play',icon=':material/play_arrow:',key='play',disabled=step>=n-1,type='primary'):
            st.session_state.playing=True;st.session_state.last_tick=time.monotonic();st.rerun(scope='app')
        if controls[1].button('Pause',icon=':material/pause:',key='pause'):
            st.session_state.playing=False;st.rerun(scope='app')
        if controls[2].button('Back',icon=':material/skip_previous:',key='step_back',disabled=step==0):_change_step(-1,n)
        if controls[3].button('Step',icon=':material/skip_next:',key='step_forward',disabled=step>=n-1):_change_step(1,n)
        if controls[4].button('Reset',icon=':material/replay:',key='reset_playback'):
            st.session_state.pending_step=0;st.session_state.playing=False;st.rerun(scope='app')
        controls[5].selectbox('Seconds per recorded step',[.5,1.,2.,5.],index=1,key='playback_speed',
            help='Viewing speed only. The physical timestep always remains ten minutes.')
        st.progress((step+1)/n,text=f'{"Playing" if st.session_state.get("playing",False) else "Paused"} · interval {step+1:03d}/{n} · 10 minutes per interval')
        if step==n-1:st.info('End of recorded block. Playback stops here; Reset returns to the first interval.')
        row=_row_metrics(context['frame'],step,context['kind'])
        history=context['frame'].iloc[:step+1]
        power_flow(row,context['kind'],'twin_flow')
        a,b=st.columns(2)
        with a:
            line_chart(history,{'charge_kw':'Charging','discharge_kw':'Discharging','battery_net_power_kw':'Net battery injection'},
                'Battery commands realised so far','Power (kW)','twin_battery')
        with b:
            if context['kind']=='uncontrolled':st.info('Uncontrolled wind has no battery. SOC and stored battery energy are not applicable.')
            else:
                fig=go.Figure(go.Scatter(x=history.timestamp,y=history.soc_percent,name='Recorded SOC',mode='lines',line={'color':COLORS['adaptive_one_sided']}))
                fig.add_hrect(y0=40,y1=90,fillcolor='rgba(36,211,186,.06)',line_width=0)
                for bound in [40,90]:fig.add_hline(y=bound,line_dash='dash',line_color='#8FA3B8')
                fig.update_layout(title='SOC and hard bounds',height=390,yaxis_title='SOC (%)',yaxis_range=[35,95])
                chart(fig,'twin_soc')
        line_chart(history,{'wind_generation_kw':'Available wind','grid_export_kw':'Grid export','curtailment_kw':'Curtailment'},
            'Recorded power balance','Power (kW)','twin_export')
        cumulative=energy_metrics(context['frame'],upto=step)
        # Display the exact instantaneous balance independently of energy summary fields.
        residual=float(row.wind_generation_kw-row.charge_kw-row.curtailment_kw+row.discharge_kw-row.grid_export_kw)
        st.subheader('Physical balance at this recorded step')
        metrics([('Charge',f'{row.charge_kw:,.2f} kW','Wind-only charging'),('Discharge',f'{row.discharge_kw:,.2f} kW','Positive battery export'),
            ('Curtailment',f'{row.curtailment_kw:,.2f} kW','Wind withheld'),('Power residual',f'{residual:.3e} kW','wind − charge − curtailment + discharge − export')])
        st.code(f'{row.wind_generation_kw:.3f} − {row.charge_kw:.3f} − {row.curtailment_kw:.3f} + {row.discharge_kw:.3f} = {row.grid_export_kw:.3f} kW',language=None)
        st.caption('Energy accounting uses 0.95 charge/discharge efficiency and a 1/6-hour interval. The export shown above is actual simulated export; hypothetical terminal restoration is shown separately in Battery Analytics.')
        with st.expander('Cumulative recorded energy accounting'):
            st.dataframe(pd.DataFrame([cumulative]),hide_index=True,width='stretch')
        st.download_button('Download replay through this step',history.to_csv(index=False).encode(),
            file_name=f'windgrid_recorded_{context["kind"]}_block_{context["block_id"]}_through_{step+1}.csv',mime='text/csv')
    workspace()
