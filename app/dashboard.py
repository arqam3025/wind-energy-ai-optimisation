"""WindGrid AI entry point: eight registered historical research pages."""
from pathlib import Path
import sys
import streamlit as st

APP_DIRECTORY=Path(__file__).resolve().parent
if str(APP_DIRECTORY) not in sys.path:
    sys.path.insert(0,str(APP_DIRECTORY))
from platform_data import CASES, ArtifactError, valid_blocks, get_replay, interval_frame
from ui import apply_style

st.set_page_config(page_title="WindGrid AI — Wind–Battery Digital Twin",
    page_icon=":material/wind_power:",layout="wide",initial_sidebar_state="auto")
apply_style()

for key,value in [("time_step",0),("playing",False),("playback_speed",1.0),("last_tick",0.0)]:
    if key not in st.session_state: st.session_state[key]=value
if "pending_step" in st.session_state:
    st.session_state.time_step=max(0,min(143,int(st.session_state.pop("pending_step"))))

def reset_replay():
    st.session_state.time_step=0
    st.session_state.playing=False
    st.session_state.pop("pending_step",None)
    st.session_state.pop("command_event",None)
    st.session_state.pop("mpc_policy",None)

def pause_on_scrub():
    st.session_state.playing=False

with st.sidebar:
    st.markdown('<div class="wg-brand">WindGrid <span style="color:#24d3ba">AI</span></div>',unsafe_allow_html=True)
    st.markdown('<div class="wg-sub">WIND–BATTERY DIGITAL TWIN<br>Research platform / recorded operation</div>',unsafe_allow_html=True)

page=st.navigation({
    "OPERATIONS":[
        st.Page("screens/command_center.py",title="Command Center",icon=":material/dashboard:",url_path="command-center",default=True),
        st.Page("screens/digital_twin.py",title="Digital Twin",icon=":material/play_circle:",url_path="digital-twin")],
    "ANALYSIS":[
        st.Page("screens/forecasting.py",title="AI Forecasting Lab",icon=":material/query_stats:",url_path="forecasting"),
        st.Page("screens/mpc.py",title="MPC Decision Explorer",icon=":material/account_tree:",url_path="mpc"),
        st.Page("screens/battery.py",title="Battery Analytics",icon=":material/battery_charging_full:",url_path="battery"),
        st.Page("screens/grid.py",title="Grid Stability Lab",icon=":material/electric_bolt:",url_path="grid")],
    "EVIDENCE":[
        st.Page("screens/results.py",title="Research Results",icon=":material/science:",url_path="results"),
        st.Page("screens/real_data.py",title="Real-Data Validation",icon=":material/public:",url_path="real-data"),
        st.Page("screens/reproducibility.py",title="Reproducibility",icon=":material/verified:",url_path="reproducibility")]
},position="sidebar",expanded=True)
if st.session_state.get("_last_windgrid_page")!=page.title:
    st.session_state.playing=False
    st.session_state["_last_windgrid_page"]=page.title

summary_error=None
try:blocks=valid_blocks()
except ArtifactError as error:
    blocks=[]
    summary_error=str(error)

with st.sidebar:
    st.divider()
    st.caption("SHARED HISTORICAL CONTEXT")
    kind=st.selectbox("Comparison case",list(CASES),format_func=CASES.get,key="controller",on_change=reset_replay)
    block_id=st.selectbox("Evaluation block",blocks,format_func=lambda b:f"Block {b}",key="block_id",on_change=reset_replay)
    horizon=st.select_slider("Forecast horizon (minutes)",options=[10,20,30,40,50,60],value=10,key="horizon")
    step=st.slider("Recorded interval",min_value=0,max_value=143,key="time_step",on_change=pause_on_scrub,
        help="Zero-based cursor. Each recorded physical step is ten minutes; viewing speed does not change the simulation.")
    st.caption(f"Interval {step+1:03d} / 144 · ten-minute timestep")
    st.caption("Block 6 is development and excluded. Battery resets to 50% SOC per episode; uncertainty history carries forward causally.")
    with st.expander("Frozen system assumptions"):
        st.write("2,000 kWh capacity · 1,000 kW charge/discharge")
        st.write("SOC 40–90% · charge/discharge efficiency 95%")
        st.write("Six-step horizon · 200 kW ramp threshold")
        st.write("100 kW weighted primary allowance · soft 1,000 kWh reserve")
    st.caption("Offline research replay. No live telemetry or physical control interface.")

bundle=None
frame=None
replay_error=None
if block_id is not None:
    try:
        bundle=get_replay(int(block_id))
        frame=interval_frame(int(block_id),kind)
    except ArtifactError as error:
        replay_error=str(error)
else:
    replay_error=summary_error or "Missing valid block summaries."
    st.error(replay_error)

st.session_state["_windgrid_context"]={
    "kind":kind,"block_id":block_id,"step":int(step),"horizon":int(horizon),
    "bundle":bundle,"frame":frame,"replay_error":replay_error,"summary_error":summary_error}
st.caption("WINDGRID AI  /  WIND–BATTERY DIGITAL TWIN  /  HISTORICAL RESEARCH")
st.caption("Historical playback of saved outputs · no live telemetry, grid-compliance guarantee or battery-lifetime claim.")
with st.expander("Research interpretation and limitations",expanded=False):
    st.write("Adaptive uses less battery throughput than fixed margins. Both MPC controllers nevertheless increase aggregate ramp violations and exceedance versus uncontrolled wind, while reducing the maximum ramp.")
    st.write("The frozen 49-block comparison is retrospective. Evaluation-period investigation predates the freeze, and five scored block-7 targets overlap development block 6. It is not an untouched confirmatory evaluation.")
    st.write("Actual export and hypothetical terminal-SOC-adjusted export are separate. One-sided lower uncertainty bounds have no established distribution-free, conditional or joint multi-horizon coverage guarantee.")
page.run()
