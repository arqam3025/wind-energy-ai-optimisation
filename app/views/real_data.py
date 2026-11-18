"""Real-data validation page: the pre-registered Kelmarsh sealed test (2023-2024) and its context.

Reads only the checksummed result copies in ``app/assets/real_data``. Each file is verified
against ``SOURCE.json`` before display, and nothing is recomputed or re-selected here.
"""
from pathlib import Path
import hashlib
import json

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from platform_data import ArtifactError
from ui import chart, info_note, metrics, section_header

ASSETS = Path(__file__).resolve().parents[1] / 'assets' / 'real_data'
FORECASTS = {'persistence': 'Persistence', 'lightgbm': 'LightGBM (Stage 2 features)',
             'lightgbm_spatial': 'LightGBM + neighbour turbines', 'perfect': 'Perfect forecast (privileged)'}
FORECAST_COLORS = {'persistence': '#9DADC0', 'lightgbm': '#F4B860', 'lightgbm_spatial': '#24D3BA', 'perfect': '#69A7FF'}
CONTROLLERS = {'uncontrolled': 'No battery', 'heuristic': 'Heuristic', 'deterministic': 'Deterministic MPC',
               'fixed_margin': 'Fixed-margin MPC', 'adaptive': 'Adaptive MPC', 'stochastic': 'Stochastic MPC',
               'stochastic_skill': 'Stochastic MPC + skill switch (proposed)'}
TEST_TEXT = {'R1': 'Proposed controller reduces ramp exceedance vs no battery',
             'R2': 'Proposed controller uses less battery throughput than adaptive MPC',
             'R3': 'No material harm with a persistence forecast (margin 5% of U)',
             'R4': 'No material harm with the weaker Stage 2 forecast (margin 5% of U)'}


def load(name):
    """Load one result copy after verifying its SHA-256 against SOURCE.json."""
    source = json.loads((ASSETS / 'SOURCE.json').read_text(encoding='utf-8'))
    path = ASSETS / name
    if not path.exists():
        raise ArtifactError(f'missing real-data result {name}')
    if hashlib.sha256(path.read_bytes()).hexdigest() != source['file_sha256'].get(name):
        raise ArtifactError(f'{name} does not match its recorded SHA-256')
    return json.loads(path.read_text(encoding='utf-8'))


def _descriptive(doc):
    return {(r['forecast'], r['controller']): r for r in doc['descriptive']}


