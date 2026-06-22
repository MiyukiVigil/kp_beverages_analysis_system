import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# ================= CONFIG & FILE SETUP =================
st.set_page_config(page_title="Daily Sales Log", layout="wide")

MENU_FILE = "menu.json"
SALES_DIR = "sales"

if not os.path.exists(SALES_DIR):
    os.makedirs(SALES_DIR)

DEFAULT_MENU = {
  "Kopi": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Kopi O": { "temperature": [ { "type": "Hot", "price": 2.00 }, { "type": "Cold", "price": 2.30 } ] },
  "Kopi C": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Teh": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Teh O": { "temperature": [ { "type": "Hot", "price": 1.80 }, { "type": "Cold", "price": 2.00 } ] },
  "Teh C": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Teh Tarik": { "temperature": [ { "type": "Hot", "price": 2.50 } ] },
  "Peppermint": { "temperature": [ { "type": "Cold", "price": 2.50 } ] },
  "Liang Tea": { "temperature": [ { "type": "Cold", "price": 2.50 } ] },
  "Green Tea": { "temperature": [ { "type": "Cold", "price": 2.50 } ] },
  "Mineral Water": { "temperature": [ { "type": "Cold", "price": 1.50 } ] },
  "Sky Juice": { "temperature": [ { "type": "Cold", "price": 0.80 } ] },
  "100 Plus": { "temperature": [ { "type": "Cold", "price": 2.80 } ] },
  "Cola": { "temperature": [ { "type": "Cold", "price": 2.80 } ] }
}

# ================= HELPER FUNCTIONS =================

def load_menu():
    if not os.path.exists(MENU_FILE):
        with open(MENU_FILE, "w") as f:
            json.dump(DEFAULT_MENU, f, indent=4)
        return DEFAULT_MENU
    with open(MENU_FILE, "r") as f:
        return json.load(f)

def save_menu(menu_data):
    with open(MENU_FILE, "w") as f:
        json.dump(menu_data, f, indent=4)

def get_sales_file(date_str):
    return os.path.join(SALES_DIR, f"{date_str}.json")

def load_sales(date_str):
    file_path = get_sales_file(date_str)
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return json.load(f)
    return []

def save_sales(date_str, data):
    file_path = get_sales_file(date_str)
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

menu = load_menu()

DRINK_OPTIONS = list(menu.keys())
TYPE_OPTIONS = ["Hot", "Cold"]

def get_price(menu_dict, drink, drink_type):
    if not drink or not drink_type:
        return 0.0
    
    temps = menu_dict.get(drink, {}).get("temperature", [])
    for t in temps:
        if t["type"] == drink_type:
            return t["price"]
    return 0.0

# ================= UI =================

st.title("Cafe Daily Sales Log")
tab1, tab2, tab3 = st.tabs(["Sales Entry", "Past Reports", "Menu Manager"])

# ---------------- TAB 1: SALES ENTRY ----------------
with tab1:
    
    col_date, _ = st.columns([1, 3])
    with col_date:
        selected_date = st.date_input("Select Date for Entry", datetime.now())
        selected_date_str = str(selected_date)

    st.subheader(f"Sales Entry for {selected_date_str}")
    st.caption("Check 'Kosong' for no sugar. Check 'Tapau' for +0.20 per cup.")
    
    day_data = load_sales(selected_date_str)
    if not day_data:
        day_data = [{
            "drink": DRINK_OPTIONS[0] if DRINK_OPTIONS else "", 
            "type": "Hot", 
            "qty": 1, 
            "kosong": False, 
            "tapau": False, 
            "qr": False
        }]
        
    df = pd.DataFrame(day_data)
    
    edited_df = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "drink": st.column_config.SelectboxColumn("Drink", options=DRINK_OPTIONS, required=True),
            "type": st.column_config.SelectboxColumn("Type", options=TYPE_OPTIONS, required=True),
            "qty": st.column_config.NumberColumn("Qty", min_value=1, step=1, required=True),
            "kosong": st.column_config.CheckboxColumn("Kosong"),
            "tapau": st.column_config.CheckboxColumn("Tapau (+0.20)"),
            "qr": st.column_config.CheckboxColumn("QR Payment")
        }
    )
    
    # --- REAL-TIME CALCULATION ---
    total_sales = 0.0
    qr_sales = 0.0
    total_takeaway_cups = 0
    
    valid_rows = edited_df.dropna(subset=["drink", "type"])
    clean_data_to_save = []
    
    for _, row in valid_rows.iterrows():
        drink = row["drink"]
        drink_type = row["type"]
        
        if not drink or not drink_type: 
            continue
        
        qty = int(row["qty"])
        base_price = get_price(menu, drink, drink_type)
        is_kosong = bool(row.get("kosong", False))
        is_tapau = bool(row.get("tapau", False))
        is_qr = bool(row.get("qr", False))
        
        if is_tapau:
            total_takeaway_cups += qty
            
        extra = 0.20 if is_tapau else 0.0
        row_total = (base_price + extra) * qty
        
        total_sales += row_total
        
        if is_qr:
            qr_sales += row_total
            
        clean_data_to_save.append({
            "drink": drink,
            "type": drink_type,
            "qty": qty,
            "kosong": is_kosong,
            "tapau": is_tapau,
            "qr": is_qr
        })
        
    cash_sales = total_sales - qr_sales

    # --- METRICS DISPLAY ---
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Revenue", f"RM {total_sales:.2f}")
    m2.metric("Cash Balance", f"RM {cash_sales:.2f}")
    m3.metric("QR Revenue", f"RM {qr_sales:.2f}")
    m4.metric("Takeaway Cups", f"{total_takeaway_cups}")

    # --- ITEMS SOLD SUMMARY ---
    if clean_data_to_save:
        st.divider()
        st.subheader("Items Sold Summary")
        
        summary_df = pd.DataFrame(clean_data_to_save)
        
        # Create a clean display name
        summary_df["Display Item"] = summary_df.apply(
            lambda x: f"{x['drink']} - {x['type']} (Kosong)" if x.get("kosong", False) else f"{x['drink']} - {x['type']}", 
            axis=1
        )
        
        summary = summary_df.groupby("Display Item")["qty"].sum().reset_index()
        summary = summary.sort_values(by="qty", ascending=False)
        
        st.dataframe(
            summary, 
            hide_index=True, 
            use_container_width=True,
            column_config={
                "Display Item": "Drink Profile",
                "qty": st.column_config.NumberColumn("Total Quantity Sold")
            }
        )

    # --- SAVE BUTTON ---
    st.divider()
    if st.button("Save Log", type="primary", use_container_width=True):
        save_sales(selected_date_str, clean_data_to_save)
        st.success("Log saved successfully.")


