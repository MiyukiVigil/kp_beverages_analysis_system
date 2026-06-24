import streamlit as st
import pandas as pd
from utils import load_menu, save_menu

def render_menu_manager():
    st.markdown('<h1><i class="bi bi-database-gear"></i> Database Maintenance</h1>', unsafe_allow_html=True)
    st.info("Add or edit drinks and prices in the table below.")
    
    menu = load_menu()
    
    menu_rows = []
    for drink, data in menu.items():
        for t_obj in data.get("temperature", []):
            menu_rows.append({
                "Drink": drink, 
                "Type (Hot/Cold)": t_obj["type"], 
                "Standard Price (RM)": t_obj["price"],
                "Big Price (RM)": t_obj.get("price_big", None)
            })
            
    # Initialize an empty DataFrame with the correct columns if the DB is blank
    if menu_rows:
        menu_df = pd.DataFrame(menu_rows)
    else:
        menu_df = pd.DataFrame(columns=["Drink", "Type (Hot/Cold)", "Standard Price (RM)", "Big Price (RM)"])
    
    edited_menu_df = st.data_editor(
        menu_df, num_rows="dynamic", use_container_width=True,
        column_config={
            "Type (Hot/Cold)": st.column_config.SelectboxColumn("Temperature", options=["Hot", "Cold"], required=True),
            "Standard Price (RM)": st.column_config.NumberColumn("Standard Price (RM)", min_value=0.0, format="%.2f", required=True),
            "Big Price (RM)": st.column_config.NumberColumn("Big Price (RM) [Hot Only]", min_value=0.0, format="%.2f")
        }
    )
    
    if st.button("💾 Apply Database Configuration", type="primary"):
        new_menu = {}
        # Drop rows missing critical data before processing
        for _, row in edited_menu_df.dropna(subset=["Drink", "Type (Hot/Cold)", "Standard Price (RM)"]).iterrows():
            d = str(row["Drink"]).strip()
            t = str(row["Type (Hot/Cold)"]).strip()
            p = float(row["Standard Price (RM)"])
            p_big = row["Big Price (RM)"]
            
            if not d or not t: continue
            
            if d not in new_menu: 
                new_menu[d] = {"temperature": []}
            
            t_entry = {"type": t, "price": p}
            
            # Only apply the price_big attribute if the type is Hot and a value was entered
            if t == "Hot" and pd.notna(p_big):
                t_entry["price_big"] = float(p_big)
                
            new_menu[d]["temperature"].append(t_entry)
            
        save_menu(new_menu)
        st.success("Database configuration committed successfully.")
        st.rerun()