def render(context=None):
    section_header('Evidence / real wind farm', 'Real-Data Validation',
                   'Pre-registered test on the Kelmarsh wind farm (UK). Forecasters were trained on 2018–2021 and '
                   'evaluated once on the sealed years 2023–2024: 2,048 paired 8-hour episodes for turbine 1. '
                   'A second site, Penmanshiel, is shown further down.')
    sealed = load('sealed_2023_2024_tests.json')
    skill = load('sealed_2023_2024_forecast_skill.json')
    rows = _descriptive(sealed)
    tests = {t['test']: t for t in sealed['tests']}
    proposed = rows[('lightgbm_spatial', 'stochastic_skill')]
    perfect = rows[('perfect', 'stochastic_skill')]
    metrics([('Hypotheses supported', f"{sum(t['supported'] for t in tests.values())} / {len(tests)}",
              'Holm-adjusted, one-sided, weekly units'),
             ('Ramp exceedance change', f"{proposed['change_vs_uncontrolled_pct']:+.1f}%",
              'Proposed controller with the neighbour-turbine forecast, vs no battery'),
             ('Throughput vs adaptive MPC', f"{tests['R2']['mean_difference']:+.0f} kWh",
              'Per 8-hour episode'),
             ('With a perfect forecast', f"{perfect['change_vs_uncontrolled_pct']:+.1f}%",
              'Privileged upper bound: the gap is due to the forecast, not the controller')])
    info_note('Forecast quality is the bottleneck. With real SCADA-only forecasts (skill about 0.15 vs persistence), '
              'the proposed controller gives a small but consistent reduction while using far less battery than '
              'margin-based MPC. With a perfect forecast, the same controller and battery remove almost all exceedance.')

    st.subheader('Pre-registered hypotheses (sealed 2023–2024)')
    table = pd.DataFrame([{
        'Test': tid, 'Claim': TEST_TEXT[tid], 'Forecast': FORECASTS[t['forecast']],
        'Mean difference': f"{t['mean_difference']:+.1f}",
        '95% CI (week-block bootstrap)': f"[{t['ci95_block_bootstrap'][0]:+.1f}, {t['ci95_block_bootstrap'][1]:+.1f}]",
        'p (Holm)': f"{t['p_holm']:.1e}", 'Supported': 'yes' if t['supported'] else 'no'} for tid, t in tests.items()])
    st.dataframe(table.set_index('Test'), width='stretch')
    st.caption('Units: R1, R3, R4 in kW of summed ramp exceedance per episode; R2 in kWh of throughput per episode. '
               f"Margin for R3/R4: {tests['R3']['margin']:.1f} kW (5% of the mean uncontrolled exceedance). "
               f"{tests['R1']['weeks']} ISO weeks are the inference unit.")

    st.subheader('Controller comparison')
    chosen = st.multiselect('Forecasts', [f for f in FORECASTS if f != 'perfect'],
                            default=['lightgbm', 'lightgbm_spatial'], format_func=FORECASTS.get,
                            key='real_data_forecasts')
    controllers = [c for c in CONTROLLERS if c != 'uncontrolled']
    fig = go.Figure()
    for forecast in chosen:
        values = [rows[(forecast, c)] for c in controllers]
        fig.add_trace(go.Bar(
            y=[CONTROLLERS[c] for c in controllers], x=[v['change_vs_uncontrolled_pct'] for v in values],
            orientation='h', name=FORECASTS[forecast], marker_color=FORECAST_COLORS[forecast],
            error_x={'type': 'data', 'symmetric': False,
                     'array': [v['change_ci95_pct'][1] - v['change_vs_uncontrolled_pct'] for v in values],
                     'arrayminus': [v['change_vs_uncontrolled_pct'] - v['change_ci95_pct'][0] for v in values]},
            hovertemplate='%{y}<br>%{x:+.2f}%<extra>' + FORECASTS[forecast] + '</extra>'))
    fig.update_layout(title='Change in ramp exceedance vs no battery (%) · 95% CI', barmode='group', height=430,
                      xaxis_title='% change (negative = fewer ramp violations)', hovermode='closest')
    fig.update_yaxes(autorange='reversed')
    chart(fig, 'real_data_controllers')

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        for c in ('fixed_margin', 'adaptive', 'stochastic', 'stochastic_skill'):
            r = rows[('lightgbm_spatial', c)]
            fig.add_trace(go.Scatter(x=[r['throughput_kwh']], y=[-r['change_vs_uncontrolled_pct']], mode='markers+text',
                                     text=[CONTROLLERS[c]], textposition='top center', name=CONTROLLERS[c],
                                     marker={'size': 16 if c == 'stochastic_skill' else 11,
                                             'color': '#24D3BA' if c == 'stochastic_skill' else '#9DADC0'},
                                     hovertemplate='%{x:.0f} kWh · %{y:.2f}% reduction<extra></extra>'))
        fig.update_layout(title='Reduction vs battery use (neighbour forecast)', height=380, showlegend=False,
                          xaxis_title='Throughput per episode (kWh)', yaxis_title='Exceedance reduction (%)',
                          hovermode='closest')
        chart(fig, 'real_data_efficiency')
    with right:
        st.markdown('**Forecast skill on 2023–2024**')
        st.dataframe(pd.DataFrame([{
            'Forecast': FORECASTS[name], 'MAE 10 / 30 / 60 min (kW)': f"{s['mae_kw'][0]:.0f} / {s['mae_kw'][2]:.0f} / {s['mae_kw'][5]:.0f}",
            'Skill vs persistence': f"{s['skill_vs_persistence']:+.3f}",
            'Ramp correlation': f"{s['ramp_correlation_abs_ramp_gt_200']:+.2f}"} for name, s in skill.items()]).set_index('Forecast'),
            width='stretch')
        st.caption('Skill = 1 − MSE(forecast) / MSE(persistence), pooled over horizons. Ramp correlation is computed on '
                   'intervals whose true 10-minute change exceeds 200 kW.')

    st.subheader('Consistency across years (proposed controller, neighbour forecast)')
    periods = [('2021', 'Development', 'development_2021_tests.json'),
               ('2022', 'Pre-freeze validation', 'validation_2022_tests.json'),
               ('2023–2024', 'Sealed test', 'sealed_2023_2024_tests.json')]
    consistency = []
    for period, role, name in periods:
        doc = load(name)
        r = _descriptive(doc)[('lightgbm_spatial', 'stochastic_skill')]
        consistency.append({'Period': period, 'Role': role, 'Episodes': r['episodes'],
                            'Change in exceedance': f"{r['change_vs_uncontrolled_pct']:+.1f}%",
                            '95% CI': f"[{r['change_ci95_pct'][0]:+.1f}, {r['change_ci95_pct'][1]:+.1f}]",
                            'Throughput (kWh)': f"{r['throughput_kwh']:.0f}",
                            'R1–R4 supported': f"{sum(t['supported'] for t in doc['tests'])} / {len(doc['tests'])}"})
    st.dataframe(pd.DataFrame(consistency).set_index('Period'), width='stretch')

    _second_site()

    simulation = load('simulation_primary_tests.json')
    st.subheader('Link to the simulation study')
    st.write(f"The pre-registered simulation study (18,900 held-out episodes) supported "
             f"**{sum(t['supported'] for t in simulation)} / {len(simulation)}** primary hypotheses. "
             'With skilful forecasts it removed 87–99% of exceedance. The real-data study confirms the same mechanism '
             '(efficiency and no-harm switch) and shows that real short-term forecasts are the limiting factor.')

    with st.expander('Integrity, deviations and limitations'):
        st.write('**Protocol:** frozen before the sealed years were opened '
                 '(SHA-256 d8337ad9…, tag stage4-protocol-frozen). The sealed test was run once by a runner that '
                 'verifies the protocol hash and a clean code tree.')
        st.write('**Deviation D1:** the 2023–2024 files were cumulative exports with partially blank duplicate rows. '
                 'Two runs stopped at data loading before any outcome was computed. An author-approved structural '
                 'check (row counts only) showed that the copies differ only by values replaced with NaN. The corrected '
                 'loader keeps the most complete version of each row and reproduces 2021 and 2022 bit for bit.')
        st.write('**Second site:** the Penmanshiel protocol was frozen separately (SHA-256 509885b8…, tag '
                 'stage5-protocol-frozen) and run once with no deviations.')
        st.write('**Limitations:** two UK sites from the same data provider, one turbine as the control unit at each; '
                 'SCADA-only forecasts; a 10-minute dispatch layer rather than second-scale ramp-rate control. The '
                 'low-pass comparisons are secondary (post-hoc) analyses.')
        st.write('**Data:** Kelmarsh wind farm data, Plumley & Takeuchi, Zenodo DOI 10.5281/zenodo.16807551; '
                 'Penmanshiel wind farm data, Zenodo DOI 10.5281/zenodo.16807304 (both CC-BY-4.0). Raw data is not '
                 'included in this app.')


