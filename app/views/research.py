"""Frozen comparison, reproducibility and explicitly bounded research claims."""
from pathlib import Path
import json
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from platform_data import (CASES,ROOT,ArtifactError,comparisons,get_table,integrity_report,
                           environment_summary,validation_summary,data_root)
from ui import chart,section_header,metrics,info_note,COLORS

def results(context):
    section_header('Evidence / original evaluation','Research Results',
        'The original 49-block comparison, preserved unchanged. Explore paired outcomes without selecting or retuning a controller on these results.')
    comparison=comparisons();blocks=get_table('block_metrics');paired=get_table('paired_differences')
    metrics([('Scored episodes','49','Block 6 excluded'),('Transitions per case','7,056','144 per episode, including initial transition'),
        ('Adaptive throughput change','−27.86%','Relative to fixed, not to uncontrolled'),('Adaptive violation difference','−16','1,486 versus 1,502 fixed')])
    st.warning('Both MPC controllers have more aggregate violations and exceedance than uncontrolled wind. Earlier test-period inspection and five block-7 targets shared with development block 6 make this a retrospective comparison, not an untouched confirmatory test.')
    labels={'ramp_violations':'Violation count','ramp_exceedance_kw':'Summed exceedance (kW)',
        'throughput_kwh':'Throughput (kWh AC)','conversion_losses_kwh':'Conversion losses (kWh)',
        'export_kwh':'Actual export (kWh)','terminal_adjusted_export_kwh':'Hypothetical adjusted export (kWh)'}
    outcome=st.selectbox('Aggregate outcome',list(labels),format_func=labels.get,key='results_outcome')
    fig=go.Figure(go.Bar(x=comparison.label,y=comparison[outcome],
        marker_color=[COLORS[k] for k in comparison.index],
        hovertemplate='%{x}<br>%{y:,.3f}<extra></extra>'))
    fig.update_layout(title=labels[outcome]+' · all original episodes',yaxis_title=labels[outcome],height=360)
    chart(fig,'results_aggregate')
    display=comparison[['label','ramp_violations','ramp_exceedance_kw','throughput_kwh','conversion_losses_kwh',
        'export_kwh','terminal_adjusted_export_kwh','terminal_energy_delta_kwh']].copy()
    display=display.set_index('label').rename(columns={'ramp_violations':'Violations','ramp_exceedance_kw':'Exceedance (kW sum)',
        'throughput_kwh':'Throughput (kWh AC)','conversion_losses_kwh':'Losses (kWh)','export_kwh':'Actual export (kWh)',
        'terminal_adjusted_export_kwh':'Hypothetical adjusted export (kWh)','terminal_energy_delta_kwh':'Inventory change (kWh stored)'})
    st.dataframe(display,width='stretch')
    st.caption('A missing adjusted-export value for uncontrolled wind means no battery inventory exists. Adjustment is hypothetical restoration accounting; actual export is reported separately. Neither throughput nor the AC-cycle proxy establishes a lifetime benefit.')
    st.subheader('Paired outcomes by episode')
    options={'throughput_kwh':'Throughput (kWh AC)','ramp_exceedance_kw':'Exceedance (kW)',
        'ramp_violations':'Violation count','conversion_losses_kwh':'Conversion loss (kWh)',
        'terminal_adjusted_export_kwh':'Hypothetical adjusted export (kWh)'}
    key=st.selectbox('Paired metric',list(options),format_func=options.get,key='results_paired_metric')
    columns=st.columns(2)
    with columns[0]:
        fig=go.Figure(go.Bar(x=paired.block_id,y=paired[key],
            marker_color=[COLORS['adaptive_one_sided'] if x<0 else COLORS['fixed'] for x in paired[key]],
            hovertemplate='Block %{x}<br>Adaptive − fixed: %{y:,.3f}<extra></extra>'))
        fig.add_hline(y=0,line_color='#8BA0B6')
        fig.update_layout(title='Adaptive minus fixed',xaxis_title='Evaluation block · 6 excluded',yaxis_title=options[key],height=370)
        chart(fig,'results_paired_bar')
    with columns[1]:
        pivot=blocks.pivot(index='block_id',columns='controller',values=key)
        extent=float(pivot.max().max())
        fig=go.Figure(go.Scatter(x=pivot.fixed,y=pivot.adaptive_one_sided,mode='markers',
            marker={'color':COLORS['adaptive_one_sided'],'size':8},text=pivot.index,
            hovertemplate='Block %{text}<br>Fixed %{x:,.3f}<br>Adaptive %{y:,.3f}<extra></extra>',name='Original paired block'))
        fig.add_trace(go.Scatter(x=[0,extent],y=[0,extent],mode='lines',line={'color':'#8BA0B6','dash':'dash'},name='Equality'))
        fig.update_layout(title='Episode comparison',xaxis_title='Fixed · '+options[key],yaxis_title='Adaptive · '+options[key],height=370)
        chart(fig,'results_paired_scatter')
    st.caption('Negative differences favour adaptive for ramp costs, throughput and losses; positive favours adaptive for adjusted export. Colour denotes the sign, not statistical significance.')
    st.subheader('Empirical uncertainty coverage')
    coverage=get_table('uncertainty_coverage').groupby(['horizon_minutes','controller']).lower_bound_coverage.mean().unstack()
    fig=go.Figure()
    for kind in coverage:
        fig.add_trace(go.Scatter(x=coverage.index,y=coverage[kind]*100,name=CASES[kind],mode='lines+markers',line={'color':COLORS[kind]}))
    fig.add_hline(y=90,line_dash='dash',line_color='#A9B9CA',annotation_text='Nominal reference, not a guarantee')
    fig.update_layout(yaxis_title='Marginal lower-bound coverage (%)',xaxis_title='Horizon (minutes)',height=340)
    chart(fig,'results_coverage')
    with st.expander('Statistical interpretation and original descriptive resampling'):
        st.dataframe(get_table('paired_summary'),hide_index=True,width='stretch')
        st.write('The original 10,000-draw paired day bootstrap resamples days independently. Its intervals are descriptive, not dependence-adjusted confirmatory confidence intervals. The ramp-exceedance and violation-count intervals span zero. Overlapping horizons, adjacent weather periods and only four contiguous segments limit independent-sample inference.')
        st.write('Adaptive changes residual direction, floors and window updating together. Margins sit at static floors for roughly 86–88% of decisions; this comparison cannot isolate rolling adaptation as the cause of battery savings.')
    st.subheader('Research table export')
    name=st.selectbox('Saved table',['aggregate_metrics','block_metrics','paired_differences','paired_summary','forecast_metrics','uncertainty_coverage','uncontrolled_wind_baseline'],key='results_download_table')
    table=get_table(name)
    st.download_button('Download saved research table',table.to_csv(index=False).encode(),file_name=f'windgrid_{name}.csv',mime='text/csv')
    st.caption('Downloads reproduce saved summary tables. Loading validates their schema; the separate Reproducibility page verifies the freeze and its referenced artifacts.')

