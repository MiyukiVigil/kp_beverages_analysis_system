import streamlit as st
from datetime import datetime

from utils import load_settings, save_settings
from pos_view import render_pos_terminal
from analytics_view import render_analytics_dashboard
from menu_view import render_menu_manager

# ================= CONFIG & FILE SETUP =================
st.set_page_config(page_title="Kopitiam POS", page_icon="☕", layout="wide", initial_sidebar_state="expanded")

# --- MASSIVE UI OVERHAUL (Bootstrap 5 Aesthetic + Dark Mode Support) ---
st.markdown(
    """
    <style>
    /* Import Google Fonts (Inter) and Bootstrap Icons */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    @import url('https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.3/font/bootstrap-icons.min.css');

    /* Global Typography */
    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 15px;
    }
    
    .block-container {
        max-width: 1400px;
        padding-top: 2.5rem;
        padding-bottom: 2.5rem;
    }

    h1, h2, h3, h4, h5 {
        font-weight: 600;
        letter-spacing: -0.02em;
    }

    /* Primary Button (Bootstrap Primary) */
    [data-testid="baseButton-primary"] {
        background-color: #0d6efd !important;
        border-color: #0d6efd !important;
        color: white !important;
        border-radius: 0.5rem;
        font-weight: 500;
        padding: 0.5rem 1rem;
        transition: all 0.2s ease-in-out;
        box-shadow: 0 2px 4px rgba(13, 110, 253, 0.2);
    }
    [data-testid="baseButton-primary"]:hover {
        background-color: #0b5ed7 !important;
        border-color: #0a58ca !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 6px rgba(13, 110, 253, 0.3);
    }

    /* Secondary Button (Bootstrap Light/Secondary) */
    [data-testid="baseButton-secondary"] {
        background-color: transparent !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
        color: var(--text-color) !important;
        border-radius: 0.5rem;
        font-weight: 500;
        transition: all 0.2s ease-in-out;
    }
    [data-testid="baseButton-secondary"]:hover {
        background-color: rgba(128, 128, 128, 0.1) !important;
    }

    /* Cards / Containers (Bootstrap Card) */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-radius: 0.75rem !important;
        background-color: var(--secondary-background-color);
        box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,.05);
        padding: 0.5rem;
        transition: box-shadow 0.3s ease-in-out;
    }
    [data-testid="stVerticalBlockBorderWrapper"]:hover {
        box-shadow: 0 0.5rem 1rem rgba(0,0,0,.15);
    }

    /* Tabs Styling (Sleeker Underline style) */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        border-bottom: 2px solid rgba(128, 128, 128, 0.2);
        gap: 2rem;
    }
    [data-testid="stTabs"] [data-baseweb="tab"] {
        padding: 0.75rem 0.5rem;
        border: none;
        background-color: transparent;
        font-weight: 500;
        opacity: 0.7;
    }
    [data-testid="stTabs"] [data-baseweb="tab"][aria-selected="true"] {
        color: #0d6efd !important;
        opacity: 1;
    }
    
    /* FIX: Recolor Streamlit's native animated tab highlight to prevent the double red/blue lines */
    [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
        background-color: #0d6efd !important;
    }

    /* Metrics Styling (KPI Boxes) */
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 0.75rem;
        padding: 1.25rem;
        background-color: var(--secondary-background-color);
        box-shadow: 0 2px 4px rgba(0,0,0,.02);
    }
    div[data-testid="stMetricLabel"] {
        font-weight: 500;
        opacity: 0.8;
        font-size: 0.9rem;
    }
    div[data-testid="stMetricValue"] {
        font-weight: 700;
        font-size: 1.8rem;
    }

    /* Inputs (Text, Select, Number) */
    .stTextInput input, .stNumberInput input, [data-baseweb="select"] > div {
        border-radius: 0.5rem !important;
        border: 1px solid rgba(128, 128, 128, 0.3) !important;
    }
    
    /* Sidebar Polish */
    [data-testid="stSidebar"] {
        background-color: var(--secondary-background-color);
        padding-top: 1rem;
    }
    [data-testid="stSidebar"] hr {
        margin: 1.5rem 0;
        border-color: rgba(128, 128, 128, 0.2);
    }
    </style>
    """,
    unsafe_allow_html=True
)

settings = load_settings()

# ================= SIDEBAR NAVIGATION =================
with st.sidebar:
    st.markdown('### <i class="bi bi-shop"></i> Main Menu', unsafe_allow_html=True)
    app_mode = st.radio("Navigation", 
                        ["Sales Log Terminal", "Analytics & Trends", "Menu Management"], 
                        label_visibility="collapsed")
    
    st.divider()
    today = datetime.now().date()
    selected_date_str = str(today) # Fallback string
    
    if app_mode == "Sales Log Terminal":
        st.markdown('#### <i class="bi bi-calendar-check"></i> Session Config', unsafe_allow_html=True)
        selected_date = st.date_input("Working Date", value=today, max_value=today)
        selected_date_str = str(selected_date)
        st.write("") 
        
    # Moved Recipe Config outside the if-block to make it globally persistent and stop sidebar UI lag
    st.markdown('#### <i class="bi bi-sliders"></i> Global Settings', unsafe_allow_html=True)
    with st.expander("⚙️ Recipe Config (Grams)"):
        new_big_g = st.number_input("Cold/Big Cup Weight (g)", value=float(settings.get("big_cup_g", 20.0)), step=1.0)
        new_small_g = st.number_input("Hot Small Cup Weight (g)", value=float(settings.get("small_cup_g", 10.0)), step=1.0)
        if st.button("Update Recipe", use_container_width=True):
            settings["big_cup_g"] = new_big_g
            settings["small_cup_g"] = new_small_g
            save_settings(settings)
            st.success("Configuration applied!")
            st.rerun()

    if app_mode == "Sales Log Terminal":
        st.divider()
        st.markdown('#### <i class="bi bi-question-circle"></i> Quick Help', unsafe_allow_html=True)
        st.caption("🗑️ **Delete an entry:** Click the empty left margin of the target row and press `Delete` or `Backspace` on your keyboard.")

# ================= APP ROUTING =================
if app_mode == "Sales Log Terminal":
    render_pos_terminal(selected_date_str, settings)
elif app_mode == "Analytics & Trends":
    render_analytics_dashboard(settings)
elif app_mode == "Menu Management":
    render_menu_manager()