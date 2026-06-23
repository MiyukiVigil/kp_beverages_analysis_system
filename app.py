import streamlit as st
from datetime import datetime

# Import components from our split files
from utils import load_settings, save_settings
from pos_view import render_pos_terminal
from analytics_view import render_analytics_dashboard
from menu_view import render_menu_manager

# ================= CONFIG & FILE SETUP =================
st.set_page_config(page_title="Kopitiam Daily Sales Log", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-family: system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        font-size: 16px;
    }
    
    .block-container {
        max-width: 1400px;
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    h1, h2, h3, h4, h5 {
        font-weight: 500;
        line-height: 1.2;
        margin-bottom: 1rem;
    }

    /* Bootstrap Primary Button */
    [data-testid="baseButton-primary"] {
        background-color: #0d6efd !important;
        border-color: #0d6efd !important;
        color: white !important;
        border-radius: 0.375rem;
        font-weight: 500;
        padding: 0.375rem 0.75rem;
    }
    
    [data-testid="baseButton-primary"]:hover {
        background-color: #0b5ed7 !important;
        border-color: #0a58ca !important;
    }

    /* Bootstrap Secondary Button */
    [data-testid="baseButton-secondary"] {
        background-color: var(--secondary-background-color) !important;
        border-color: rgba(128, 128, 128, 0.2) !important;
        border-radius: 0.375rem;
    }

    /* Cards / Containers */
    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-radius: 0.375rem !important;
        box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,.075);
        background-color: var(--secondary-background-color);
    }

    /* Tabs styling */
    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        border-bottom: 1px solid rgba(128, 128, 128, 0.2);
        gap: 0;
    }
    
    [data-testid="stTabs"] [data-baseweb="tab"] {
        padding: 0.5rem 1rem;
        border: 1px solid transparent;
        border-top-left-radius: 0.375rem;
        border-top-right-radius: 0.375rem;
        background-color: transparent;
    }

    /* Metrics styling */
    div[data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 0.375rem;
        padding: 1rem;
        background-color: var(--secondary-background-color);
    }

    /* Sidebar Polish */
    [data-testid="stSidebar"] {
        padding-top: 2rem;
    }
    [data-testid="stSidebar"] hr {
        margin: 1.5rem 0;
    }
    </style>
    """,
    unsafe_allow_html=True
)

settings = load_settings()

# ================= SIDEBAR NAVIGATION =================
with st.sidebar:
    st.markdown("### 🏢 Main Menu")
    app_mode = st.selectbox("Choose Page", ["Sales Log Terminal", "Analytics & Trends", "Menu Management"], label_visibility="collapsed")
    
    st.divider()
    today = datetime.now().date()
    
    if app_mode == "Sales Log Terminal":
        st.markdown("#### 📅 Session Configuration")
        
        selected_date = st.date_input("Working Date", value=today, max_value=today)
        selected_date_str = str(selected_date)
        
        st.write("") 
        
        with st.expander("⚙️ Recipe Config (Grams)"):
            new_big_g = st.number_input("Cold Cup Weight (g)", value=float(settings.get("big_cup_g", 20.0)), step=1.0)
            new_small_g = st.number_input("Hot Cup Weight (g)", value=float(settings.get("small_cup_g", 10.0)), step=1.0)
            if st.button("Update Recipe", use_container_width=True):
                settings["big_cup_g"] = new_big_g
                settings["small_cup_g"] = new_small_g
                save_settings(settings)
                st.success("Configuration applied!")
                st.rerun()

        st.divider()
        st.markdown("#### 📖 Quick Help")
        st.caption("🗑️ **Delete an entry:** Click the empty left margin of the target row and press `Delete` or `Backspace` on your keyboard.")

# ================= APP ROUTING =================
if app_mode == "Sales Log Terminal":
    render_pos_terminal(selected_date_str, settings)
elif app_mode == "Analytics & Trends":
    render_analytics_dashboard(settings)
elif app_mode == "Menu Management":
    render_menu_manager()