def reproducibility(context):
    section_header('Provenance / repeatable science','Reproducibility',
        'Check source integrity, inspect the software environment and distinguish current checks from historical validation records.')
    report=integrity_report()
    metrics([('Freeze SHA256','MATCH' if report['manifest_match'] else report['status'].upper(),'Exact expected development freeze'),
        ('Referenced artifacts',f'{report["checked_files"]} / 59','Five source files and 54 development results'),
        ('Data mode','Historical replay','No live turbine or inverter connection')])
    (st.success if report['status']=='pass' else st.warning)(report.get('message','Freeze verification unavailable.'))
    if st.button('Verify freeze and references again',icon=':material/verified:',key='verify_freeze'):
        report=integrity_report()
        (st.success if report['status']=='pass' else st.error)(report.get('message',report['status']))
    st.code(report['expected_sha256'],language=None)
    if report['source_checks']:
        with st.expander('Individual source and development-result hashes'):
            st.dataframe(pd.DataFrame(report['source_checks']),hide_index=True,width='stretch')
    st.caption('The original manifest is never rewritten. A matching development freeze does not establish prior test blindness or authenticate every later experiment. Current replay loading checks schema, timestamp alignment and physical constraints separately.')
    environment=environment_summary()
    st.subheader('Current local environment')
    st.write(f'**Python {environment["python"]}** · {environment["platform"]}')
    st.dataframe(pd.DataFrame(environment['packages'].items(),columns=['Package','Installed version']),hide_index=True,width='stretch')
    saved=validation_summary()
    st.subheader('Validation evidence')
    st.info(saved['message'])
    if saved['available']:
        st.caption('Saved record: '+saved.get('path','unknown'))
        with st.expander('Prior research validation record · not a new UI test run'):
            st.json(saved['record'])
    current=data_root()/'audits/windgrid_dashboard_20261029/validation_report.json'
    if current.exists():
        with st.expander('WindGrid platform test record'):
            st.json(json.loads(current.read_text(encoding='utf-8')))
    else:st.caption('Current WindGrid platform test evidence is not present in this checkout. Run the commands below; do not infer UI correctness from the older research record.')
    st.subheader('Local research documents')
    documents={'Submission draft':'docs/paper_submission_draft.md','Grid-ramp diagnostic':'docs/grid_ramp_diagnostic.md',
        'Mathematical formulation':'docs/mathematical_formulation.md','Methodology':'docs/methodology.md',
        'Literature review':'docs/literature_review.md','Reproduction guide':'docs/reproducibility.md',
        'Scientific limitations':'docs/unresolved_scientific_issues.md'}
    for label,name in documents.items():
        path=data_root()/name
        if path.is_file():
            st.download_button(label+' · Markdown',path.read_bytes(),file_name=path.name,mime='text/markdown',key='doc_'+path.stem)
        else:st.caption(label+' unavailable: '+name)
    st.subheader('Repeatable commands')
    st.code('.venv/Scripts/python.exe -B -m unittest discover -s tests -v\n.venv/Scripts/python.exe -B scripts/verify_research_completion.py',language='powershell')
    st.code('.venv/Scripts/python.exe -m streamlit run app/dashboard.py --server.address 127.0.0.1 --server.port 8501 --browser.gatherUsageStats false',language='powershell')
    st.write('A full frozen replay requires the original local input/calibration/development files and CVXPY/HiGHS. Summary-only installations can explore aggregate research tables. Use a unique output directory for every additional simulation; never alter or overwrite the original evaluation.')
    st.code('.venv/Scripts/python.exe scripts/run_frozen_heldout.py --run my_unique_replay --blocks 1',language='powershell')
    st.warning('A one-block rerun is not a new full evaluation. No parameter tuning or exploratory battery model is embedded in playback. Original runners skip existing CSVs by existence; independently verify resumed files. No source, dataset, calibration, manifest or original result is changed by WindGrid.')
