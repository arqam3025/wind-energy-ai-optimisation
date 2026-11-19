"""Controller Lab: run the validated controllers live, closed loop, on the bundled Penmanshiel sample.

Every decision goes through ``windgrid.service.dispatch``, the same code path as the HTTP API, so
what is shown here is what the API would do. The sample (14 days of February 2022, CC-BY-4.0) is a
demonstration; the evidence for the method is on the Real-Data Validation page.
"""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from windgrid import service, simulate

from ui import chart, info_note, metrics, section_header

COLORS = {
    'graded_mpc': '#24D3BA',
    'stochastic_skill': '#69A7FF',
    'stochastic': '#8E7CFF',
    'adaptive': '#F47C7C',
    'lowpass_fast': '#F4B860',
    'graded_lowpass': '#E8D07A',
    'heuristic': '#B7C4D1',
    'uncontrolled': '#9DADC0',
}
LABELS = {
    'graded_mpc': 'G: graded skill switch (proposed)',
    'stochastic_skill': 'P: binary skill switch',
    'stochastic': 'Stochastic MPC',
    'adaptive': 'Adaptive MPC',
    'lowpass_fast': 'Low-pass filter',
    'graded_lowpass': 'Graded low-pass filter',
    'heuristic': 'Heuristic',
    'uncontrolled': 'No battery',
}


@st.cache_data(show_spinner=False, max_entries=256)
def _replay(controller, forecast, episode):
    series = simulate.load_sample()[forecast]
    result = simulate.replay(series, simulate.sample_episode_starts(forecast)[episode], controller)
    return result['metrics'], pd.DataFrame(result['trace'])