# ---------------- TAB 2: PAST REPORTS ----------------
with tab2:
    st.subheader("View Past Sales")
    
    col_look_date, _ = st.columns([1, 3])
    with col_look_date:
        look_date = st.date_input("Select Report Date", datetime.now())
        look_date_str = str(look_date)
    
    past_data = load_sales(look_date_str)
    
    if not past_data:
        st.info(f"No sales recorded for {look_date_str}.")
    else:
        past_df = pd.DataFrame(past_data)
        
        p_total = 0.0
        p_qr = 0.0
        p_takeaway = 0
        
        for _, row in past_df.iterrows():
            # Support backwards compatibility if old data has 'item' instead of 'drink'/'type'
            if "item" in row and "drink" not in row:
                st.warning("Old data format detected. Save today's log to update format.")
                break

            base_price = get_price(menu, row["drink"], row["type"])
            extra = 0.20 if row.get("tapau", False) else 0.0
            rt = (base_price + extra) * row["qty"]
            p_total += rt
            if row.get("qr", False): p_qr += rt
            if row.get("tapau", False): p_takeaway += row["qty"]
                
        p_cash = p_total - p_qr
        
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Sales", f"RM {p_total:.2f}")
        m2.metric("Cash", f"RM {p_cash:.2f}")
        m3.metric("QR", f"RM {p_qr:.2f}")
        m4.metric("Takeaway Cups", f"{p_takeaway}")
        
        st.markdown("**Item Summary**")
        
        if "drink" in past_df.columns and "type" in past_df.columns:
            past_df["Display Item"] = past_df.apply(
                lambda x: f"{x['drink']} - {x['type']} (Kosong)" if x.get("kosong", False) else f"{x['drink']} - {x['type']}", 
                axis=1
            )
            
            past_summary = past_df.groupby("Display Item")["qty"].sum().reset_index().sort_values(by="qty", ascending=False)
            
            st.dataframe(
                past_summary, 
                hide_index=True, 
                use_container_width=True,
                column_config={"Display Item": "Drink Profile", "qty": "Quantity Sold"}
            )
        
        with st.expander("View Raw Log"):
            st.dataframe(past_df, use_container_width=True)


# ---------------- TAB 3: MENU MANAGER ----------------
with tab3:
    st.subheader("Menu Manager")
    st.markdown("""
    Update base prices or add new items. 
    * **To add a new drink:** Scroll to the bottom of the table and type in the empty row. 
    * **Note:** Kosong is managed via the tick box in the Sales Entry tab.
    """)
    
    menu_rows = []
    for drink, data in menu.items():
        for t_obj in data.get("temperature", []):
            menu_rows.append({
                "Drink": drink, 
                "Type (Hot/Cold)": t_obj["type"], 
                "Price (RM)": t_obj["price"]
            })
            
    menu_df = pd.DataFrame(menu_rows) if menu_rows else pd.DataFrame(columns=["Drink", "Type (Hot/Cold)", "Price (RM)"])
    
    edited_menu_df = st.data_editor(
        menu_df,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "Type (Hot/Cold)": st.column_config.SelectboxColumn("Type (Hot/Cold)", options=["Hot", "Cold"], required=True),
            "Price (RM)": st.column_config.NumberColumn("Price (RM)", min_value=0.0, format="%.2f")
        }
    )
    
    if st.button("Save Menu", type="primary"):
        new_menu = {}
        for _, row in edited_menu_df.dropna(subset=["Drink", "Type (Hot/Cold)"]).iterrows():
            d = str(row["Drink"]).strip()
            t = str(row["Type (Hot/Cold)"]).strip()
            
            if not d or not t:
                continue
                
            p = float(row["Price (RM)"])
            
            if d not in new_menu:
                new_menu[d] = {"temperature": []}
            
            new_menu[d]["temperature"].append({"type": t, "price": p})
            
        save_menu(new_menu)
        st.success("Menu updated successfully.")
        st.rerun()