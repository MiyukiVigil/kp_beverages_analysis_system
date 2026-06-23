import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime
from exporter import generate_excel, generate_pdf

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

    [data-testid="baseButton-secondary"] {
        background-color: var(--secondary-background-color) !important;
        border-color: rgba(128, 128, 128, 0.2) !important;
        border-radius: 0.375rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        border: 1px solid rgba(128, 128, 128, 0.2) !important;
        border-radius: 0.375rem !important;
        box-shadow: 0 0.125rem 0.25rem rgba(0,0,0,.075);
        background-color: var(--secondary-background-color);
    }

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

    div[data-testid="stMetric"] {
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-radius: 0.375rem;
        padding: 1rem;
        background-color: var(--secondary-background-color);
    }
    </style>
    """,
    unsafe_allow_html=True
)

MENU_FILE = "menu.json"
SETTINGS_FILE = "settings.json"
SALES_DIR = "sales"

if not os.path.exists(SALES_DIR):
    os.makedirs(SALES_DIR)

DEFAULT_MENU = {
  "Kopi": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Kopi O": { "temperature": [ { "type": "Hot", "price": 2.00 }, { "type": "Cold", "price": 2.30 } ] },
  "Teh": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] }
}

DEFAULT_SETTINGS = {
    "big_cup_g": 20.0,
    "small_cup_g": 10.0
}

# ================= HELPER FUNCTIONS =================

def load_settings():
    if not os.path.exists(SETTINGS_FILE):
        with open(SETTINGS_FILE, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=4)
        return DEFAULT_SETTINGS
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def save_settings(settings_data):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings_data, f, indent=4)

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
            data = json.load(f)
            if isinstance(data, list):
                return {"transactions": data, "actual_kg": 0.0}
            return data
    return {"transactions": [], "actual_kg": 0.0}

def save_sales(date_str, transactions, actual_kg):
    data = {
        "transactions": transactions,
        "actual_kg": actual_kg
    }
    with open(get_sales_file(date_str), "w") as f:
        json.dump(data, f, indent=4)

def load_all_historical_sales(menu_dict, settings_dict):
    all_records = []
    if not os.path.exists(SALES_DIR): return pd.DataFrame()
    
    big_g = settings_dict.get("big_cup_g", 20.0)
    small_g = settings_dict.get("small_cup_g", 10.0)
    
    for filename in os.listdir(SALES_DIR):
        if filename.endswith(".json"):
            date_str = filename.replace(".json", "")
            try:
                valid_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                file_path = os.path.join(SALES_DIR, filename)
                with open(file_path, "r") as f:
                    day_data_raw = json.load(f)
                    
                if isinstance(day_data_raw, dict):
                    day_data = day_data_raw.get("transactions", [])
                    actual_kg = day_data_raw.get("actual_kg", 0.0)
                else:
                    day_data = day_data_raw
                    actual_kg = 0.0
                    
                day_expected_g = 0.0
                for row in day_data:
                    drink = row.get("drink", "")
                    dtype = row.get("type", "")
                    qty = row.get("qty", 0)
                    if "Kopi" in drink:
                        day_expected_g += (small_g if "Hot" in dtype else big_g) * qty
                
                day_expected_kg = day_expected_g / 1000.0
                    
                for row in day_data:
                    drink = row.get("drink", "")
                    drink_type = row.get("type", "")
                    if not drink or not drink_type: continue
                    
                    qty = row.get("qty", 0)
                    is_tapau = row.get("tapau", False)
                    is_qr = row.get("qr", False)
                    is_kosong = row.get("kosong", False)
                    
                    base_price = get_price(menu_dict, drink, drink_type)
                    extra = 0.20 if is_tapau else 0.0
                    row_revenue = (base_price + extra) * qty
                    
                    display_name = f"{drink} - {drink_type} (Kosong)" if is_kosong else f"{drink} - {drink_type}"
                    
                    item_coffee_g = 0.0
                    if "Kopi" in drink:
                        item_coffee_g = (small_g if "Hot" in drink_type else big_g) * qty

                    all_records.append({
                        "Date": valid_date,
                        "Drink Base": drink,
                        "Drink Type": drink_type,
                        "Drink Profile": display_name,
                        "Qty": qty,
                        "Revenue": row_revenue,
                        "QR Revenue": row_revenue if is_qr else 0.0,
                        "Takeaway": qty if is_tapau else 0,
                        "Expected Coffee (kg)": item_coffee_g / 1000.0,
                        "Day Actual Coffee (kg)": actual_kg,
                        "Day Expected Coffee (kg)": day_expected_kg
                    })
            except ValueError:
                continue 
                
    return pd.DataFrame(all_records)

menu = load_menu()
settings = load_settings()
DRINK_OPTIONS = list(menu.keys())
TIN_DRINKS = {"100 Plus", "Cola"}
TYPE_OPTIONS = sorted({
    temp["type"]
    for drink_data in menu.values()
    for temp in drink_data.get("temperature", [])
    if temp.get("type")
})

def is_blank_value(value):
    return value is None or pd.isna(value) or str(value).strip() == ""

def clean_text(value):
    if is_blank_value(value):
        return ""
    return str(value).strip()

def is_tin_drink(drink):
    return clean_text(drink) in TIN_DRINKS

def parse_qty(value):
    if is_blank_value(value):
        return 1
    try:
        return max(int(value), 1)
    except (TypeError, ValueError):
        return 1

def parse_bool(value):
    if is_blank_value(value):
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}

def clean_sales_rows(rows):
    clean_rows = []
    for row in rows:
        drink = clean_text(row.get("drink"))
        drink_type = clean_text(row.get("type"))
        if not drink and not drink_type:
            continue
        clean_rows.append({
            "drink": drink,
            "type": drink_type,
            "qty": parse_qty(row.get("qty", 1)),
            "kosong": parse_bool(row.get("kosong", False)),
            "tapau": False if is_tin_drink(drink) else parse_bool(row.get("tapau", False)),
            "qr": parse_bool(row.get("qr", False)),
        })
    return clean_rows

def get_price(menu_dict, drink, drink_type):
    if not drink or not drink_type:
        return 0.0
    temps = menu_dict.get(drink, {}).get("temperature", [])
    for t in temps:
        if t["type"] == drink_type:
            return t["price"]
    return 0.0

# ================= SIDEBAR NAVIGATION =================
with st.sidebar:
    st.header("Navigation")
    app_mode = st.radio("Module Selection", ["POS Terminal", "Analytics & Trends"], label_visibility="collapsed")
    
    st.divider()
    
    today = datetime.now().date()
    
    if app_mode == "POS Terminal":
        st.header("Terminal Settings")
        
        selected_date = st.date_input("Working Date", value=today, max_value=today)
        selected_date_str = str(selected_date)
        st.caption(f"Active Session: {selected_date_str}")
        
        with st.expander("Inventory Recipe Configuration"):
            new_big_g = st.number_input("Cold Cup Weight (g)", value=float(settings.get("big_cup_g", 20.0)), step=1.0)
            new_small_g = st.number_input("Hot Cup Weight (g)", value=float(settings.get("small_cup_g", 10.0)), step=1.0)
            if st.button("Update Configuration", use_container_width=True):
                settings["big_cup_g"] = new_big_g
                settings["small_cup_g"] = new_small_g
                save_settings(settings)
                st.success("Configuration applied successfully.")
                st.rerun()

        st.divider()
        st.markdown("#### User Guide")
        st.info("To remove an entry, select the left margin of the target row and press Delete or Backspace.")

# ================= APP ROUTING =================

if app_mode == "POS Terminal":
    
    if "current_date" not in st.session_state or st.session_state.current_date != selected_date_str:
        st.session_state.current_date = selected_date_str
        sales_data = load_sales(selected_date_str)
        st.session_state.day_transactions = sales_data["transactions"]
        st.session_state.actual_kg = sales_data["actual_kg"]

    st.title("Point of Sale Terminal")
    tab1, tab2, tab3 = st.tabs(["Transaction Entry", "Daily Reconciliation", "Menu Management"])

    # ---------------- TAB 1: REGISTER ----------------
    with tab1:
        st.subheader("Process New Transaction")
        with st.container(border=True):
            col1, col2, col3 = st.columns([2.1, 1.6, 1], gap="medium")
            
            with col1:
                selected_drink = st.selectbox("Beverage Selection", DRINK_OPTIONS, key="add_drink")
            with col2:
                valid_types = [t["type"] for t in menu.get(selected_drink, {}).get("temperature", [])]
                selected_type = st.radio("Variant", valid_types, horizontal=True)
            with col3:
                add_qty = st.number_input("Quantity", min_value=1, step=1)
                
            modifier_col, action_col = st.columns([1.6, 1], gap="medium")
            with modifier_col:
                st.markdown("**Transaction Modifiers**")
                mod1, mod2, mod3 = st.columns(3, gap="small")
                with mod1:
                    is_kosong = st.checkbox("Kosong (No Sugar)")
                with mod2:
                    tapau_disabled = is_tin_drink(selected_drink)
                    is_tapau = st.checkbox(
                        "Takeaway",
                        disabled=tapau_disabled,
                        help="Packaging modifiers disabled for canned beverages." if tapau_disabled else None,
                    )
                    if tapau_disabled:
                        is_tapau = False
                with mod3:
                    is_qr = st.checkbox("QR/Digital Payment")
            with action_col:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("Append to Ledger", type="primary", use_container_width=True):
                    st.session_state.day_transactions.append({
                        "drink": selected_drink,
                        "type": selected_type,
                        "qty": add_qty,
                        "kosong": is_kosong,
                        "tapau": is_tapau,
                        "qr": is_qr
                    })
                    st.rerun()

        st.subheader(f"Ledger Overview: {selected_date_str}")
        
        with st.container(border=True):
            invalid_rows = []

            if not st.session_state.day_transactions:
                st.info(f"The transaction ledger for {selected_date_str} is currently empty.")
                edited_data = []
                day_total = 0.0
                cash_total = 0.0
                qr_total = 0.0
            else:
                df_log = pd.DataFrame(st.session_state.day_transactions)
                expected_columns = ["drink", "type", "qty", "kosong", "tapau", "qr"]
                defaults = {
                    "drink": "", "type": "", "qty": 1,
                    "kosong": False, "tapau": False, "qr": False,
                }

                for column, default in defaults.items():
                    if column not in df_log.columns:
                        df_log[column] = default

                df_log = df_log[expected_columns]
                drink_options_for_editor = sorted({
                    *DRINK_OPTIONS,
                    *[clean_text(value) for value in df_log["drink"] if clean_text(value)]
                })
                type_options_for_editor = sorted({
                    *TYPE_OPTIONS,
                    *[clean_text(value) for value in df_log["type"] if clean_text(value)]
                })
                
                edited_df = st.data_editor(
                    df_log,
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "drink": st.column_config.SelectboxColumn("Beverage", options=drink_options_for_editor, required=True),
                        "type": st.column_config.SelectboxColumn("Variant", options=type_options_for_editor, required=True),
                        "qty": st.column_config.NumberColumn("Volume", min_value=1, step=1),
                        "kosong": "Kosong",
                        "tapau": "Takeaway (+0.20)",
                        "qr": "Digital Payment"
                    }
                )
                
                edited_data = clean_sales_rows(edited_df.to_dict('records'))
                st.session_state.day_transactions = edited_data
                
                day_total = 0.0
                qr_total = 0.0
                invalid_rows = []
                
                for item in edited_data:
                    if not item.get("drink") or not item.get("type"): 
                        continue
                    
                    base_price = get_price(menu, item["drink"], item["type"])
                    if base_price == 0.0:
                        invalid_rows.append(f"{item['drink']} - {item['type']}")
                        continue

                    extra = 0.20 if item.get("tapau") and not is_tin_drink(item.get("drink")) else 0.0
                    row_val = (base_price + extra) * item.get("qty", 1)
                    
                    day_total += row_val
                    if item.get("qr"):
                        qr_total += row_val
                        
                cash_total = day_total - qr_total

                if invalid_rows:
                    st.warning("Data mismatch: Certain entries do not correspond to active menu items. Please verify entries.")
                
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Gross Revenue", f"RM {day_total:.2f}")
            m2.metric("Cash Drawer Expected", f"RM {cash_total:.2f}")
            m3.metric("Digital Collection", f"RM {qr_total:.2f}")
            
            st.divider()
            st.markdown("#### Closing Inventory Validation")
            input_actual_kg = st.number_input(
                "Physical Coffee Grounds Utilized (kg)", 
                min_value=0.0, step=0.100, format="%.3f", 
                value=float(st.session_state.actual_kg)
            )

            if st.button("Commit Ledger & Inventory", type="primary", use_container_width=True, disabled=len(st.session_state.day_transactions) == 0 or bool(invalid_rows)):
                valid_items = [item for item in clean_sales_rows(edited_data) if item.get("drink") and item.get("type")]
                
                save_sales(selected_date_str, valid_items, input_actual_kg)
                st.session_state.actual_kg = input_actual_kg
                
                st.success(f"System synchronized successfully for {selected_date_str}.")

    # ---------------- TAB 2: DAILY REPORT ----------------
    with tab2:
        st.subheader(f"End of Day Report: {selected_date_str}")
        
        past_data_full = load_sales(selected_date_str)
        past_transactions = past_data_full.get("transactions", [])
        saved_actual_kg = past_data_full.get("actual_kg", 0.0)
        
        if not past_transactions:
            st.warning("No committed transactions found for the selected date.")
        else:
            past_df = pd.DataFrame(past_transactions)
            
            p_total = 0.0
            p_qr = 0.0
            p_takeaway = 0
            expected_coffee_used_g = 0.0 
            
            for _, row in past_df.iterrows():
                drink_name = row.get("drink", "")
                drink_type = row.get("type", "")
                qty = row.get("qty", 0)

                base_price = get_price(menu, drink_name, drink_type)
                extra = 0.20 if row.get("tapau", False) and not is_tin_drink(drink_name) else 0.0
                rt = (base_price + extra) * qty
                
                p_total += rt
                if row.get("qr", False): p_qr += rt
                if row.get("tapau", False) and not is_tin_drink(drink_name): p_takeaway += qty
                
                if "Kopi" in drink_name:
                    if "Hot" in drink_type:
                        expected_coffee_used_g += (settings.get("small_cup_g", 10.0) * qty)
                    elif "Cold" in drink_type:
                        expected_coffee_used_g += (settings.get("big_cup_g", 20.0) * qty)
                    else:
                        expected_coffee_used_g += (settings.get("big_cup_g", 20.0) * qty)
                    
            p_cash = p_total - p_qr
            total_cups = past_df["qty"].sum() if not past_df.empty else 0
            
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Gross Revenue", f"RM {p_total:.2f}")
            m2.metric("Cash Balance", f"RM {p_cash:.2f}")
            m3.metric("Digital Revenue", f"RM {p_qr:.2f}")
            m4.metric("Takeaway Volume", f"{p_takeaway}")
            
            st.divider()
            st.markdown("#### Inventory Reconciliation (Coffee Grounds)")
            
            expected_kg = expected_coffee_used_g / 1000
            
            inv_col1, inv_col2, inv_col3 = st.columns(3)
            
            with inv_col1:
                st.metric("System Expected Usage", f"{expected_kg:.3f} kg")
            with inv_col2:
                st.metric("Physical Record", f"{saved_actual_kg:.3f} kg")
            with inv_col3:
                if saved_actual_kg > 0:
                    variance = saved_actual_kg - expected_kg
                    if variance > 0.1:
                        st.metric("Calculated Variance", f"{variance:+.3f} kg", delta_color="inverse")
                        st.error("Audit Required: Physical usage exceeds system projection.")
                    elif variance < -0.1:
                        st.metric("Calculated Variance", f"{variance:+.3f} kg", delta_color="normal")
                        st.warning("Review Required: Physical usage falls below system projection.")
                    else:
                        st.metric("Calculated Variance", f"{variance:+.3f} kg", delta_color="off")
                        st.success("Reconciliation successful. Data within accepted tolerances.")
                else:
                    st.info("Awaiting physical inventory input for reconciliation.")
            
            st.divider()
            
            col_summary, col_raw = st.columns([1, 1])
            
            with col_summary:
                st.markdown("#### Item Performance")
                if "drink" in past_df.columns and "type" in past_df.columns:
                    past_df["Display Item"] = past_df.apply(
                        lambda x: f"{x['drink']} - {x['type']} (Kosong)" if x.get("kosong", False) else f"{x['drink']} - {x['type']}", 
                        axis=1
                    )
                    past_summary = past_df.groupby("Display Item")["qty"].sum().reset_index().sort_values(by="qty", ascending=False)
                    st.dataframe(past_summary, hide_index=True, use_container_width=True, column_config={"Display Item": "Item Classification", "qty": "Volume"})
                    
                    # --- DAILY EXPORT FUNCTIONALITY ---
                    st.markdown("#### Daily Operations Export")
                    st.caption("Generate formal documentation for daily operations.")
                    
                    daily_metrics = {
                        "Gross Revenue": f"RM {p_total:.2f}",
                        "Cash Expected": f"RM {p_cash:.2f}",
                        "Digital Remittances": f"RM {p_qr:.2f}",
                        "Total Output Volume": str(int(total_cups)),
                        "Inventory Utilized": f"{saved_actual_kg:.3f} kg"
                    }
                    
                    excel_sheets = {
                        "Performance Summary": past_summary,
                        "Raw Ledger": past_df.drop(columns=["Display Item"], errors='ignore')
                    }
                    
                    export_excel = generate_excel(excel_sheets)
                    export_pdf = generate_pdf(past_summary, title="Daily End of Day Report", date_range_str=selected_date_str, metrics=daily_metrics)
                    
                    btn_col1, btn_col2 = st.columns(2)
                    with btn_col1:
                        st.download_button(label="Download Workbook (.xlsx)", data=export_excel, file_name=f"Daily_Log_{selected_date_str}.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
                    with btn_col2:
                        st.download_button(label="Download Document (.pdf)", data=export_pdf, file_name=f"Daily_Report_{selected_date_str}.pdf", mime="application/pdf", use_container_width=True)

            with col_raw:
                st.markdown("#### Raw Transaction Log")
                st.dataframe(past_df.drop(columns=["Display Item"], errors='ignore'), use_container_width=True)

    # ---------------- TAB 3: MENU MANAGER ----------------
    with tab3:
        st.subheader("Database Maintenance")
        st.info("System configuration module. Append entries by utilizing the terminal row at the bottom of the dataset.")
        
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
                "Type (Hot/Cold)": st.column_config.SelectboxColumn("Variant Architecture", options=["Hot", "Cold"], required=True),
                "Price (RM)": st.column_config.NumberColumn("Unit Price (RM)", min_value=0.0, format="%.2f")
            }
        )
        
        if st.button("Apply Database Configuration", type="primary"):
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
            st.success("Database configuration committed successfully.")
            st.rerun()

elif app_mode == "Analytics & Trends":
    
    st.title("Business Analytics Dashboard")
    st.info("Data aggregation and visualization layer. Modifying query parameters will recalculate structural metrics.")
    
    df_all = load_all_historical_sales(menu, settings)
    
    if df_all.empty:
        st.warning("Insufficient data points. Proceed to POS Terminal to append transactional records.")
    else:
        df_all["Date"] = pd.to_datetime(df_all["Date"])
        min_date = df_all["Date"].min().date()
        max_date = df_all["Date"].max().date()
        
        # --- GLOBAL DATE FILTER ---
        st.markdown("### Filtering Criteria")
        
        date_selection = st.date_input(
            "Temporal Range Constraints", 
            value=(min_date, max_date),
            min_value=min_date, 
            max_value=max_date
        )
        
        if isinstance(date_selection, tuple) and len(date_selection) == 2:
            start_date, end_date = date_selection
        elif isinstance(date_selection, tuple) and len(date_selection) == 1:
            start_date = end_date = date_selection[0]
        else:
            start_date = end_date = date_selection
            
        mask = (df_all["Date"].dt.date >= start_date) & (df_all["Date"].dt.date <= end_date)
        df_filtered = df_all.loc[mask]
        
        if df_filtered.empty:
            st.warning("Query returned 0 results for the specified temporal constraints.")
        else:
            st.markdown("### Financial Performance Architecture")
            trend_grouping = st.radio("Temporal Aggregation Node:", ["Daily", "Weekly", "Monthly"], horizontal=True)
            
            if trend_grouping == "Daily":
                trend_df = df_filtered.groupby(df_filtered["Date"].dt.date)["Revenue"].sum().reset_index()
                trend_df["Date"] = pd.to_datetime(trend_df["Date"]).dt.strftime("%b %d, %Y")
            elif trend_grouping == "Weekly":
                trend_df = df_filtered.groupby(df_filtered["Date"].dt.to_period("W"))["Revenue"].sum().reset_index()
                trend_df["Date"] = trend_df["Date"].dt.start_time.dt.strftime("Week of %b %d")
            else: # Monthly
                trend_df = df_filtered.groupby(df_filtered["Date"].dt.to_period("M"))["Revenue"].sum().reset_index()
                trend_df["Date"] = trend_df["Date"].dt.start_time.dt.strftime("%B %Y")
                
            trend_df = trend_df.set_index("Date")
            st.line_chart(trend_df, y="Revenue", color="#0d6efd") 
            
            st.divider()

            st.markdown("### Material Utilization & Inventory Analytics")
            
            day_inventory = df_filtered.drop_duplicates(subset=["Date"]).copy()
            
            if day_inventory["Day Actual Coffee (kg)"].sum() == 0.0:
                st.info("Statistical models will populate as closing inventory weights are recorded in standard operating procedures.")
            else:
                col_inv1, col_inv2 = st.columns(2)
                
                with col_inv1:
                    st.markdown("#### Aggregate Consumption Trajectory")
                    if trend_grouping == "Daily":
                        inv_trend = day_inventory.groupby(day_inventory["Date"].dt.date).agg({"Day Actual Coffee (kg)": "sum"}).reset_index()
                        inv_trend["Date"] = pd.to_datetime(inv_trend["Date"]).dt.strftime("%b %d, %Y")
                    elif trend_grouping == "Weekly":
                        inv_trend = day_inventory.groupby(day_inventory["Date"].dt.to_period("W")).agg({"Day Actual Coffee (kg)": "sum"}).reset_index()
                        inv_trend["Date"] = inv_trend["Date"].dt.start_time.dt.strftime("Week of %b %d")
                    else:
                        inv_trend = day_inventory.groupby(day_inventory["Date"].dt.to_period("M")).agg({"Day Actual Coffee (kg)": "sum"}).reset_index()
                        inv_trend["Date"] = inv_trend["Date"].dt.start_time.dt.strftime("%B %Y")
                        
                    st.line_chart(inv_trend.set_index("Date"), y="Day Actual Coffee (kg)", color="#6c757d") 
                    
                with col_inv2:
                    st.markdown("#### System Baseline vs Physical Variance")
                    if trend_grouping == "Daily":
                        variance_trend = day_inventory.groupby(day_inventory["Date"].dt.date).agg({"Day Expected Coffee (kg)": "sum", "Day Actual Coffee (kg)": "sum"}).reset_index()
                        variance_trend["Date"] = pd.to_datetime(variance_trend["Date"]).dt.strftime("%b %d")
                    elif trend_grouping == "Weekly":
                        variance_trend = day_inventory.groupby(day_inventory["Date"].dt.to_period("W")).agg({"Day Expected Coffee (kg)": "sum", "Day Actual Coffee (kg)": "sum"}).reset_index()
                        variance_trend["Date"] = variance_trend["Date"].dt.start_time.dt.strftime("Wk of %b %d")
                    else:
                        variance_trend = day_inventory.groupby(day_inventory["Date"].dt.to_period("M")).agg({"Day Expected Coffee (kg)": "sum", "Day Actual Coffee (kg)": "sum"}).reset_index()
                        variance_trend["Date"] = variance_trend["Date"].dt.start_time.dt.strftime("%b %Y")
                    
                    melted_var = variance_trend.melt(id_vars=["Date"], value_vars=["Day Expected Coffee (kg)", "Day Actual Coffee (kg)"], var_name="Metric Class", value_name="Mass (kg)")
                    st.bar_chart(melted_var, x="Date", y="Mass (kg)", color="Metric Class", stack=False)

            st.divider()
            
            col_charts1, col_charts2 = st.columns(2)
            
            with col_charts1:
                st.markdown("#### Item Velocity Index (Filtered)")
                top_sellers = df_filtered.groupby("Drink Profile")["Qty"].sum().sort_values(ascending=False).head(10)
                st.bar_chart(top_sellers, horizontal=True, color="#0d6efd") 
                
            with col_charts2:
                st.markdown("#### Output Architecture Segmentation")
                coffee_sales = df_filtered[df_filtered["Drink Base"].str.contains("Kopi", na=False)]
                if not coffee_sales.empty:
                    size_df = coffee_sales.groupby("Drink Type")["Qty"].sum().reset_index()
                    size_df["Categorical Mapping"] = size_df["Drink Type"].map({"Hot": "Primary Volume (Hot)", "Cold": "Secondary Volume (Cold)"}).fillna("Other")
                    st.bar_chart(size_df, x="Categorical Mapping", y="Qty", color="Categorical Mapping")
                else:
                    st.caption("Awaiting data vector inputs for coffee metrics.")
                    
            st.divider()
            
            # --- ADVANCED EXPORT FUNCTIONALITY ---
            st.markdown("#### Data Extraction Protocols")
            st.caption("Generates consolidated business reports based on current filter configurations.")
            filtered_summary = df_filtered.groupby("Drink Profile")["Qty"].sum().reset_index().sort_values(by="Qty", ascending=False)
            
            # Prepare Export Metrics
            rep_rev = df_filtered["Revenue"].sum()
            rep_qr = df_filtered["QR Revenue"].sum()
            rep_cash = rep_rev - rep_qr
            rep_cups = df_filtered["Qty"].sum()
            
            period_metrics = {
                "Aggregate Gross Revenue": f"RM {rep_rev:.2f}",
                "Cash Remittances": f"RM {rep_cash:.2f}",
                "Digital Collections": f"RM {rep_qr:.2f}",
                "Aggregate Output Volume": str(int(rep_cups))
            }
            
            excel_sheets = {
                "Performance Matrix": filtered_summary,
                "Temporal Distribution": trend_df.reset_index(),
                "Raw Transaction Vector": df_filtered[["Date", "Drink Profile", "Qty", "Revenue", "QR Revenue"]]
            }
            
            export_excel = generate_excel(excel_sheets)
            
            date_label = f"{start_date} to {end_date}" if start_date != end_date else str(start_date)
            export_pdf = generate_pdf(filtered_summary, title="Business Performance Analytics", date_range_str=date_label, metrics=period_metrics)
            
            rep_col1, rep_col2, _ = st.columns([1, 1, 2])
            with rep_col1:
                st.download_button(label="Extract Selection to Excel", data=export_excel, file_name="Filtered_Analytics_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
            with rep_col2:
                st.download_button(label="Extract Selection to PDF", data=export_pdf, file_name="Filtered_Analytics_Report.pdf", mime="application/pdf", use_container_width=True)

            st.divider()

            # --- COMPARE PERIODS ---
            st.markdown("#### Period over Period Differential Analysis")
            st.caption("Isolates and contrasts independent temporal nodes. (Overrides global constraints above).")
            comp1, comp2 = st.columns(2)
            
            today = datetime.now().date()
            
            def get_range_data(date_val, df):
                if isinstance(date_val, tuple) and len(date_val) == 2:
                    start_d, end_d = date_val
                elif isinstance(date_val, tuple) and len(date_val) == 1:
                    start_d = end_d = date_val[0]
                else:
                    start_d = end_d = date_val
                
                mask = (df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)
                return df.loc[mask]

            with comp1:
                default_start_a = max(min_date, today - pd.Timedelta(days=7))
                date_a = st.date_input("Node Alpha Configuration", value=(default_start_a, today), min_value=min_date, max_value=max_date, key="comp_a")
                df_a = get_range_data(date_a, df_all)
                
                rev_a = df_a["Revenue"].sum() if not df_a.empty else 0.0
                qr_a = df_a["QR Revenue"].sum() if not df_a.empty else 0.0
                cash_a = rev_a - qr_a
                
                st.metric("Node Alpha Valuation", f"RM {rev_a:.2f}")
                st.metric("Liquid / Digital Distribution", f"RM {cash_a:.2f} / RM {qr_a:.2f}")
                st.metric("Aggregate Output Volume", f"{df_a['Qty'].sum() if not df_a.empty else 0}")

            with comp2:
                default_start_b = max(min_date, default_start_a - pd.Timedelta(days=7))
                default_end_b = max(min_date, default_start_a - pd.Timedelta(days=1))
                date_b = st.date_input("Node Beta Configuration", value=(default_start_b, default_end_b), min_value=min_date, max_value=max_date, key="comp_b")
                df_b = get_range_data(date_b, df_all)
                
                rev_b = df_b["Revenue"].sum() if not df_b.empty else 0.0
                qr_b = df_b["QR Revenue"].sum() if not df_b.empty else 0.0
                cash_b = rev_b - qr_b
                
                delta_rev = rev_b - rev_a if not df_a.empty else None
                
                st.metric(
                    "Node Beta Valuation", 
                    f"RM {rev_b:.2f}", 
                    delta=f"{delta_rev:.2f} RM" if delta_rev is not None else None
                )
                
                st.metric("Liquid / Digital Distribution", f"RM {cash_b:.2f} / RM {qr_b:.2f}")
                st.metric("Aggregate Output Volume", f"{df_b['Qty'].sum() if not df_b.empty else 0}")