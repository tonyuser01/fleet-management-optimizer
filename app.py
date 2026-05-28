import streamlit as st

st.set_page_config(
    page_title="Fleet Management Optimizer",
    page_icon="🚚",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2rem; font-weight: 700; color: #ffffff;
        border-bottom: 3px solid #e94560; padding-bottom: 0.5rem; margin-bottom: 1rem;
    }
    .sub-header { font-size: 1rem; color: #cccccc; margin-bottom: 2rem; }
    .stButton > button {
        background-color: #e94560; color: white;
        border: none; border-radius: 8px;
        font-weight: 600; padding: 0.5rem 2rem;
    }
    .stButton > button:hover { background-color: #c73652; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">🚚 Fleet Management Optimizer</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="sub-header">Scientific Research — Fleet Management for a General Merchandise Distributor | '
    'MSc Transport Management · National University of Science and Technology POLITEHNICA Bucharest</div>',
    unsafe_allow_html=True
)

st.markdown("### Welcome to the Fleet Management Optimization Application")
st.markdown(
    "This application implements advanced mathematical models for fleet management of a general "
    "merchandise distributor, featuring real-map visualization and multi-algorithm comparison."
)

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info("**📍 MDVRP**\n\nMulti-Depot Vehicle Routing Problem — route optimization across multiple depots")
with col2:
    st.info("**🚛 FSMVRP**\n\nFleet Size & Mix — optimal vehicle type selection for minimum cost")
with col3:
    st.info("**🗺️ Interactive Map**\n\nReal-map visualization on OpenStreetMap with animated routes")
with col4:
    st.info("**📊 Algorithm Comparison**\n\nNearest Neighbor vs Clarke-Wright Savings vs 2-opt improvement")

st.markdown("---")
st.markdown("### Navigation")
st.markdown("""
Use the left sidebar to access the application modules:

- **🗺️ Map & Data** — Configure depots, customers, fleet allocation and network data
- **📐 MDVRP Solver** — Run routing algorithms with route visualization on map
- **🚛 FSMVRP Optimizer** — Optimize fleet composition with sensitivity analysis
- **🕐 Route Timeline** — Step-by-step delivery schedule and pallet tracking
- **📖 Mathematical Models** — Full mathematical documentation with formulas
""")

st.markdown("---")

c1, c2, c3 = st.columns(3)
c1.metric("Depots", "3", "Bucharest network")
c2.metric("Customers", "20", "Active stores")
c3.metric("Vehicle types", "4", "Heterogeneous fleet")

st.markdown("---")
st.caption("Developed for dissertation research · Faculty of Transport · National University of Science and Technology POLITEHNICA Bucharest · 2024-2026")
