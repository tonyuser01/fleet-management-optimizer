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
        font-size: 2rem; font-weight: 700; color: #1a1a2e;
        border-bottom: 3px solid #e94560; padding-bottom: 0.5rem; margin-bottom: 1rem;
    }
    .sub-header { font-size: 1rem; color: #555; margin-bottom: 2rem; }
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
    'MSc Transport Management · Politehnica University of Bucharest</div>',
    unsafe_allow_html=True
)

st.markdown("""
### Welcome to the Fleet Management Optimization Application

This application implements advanced mathematical models for fleet management of a general
merchandise distributor, featuring real-map visualization and multi-algorithm comparison.

---
""")

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

- **🗺️ Map & Data** — Configure depots and customers on a real interactive map
- **📐 MDVRP Solver** — Run routing algorithms with route visualization on map
- **🚛 FSMVRP Optimizer** — Optimize fleet composition with sensitivity analysis
- **📖 Mathematical Models** — Full mathematical documentation with formulas
""")

st.markdown("---")
st.caption("Developed for dissertation research · Faculty of Transport · Politehnica University of Bucharest · 2024-2026")