SITE2_CONTROLLERS = {'heuristic': 'Heuristic', 'adaptive': 'Adaptive MPC', 'stochastic': 'Stochastic MPC',
                     'stochastic_skill': 'P: binary skill switch', 'graded_mpc': 'G: graded skill switch (proposed)',
                     'lowpass_fast': 'Low-pass filter', 'graded_lowpass': 'Graded low-pass filter'}
SITE2_TESTS = {'S1': 'G reduces ramp exceedance vs no battery',
               'S2': 'G uses less battery throughput than P',
               'S3': 'G exceedance non-inferior to P (margin 1% of U)',
               'S4': 'G uses less battery throughput than adaptive MPC',
               'S5': 'No material harm with a persistence forecast (margin 5% of U)',
               'S6': 'No material harm with the weaker Stage 2 forecast (margin 5% of U)'}


def _second_site():
    """Penmanshiel: the sealed second-site test of the graded skill switch (Stage 5)."""
    st.subheader('Second site: Penmanshiel (sealed 2023–2024)')
    sealed = load('penmanshiel_sealed_2023_2024_tests.json')
    rows = _descriptive(sealed)
    tests = {t['test']: t for t in sealed['tests']}
    g, p = rows[('lightgbm_spatial', 'graded_mpc')], rows[('lightgbm_spatial', 'stochastic_skill')]
    st.write(f"A second wind farm, never seen during design, tested with no re-tuning: turbine WT11, "
             f"{tests['S1']['episodes']:,} paired episodes. The new graded switch G scales the battery plan by the "
             'released forecast skill instead of switching it on or off.')
    metrics([('Hypotheses supported', f"{sum(t['supported'] for t in tests.values())} / {len(tests)}",
              'Holm-adjusted, one-sided, weekly units'),
             ('G: exceedance change', f"{g['change_vs_uncontrolled_pct']:+.1f}%", 'Neighbour forecast, vs no battery'),
             ('Battery use vs P', f"{(g['throughput_kwh'] / p['throughput_kwh'] - 1) * 100:+.0f}%",
              f"{g['throughput_kwh']:.0f} vs {p['throughput_kwh']:.0f} kWh per episode"),
             ('P: exceedance change', f"{p['change_vs_uncontrolled_pct']:+.1f}%", 'Kelmarsh controller, replicated')])
    st.dataframe(pd.DataFrame([{
        'Test': tid, 'Claim': SITE2_TESTS[tid], 'Forecast': FORECASTS[t['forecast']],
        'Mean difference': f"{t['mean_difference']:+.1f}",
        '95% CI (week-block bootstrap)': f"[{t['ci95_block_bootstrap'][0]:+.1f}, {t['ci95_block_bootstrap'][1]:+.1f}]",
        'p (Holm)': f"{t['p_holm']:.1e}", 'Supported': 'yes' if t['supported'] else 'no'} for tid, t in tests.items()
    ]).set_index('Test'), width='stretch')
    st.caption('Units: S1, S3, S5, S6 in kW of summed ramp exceedance per episode; S2, S4 in kWh of throughput per episode.')

    left, right = st.columns(2)
    with left:
        fig = go.Figure()
        for c, label in SITE2_CONTROLLERS.items():
            r = rows[('lightgbm_spatial', c)]
            y = -r['change_vs_uncontrolled_pct']
            lo, hi = (-v for v in r['change_ci95_pct'][::-1])
            proposed = c == 'graded_mpc'
            fig.add_trace(go.Scatter(
                x=[r['throughput_kwh']], y=[y], mode='markers', name=label,
                error_y={'type': 'data', 'symmetric': False, 'array': [hi - y], 'arrayminus': [y - lo]},
                marker={'size': 16 if proposed else 11, 'symbol': 'diamond' if 'lowpass' in c else 'circle',
                        'color': '#24D3BA' if proposed else ('#F4B860' if 'lowpass' in c else '#9DADC0')},
                hovertemplate=label + '<br>%{x:.0f} kWh · %{y:.2f}% reduction<extra></extra>'))
        fig.update_layout(title='Reduction vs battery use (neighbour forecast) · 95% CI', height=400,
                          xaxis_title='Throughput per episode (kWh)', yaxis_title='Exceedance reduction (%)',
                          hovermode='closest', legend={'orientation': 'h', 'y': -0.25})
        chart(fig, 'penmanshiel_efficiency')
    with right:
        periods = [('2021', 'Development', 'penmanshiel_development_2021_tests.json'),
                   ('2022', 'Pre-freeze validation', 'penmanshiel_validation_2022_tests.json'),
                   ('2023–2024', 'Sealed test', 'penmanshiel_sealed_2023_2024_tests.json')]
        table = []
        for period, role, name in periods:
            r = _descriptive(load(name))
            for c in ('graded_mpc', 'stochastic_skill'):
                v = r[('lightgbm_spatial', c)]
                table.append({'Period': period, 'Role': role, 'Controller': 'G (graded)' if c == 'graded_mpc' else 'P (binary)',
                              'Change in exceedance': f"{v['change_vs_uncontrolled_pct']:+.2f}%",
                              'Throughput (kWh)': f"{v['throughput_kwh']:.0f}"})
        st.markdown('**Consistency across years (neighbour forecast)**')
        st.dataframe(pd.DataFrame(table).set_index('Period'), width='stretch')
    info_note('G gives the same ramp reduction as P with about half the battery use, at a second site and without '
              're-tuning. Adaptive MPC and a forecast-driven low-pass filter reduce exceedance more, but use more battery '
              'per kW avoided; G and the graded low-pass filter are the most efficient. These low-pass comparisons are '
              'secondary analyses.')
