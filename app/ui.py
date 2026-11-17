"""Small shared visual vocabulary for the historical WindGrid platform."""
import html
import plotly.graph_objects as go
import streamlit as st

COLORS={'adaptive_one_sided':'#24D3BA','fixed':'#F4B860','uncontrolled':'#9DADC0',
        'wind':'#9DADC0','grid':'#24D3BA','charge':'#69A7FF','discharge':'#F4B860',
        'loss':'#EC8BA4','violation':'#FF8E86','text':'#E6EDF5','muted':'#A9B9CA'}

def apply_style():
    st.markdown('''<style>
    .stApp {background:#08111b; color:#e6edf5;}
    .block-container {max-width:1550px; padding:1.8rem 2.4rem 3rem;}
    [data-testid="stSidebar"] {background:#0c1724; border-right:1px solid #223449;}
    [data-testid="stMetric"] {background:#111f2f; border:1px solid #26394c;
        border-radius:12px; padding:1rem 1.05rem; min-height:108px;}
    [data-testid="stMetricLabel"] {color:#a9b9ca; font-size:.8rem;}
    [data-testid="stMetricValue"] {color:#f0f5fa; font-variant-numeric:tabular-nums; font-size:clamp(1rem,2vw,1.85rem);}
    [data-testid="stMetricDelta"] {font-size:.8rem;}
    h1,h2,h3 {letter-spacing:-.035em;}
    .wg-eyebrow {color:#24d3ba; font-weight:650; font-size:.73rem;
        letter-spacing:.17em; text-transform:uppercase; margin:0 0 .45rem;}
    .wg-note {background:#0f2131; border-left:3px solid #24d3ba;
        padding:.85rem 1rem; border-radius:0 8px 8px 0; color:#c2cfdd; margin:.6rem 0 1rem;}
    .wg-brand {font-weight:750; font-size:1.4rem; letter-spacing:-.035em; margin-bottom:0;}
    .wg-sub {font-size:.75rem; color:#9dadc0; margin:.15rem 0 1.2rem;}
    .stButton button, .stDownloadButton button {border-radius:8px; min-height:2.5rem;}
    @media(max-width:760px) {.block-container {padding:1.1rem .85rem 2rem;}
        [data-testid="stMetric"] {padding:.75rem; min-height:90px;}}
    </style>''',unsafe_allow_html=True)

def section_header(eyebrow,title,description):
    st.markdown(f'<div class="wg-eyebrow">{html.escape(eyebrow)}</div>',unsafe_allow_html=True)
    st.title(title)
    st.write(description)

def info_note(text):
    st.markdown(f'<div class="wg-note">{html.escape(text)}</div>',unsafe_allow_html=True)

def metrics(items):
    if not items:return
    cols=st.columns(len(items))
    for col,item in zip(cols,items):
        label,value,*details=item
        with col:
            st.metric(label,str(value),help=str(details[0]) if details else None)

def chart(fig,key):
    fig.update_layout(template='plotly_dark',paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='#0D1A28',font={'family':'Segoe UI, Arial, sans-serif','color':COLORS['text'],'size':12},
        colorway=[COLORS[k] for k in ['adaptive_one_sided','fixed','uncontrolled','charge','loss']],
        margin={'l':18,'r':18,'t':48,'b':40},
        legend={'orientation':'h','yanchor':'top','y':-0.16,'x':0},hovermode='x unified')
    fig.update_xaxes(gridcolor='#203247',zerolinecolor='#324860')
    fig.update_yaxes(gridcolor='#203247',zerolinecolor='#324860')
    st.plotly_chart(fig,key=key,width='stretch',config={'displaylogo':False,'scrollZoom':False})

def line_chart(frame,columns,title,ylabel,key,x='timestamp',colors=None):
    fig=go.Figure()
    for i,(field,label) in enumerate(columns.items()):
        if field in frame:
            color=(colors or {}).get(field)
            fig.add_trace(go.Scatter(x=frame[x],y=frame[field],name=label,mode='lines',
                line={'width':2,**({'color':color} if color else {})},
                hovertemplate='%{x}<br>%{y:,.2f}<extra>'+label+'</extra>'))
    fig.update_layout(title=title,height=390,yaxis_title=ylabel,xaxis_title='Target time · dataset clock')
    chart(fig,key)
