import streamlit as st
import pandas as pd
from utils import load_menu, save_menu

def render_menu_manager():
    st.title("Database Maintenance")
    st.info("System configuration module. Append entries by utilizing the terminal row at the bottom of the dataset.")
    
    menu = load_menu()
    
    menu_rows = []
    for drink, data in menu.items():
        for t_obj in data.get("temperature", []):
            menu_rows.append({"Drink": drink, "Type (Hot/Cold)": t_obj["type"], "Price (RM)": t_obj["price"]})
            
    menu_df = pd.DataFrame(menu_rows) if menu_rows else pd.DataFrame(columns=["Drink", "Type (Hot/Cold)", "Price (RM)"])
    
    edited_menu_df = st.data_editor(
        menu_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "Type (Hot/Cold)": st.column_config.SelectboxColumn("Variant Architecture", options=["Hot", "Cold"], required=True),
            "Price (RM)": st.column_config.NumberColumn("Unit Price (RM)", min_value=0.0, format="%.2f")
        }
    )
    
    if st.button("Apply Database Configuration", type="primary"):
        new_menu = {}
        for _, row in edited_menu_df.dropna(subset=["Drink", "Type (Hot/Cold)"]).iterrows():
            d, t, p = str(row["Drink"]).strip(), str(row["Type (Hot/Cold)"]).strip(), float(row["Price (RM)"])
            if not d or not t: continue
            if d not in new_menu: new_menu[d] = {"temperature": []}
            new_menu[d]["temperature"].append({"type": t, "price": p})
        save_menu(new_menu)
        st.success("Database configuration committed successfully.")
        st.rerun()