def render(context=None):
    section_header(
        'Live control / closed loop',
        'Controller Lab',
        'Run the battery controllers decision by decision on real turbine data. Each 10-minute decision '
        'uses only data released before it, exactly as in deployment and through the same code as the API.',
    )
    left, middle, right = st.columns([2, 1, 1])
    chosen = left.multiselect(
        'Controllers',
        list(service.CONTROLLERS),
        default=['graded_mpc', 'stochastic_skill', 'lowpass_fast', 'adaptive'],
        format_func=LABELS.get,
        key='lab_controllers',
    )
    forecast = middle.selectbox(
        'Forecast', simulate.SAMPLE_FORECASTS, format_func=simulate.FORECAST_LABELS.get, key='lab_forecast'
    )
    starts = simulate.sample_episode_starts(forecast)
    series = simulate.load_sample()[forecast]
    episode = right.selectbox(
        '8-hour episode',
        range(len(starts)),
        index=min(14, len(starts) - 1),
        format_func=lambda i: series.times[starts[i]].strftime('%d %b %Y, %H:%M UTC'),
        key='lab_episode',
    )
    if not chosen:
        st.info('Select at least one controller.')
        return
    with st.spinner('Running the closed loop…'):
        runs = {c: _replay(c, forecast, episode) for c in dict.fromkeys(['uncontrolled', *chosen])}
    base = runs['uncontrolled'][0]['total_ramp_exceedance_kw']
    lead = chosen[0]
    lead_metrics, lead_trace = runs[lead]
    change = 100 * (lead_metrics['total_ramp_exceedance_kw'] / base - 1) if base > 0 else 0.0
    metrics(
        [
            (f'{LABELS[lead]}: exceedance', f'{change:+.1f}%', 'Ramp exceedance vs no battery, this episode'),
            ('Battery throughput', f'{lead_metrics["total_throughput_kwh"]:.0f} kWh', 'Charge + discharge, 8 hours'),
            (
                'Ramp violations',
                f'{lead_metrics["ramp_violations"]} vs {runs["uncontrolled"][0]["ramp_violations"]}',
                'Intervals above 200 kW per 10 min (controller vs none)',
            ),
            ('Decision time', f'{lead_trace["computation_ms"].median():.1f} ms', 'Median per 10-minute decision'),
        ]
    )

    times = pd.to_datetime(lead_trace['decision_time']) + pd.Timedelta(minutes=10)
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=times,
            y=runs['uncontrolled'][1]['grid_kw'],
            name='Wind power (no battery)',
            line={'color': '#9DADC0', 'width': 2, 'dash': 'dot'},
        )
    )
    for c in chosen:
        if c != 'uncontrolled':
            fig.add_trace(
                go.Scatter(x=times, y=runs[c][1]['grid_kw'], name=LABELS[c], line={'color': COLORS[c], 'width': 2})
            )
    fig.update_layout(
        title='Power exported to the grid (kW)',
        height=380,
        hovermode='x unified',
        yaxis_title='kW',
        legend={'orientation': 'h', 'y': -0.2},
    )
    chart(fig, 'lab_grid')

    a, b = st.columns(2)
    with a:
        fig = go.Figure()
        for c in chosen:
            trace = runs[c][1]
            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=100 * trace['energy_after_kwh'] / 2000.0,
                    name=LABELS[c],
                    line={'color': COLORS[c], 'width': 2},
                )
            )
        fig.add_hrect(y0=40, y1=90, fillcolor='#24D3BA', opacity=0.05, line_width=0)
        fig.update_layout(
            title='Battery state of charge (%) · allowed 40–90%',
            height=320,
            hovermode='x unified',
            yaxis_title='%',
            showlegend=False,
        )
        chart(fig, 'lab_soc')
    with b:
        trace = runs[lead][1]
        fig = go.Figure()
        fig.add_trace(
            go.Scatter(x=times, y=trace['skill_score'], name='Released skill score', line={'color': '#69A7FF', 'width': 2})
        )
        if trace['skill_weight'].notna().any():
            fig.add_trace(
                go.Scatter(
                    x=times,
                    y=trace['skill_weight'],
                    name='Graded weight w',
                    line={'color': '#24D3BA', 'width': 2, 'dash': 'dash'},
                )
            )
        fig.add_hline(y=0.10, line={'color': '#F4B860', 'dash': 'dot'}, annotation_text='binary switch 0.10')
        fig.update_layout(
            title=f'Forecast skill seen by the controller ({LABELS[lead]})',
            height=320,
            hovermode='x unified',
            legend={'orientation': 'h', 'y': -0.25},
        )
        chart(fig, 'lab_skill')

    st.dataframe(
        pd.DataFrame(
            [
                {
                    'Controller': LABELS[c],
                    'Ramp exceedance (kW)': f'{runs[c][0]["total_ramp_exceedance_kw"]:.0f}',
                    'Change vs none': f'{100 * (runs[c][0]["total_ramp_exceedance_kw"] / base - 1):+.1f}%'
                    if base > 0
                    else '—',
                    'Violations': runs[c][0]['ramp_violations'],
                    'Throughput (kWh)': f'{runs[c][0]["total_throughput_kwh"]:.0f}',
                    'SOC range': f'{100 * runs[c][0]["minimum_soc"]:.0f}–{100 * runs[c][0]["maximum_soc"]:.0f}%',
                }
                for c in runs
            ]
        ).set_index('Controller'),
        width='stretch',
    )
    info_note(
        'One episode is a demonstration, not evidence: single episodes vary a lot. The pre-registered results '
        'over 2,000+ episodes per wind farm are on the Real-Data Validation page.'
    )
    with st.expander('Use the same controller through the API'):
        st.code(
            'windgrid serve                      # http://127.0.0.1:8000/docs\n'
            'curl -s "http://127.0.0.1:8000/v1/sample" > request.json\n'
            'curl -s -X POST http://127.0.0.1:8000/v1/dispatch \\\n'
            '     -H "Content-Type: application/json" -d @request.json',
            language='bash',
        )
        st.caption(
            'Data: Penmanshiel wind farm SCADA, Zenodo DOI 10.5281/zenodo.16807304 (CC-BY-4.0); February 2022, '
            'turbine WT11. Forecasts: this project.'
        )
