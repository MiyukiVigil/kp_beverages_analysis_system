import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

# ================= CONFIG & FILE SETUP =================
st.set_page_config(page_title="Kopitiam Daily Sales Log", layout="wide", initial_sidebar_state="expanded")

st.markdown(
    """
    <style>
    html, body, [class*="css"] {
        font-size: 17px;
    }

    .block-container {
        max-width: 1480px;
        padding-top: 1.25rem;
        padding-bottom: 1.5rem;
    }

    h1 {
        font-size: 2.45rem !important;
        line-height: 1.15 !important;
        margin: 0.25rem 0 0.9rem !important;
    }

    h2, h3 {
        line-height: 1.2 !important;
        margin: 0.45rem 0 0.35rem !important;
    }

    p, label, [data-testid="stWidgetLabel"],
    [data-testid="stMarkdownContainer"] {
        font-size: 1.04rem;
    }

    [data-testid="stVerticalBlock"] {
        gap: 0.65rem;
    }

    [data-testid="stHorizontalBlock"] {
        gap: 0.9rem;
    }

    [data-testid="stTabs"] [data-baseweb="tab-list"] {
        gap: 0.8rem;
    }

    [data-testid="stTabs"] [data-baseweb="tab-panel"] {
        padding-top: 0.85rem;
    }

    [data-testid="stVerticalBlockBorderWrapper"] {
        margin-top: 0.25rem;
    }

    div[data-testid="stMetric"] {
        padding: 0.55rem 0.75rem;
    }

    [data-testid="stMetricLabel"] p {
        font-size: 1rem;
    }

    [data-testid="stMetricValue"] {
        font-size: 1.75rem;
    }

    div[data-testid="stDataFrame"] {
        margin-top: 0.25rem;
    }

    button {
        font-size: 1.02rem !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

MENU_FILE = "menu.json"
SALES_DIR = "sales"

if not os.path.exists(SALES_DIR):
    os.makedirs(SALES_DIR)

DEFAULT_MENU = {
  "Kopi": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] },
  "Kopi O": { "temperature": [ { "type": "Hot", "price": 2.00 }, { "type": "Cold", "price": 2.30 } ] },
  "Teh": { "temperature": [ { "type": "Hot", "price": 2.50 }, { "type": "Cold", "price": 2.80 } ] }
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
    with open(get_sales_file(date_str), "w") as f:
        json.dump(data, f, indent=4)

def load_all_historical_sales(menu_dict):
    """Loads all JSON files in the sales directory and calculates revenue for analytics."""
    all_records = []
    if not os.path.exists(SALES_DIR): return pd.DataFrame()
    
    for filename in os.listdir(SALES_DIR):
        if filename.endswith(".json"):
            date_str = filename.replace(".json", "")
            try:
                # Validate date format
                valid_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                file_path = os.path.join(SALES_DIR, filename)
                with open(file_path, "r") as f:
                    day_data = json.load(f)
                    
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
                    
                    all_records.append({
                        "Date": valid_date,
                        "Drink Profile": display_name,
                        "Qty": qty,
                        "Revenue": row_revenue,
                        "QR Revenue": row_revenue if is_qr else 0.0,
                        "Takeaway": qty if is_tapau else 0
                    })
            except ValueError:
                continue # Skip files that aren't named as YYYY-MM-DD
                
    return pd.DataFrame(all_records)

menu = load_menu()
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
    st.header("🧭 Navigation")
    app_mode = st.radio("Go to:", ["POS Terminal", "Analytics & Trends"])
    
    st.divider()
    
    today = datetime.now().date()
    
    # Only show the date picker and tips if we are actually in the POS terminal
    if app_mode == "POS Terminal":
        st.header("⚙️ Settings")
        
        # Block future dates by setting max_value to today's date
        selected_date = st.date_input("Working Date", value=today, max_value=today)
        selected_date_str = str(selected_date)
        
        st.caption(f"Transactions are logged under: **{selected_date_str}**")
        
        st.divider()
        st.markdown("### 💡 Tips")
        st.info("To delete an item from the log, click the empty space on the far left of the row and press **Delete/Backspace** on your keyboard.")

# ================= APP ROUTING =================

if app_mode == "POS Terminal":
    
    # --- SESSION STATE (LIVE DAY LOG) ---
    if "current_date" not in st.session_state or st.session_state.current_date != selected_date_str:
        st.session_state.current_date = selected_date_str
        st.session_state.day_data = load_sales(selected_date_str)

    st.title("Kopitiam Daily Sales Log")
    tab1, tab2, tab3 = st.tabs(["Register (Add & Edit)", "Daily Report", "Menu Manager"])

    # ---------------- TAB 1: REGISTER ----------------
    with tab1:
        
        # --- TOP SECTION: ADD ITEM TERMINAL ---
        st.subheader("Add Drink")
        with st.container(border=True):
            col1, col2, col3 = st.columns([2.1, 1.6, 1], gap="medium")
            
            with col1:
                selected_drink = st.selectbox("Select Drink", DRINK_OPTIONS, key="add_drink")
            with col2:
                # Dynamically get valid types (Hot/Cold) for the selected drink
                valid_types = [t["type"] for t in menu.get(selected_drink, {}).get("temperature", [])]
                selected_type = st.radio("Temperature", valid_types, horizontal=True)
            with col3:
                add_qty = st.number_input("Quantity", min_value=1, step=1)
                
            modifier_col, action_col = st.columns([1.6, 1], gap="medium")
            with modifier_col:
                st.markdown("**Modifiers**")
                mod1, mod2, mod3 = st.columns(3, gap="small")
                with mod1:
                    is_kosong = st.checkbox("Kosong")
                with mod2:
                    tapau_disabled = is_tin_drink(selected_drink)
                    is_tapau = st.checkbox(
                        "Tapau",
                        disabled=tapau_disabled,
                        help="Tin drinks cannot be marked as Tapau." if tapau_disabled else None,
                    )
                    if tapau_disabled:
                        is_tapau = False
                with mod3:
                    is_qr = st.checkbox("QR Paid")
            with action_col:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("➕ Add to Day's Log", type="primary", use_container_width=True):
                    st.session_state.day_data.append({
                        "drink": selected_drink,
                        "type": selected_type,
                        "qty": add_qty,
                        "kosong": is_kosong,
                        "tapau": is_tapau,
                        "qr": is_qr
                    })
                    # We do not auto-save here, giving you a chance to edit below first
                    st.rerun()

        # --- BOTTOM SECTION: THE DAY'S LOG ---
        st.subheader(f"Log for {selected_date_str}")
        st.caption("Edit quantities, check/uncheck boxes, or delete rows directly below. **Make sure to hit Save when done**")
        
        with st.container(border=True):
            invalid_rows = []

            if not st.session_state.day_data:
                st.info(f"No records yet for {selected_date_str}. Add an item above to start.")
                edited_data = []
                day_total = 0.0
                cash_total = 0.0
                qr_total = 0.0
            else:
                df_log = pd.DataFrame(st.session_state.day_data)
                expected_columns = ["drink", "type", "qty", "kosong", "tapau", "qr"]
                defaults = {
                    "drink": "",
                    "type": "",
                    "qty": 1,
                    "kosong": False,
                    "tapau": False,
                    "qr": False,
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
                
                # Interactive grid for the entire day's log
                edited_df = st.data_editor(
                    df_log,
                    num_rows="dynamic", 
                    use_container_width=True,
                    column_config={
                        "drink": st.column_config.SelectboxColumn(
                            "Drink",
                            options=drink_options_for_editor,
                            required=True,
                        ),
                        "type": st.column_config.SelectboxColumn(
                            "Type",
                            options=type_options_for_editor,
                            required=True,
                        ),
                        "qty": st.column_config.NumberColumn("Qty", min_value=1, step=1),
                        "kosong": "Kosong",
                        "tapau": "Tapau (+0.20)",
                        "qr": "QR"
                    }
                )
                
                # Sync the grid edits back to session state so we don't lose them
                edited_data = clean_sales_rows(edited_df.to_dict('records'))
                st.session_state.day_data = edited_data
                
                # Live Math Calculation
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
                    st.warning(
                        "Some edited rows do not match a price in the menu: "
                        + ", ".join(invalid_rows)
                        + ". Change the drink/type or update the Menu Manager before saving."
                    )
                
            # Display live metrics
            st.divider()
            m1, m2, m3 = st.columns(3)
            m1.metric("Total Generated", f"RM {day_total:.2f}")
            m2.metric("Cash", f"RM {cash_total:.2f}")
            m3.metric("QR Total", f"RM {qr_total:.2f}")
            
            # Explicit Save Button
            if st.button("Save Full Day's Log", type="primary", use_container_width=True, disabled=len(st.session_state.day_data) == 0 or bool(invalid_rows)):
                # Clean out any empty rows before saving
                valid_items = [
                    item for item in clean_sales_rows(edited_data)
                    if item.get("drink") and item.get("type")
                ]
                save_sales(selected_date_str, valid_items)
                st.success(f"✅ Log successfully saved to {selected_date_str}!")

    # ---------------- TAB 2: DAILY REPORT ----------------
    with tab2:
        st.subheader(f"Sales Summary for {selected_date_str}")
        st.info("This report shows the saved data. If you recently made changes in the Register tab, ensure you clicked 'Save Full Day's Log'.")
        
        past_data = load_sales(selected_date_str)
        
        if not past_data:
            st.warning("No saved sales recorded for this date yet.")
        else:
            past_df = pd.DataFrame(past_data)
            
            p_total = 0.0
            p_qr = 0.0
            p_takeaway = 0
            
            for _, row in past_df.iterrows():
                if "item" in row and "drink" not in row:
                    st.error("Old data format detected. Reports require the new format.")
                    break

                base_price = get_price(menu, row.get("drink", ""), row.get("type", ""))
                extra = 0.20 if row.get("tapau", False) and not is_tin_drink(row.get("drink", "")) else 0.0
                rt = (base_price + extra) * row.get("qty", 0)
                
                p_total += rt
                if row.get("qr", False): p_qr += rt
                if row.get("tapau", False) and not is_tin_drink(row.get("drink", "")): p_takeaway += row.get("qty", 0)
                    
            p_cash = p_total - p_qr
            
            # Metric Cards
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total Revenue", f"RM {p_total:.2f}")
            m2.metric("Cash Balance", f"RM {p_cash:.2f}")
            m3.metric("QR Revenue", f"RM {p_qr:.2f}")
            m4.metric("Takeaway Cups", f"{p_takeaway}")
            
            st.divider()
            col_summary, col_raw = st.columns([1, 1])
            
            with col_summary:
                st.markdown("#### Popular Items Today")
                if "drink" in past_df.columns and "type" in past_df.columns:
                    past_df["Display Item"] = past_df.apply(
                        lambda x: f"{x['drink']} - {x['type']} (Kosong)" if x.get("kosong", False) else f"{x['drink']} - {x['type']}", 
                        axis=1
                    )
                    past_summary = past_df.groupby("Display Item")["qty"].sum().reset_index().sort_values(by="qty", ascending=False)
                    st.dataframe(past_summary, hide_index=True, use_container_width=True, column_config={"Display Item": "Drink Profile", "qty": "Qty Sold"})

            with col_raw:
                st.markdown("#### Raw Transaction Log")
                st.dataframe(past_df.drop(columns=["Display Item"], errors='ignore'), use_container_width=True)

    # ---------------- TAB 3: MENU MANAGER ----------------
    with tab3:
        st.subheader("Menu Database Manager")
        st.info("Add new drinks or edit prices. To add a new item, scroll to the bottom of the table and type in the empty row.")
        
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
        
        if st.button("💾 Save Menu Changes", type="primary"):
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
            st.success("Menu updated successfully! Changes are live in the console.")
            st.rerun()

elif app_mode == "Analytics & Trends":
    
    st.title("📈 Business Analytics & Trends")
    st.info("This dashboard analyzes all historical saved data across all dates.")
    
    # Load massive dataset encompassing all history
    df_all = load_all_historical_sales(menu)
    
    if df_all.empty:
        st.warning("Not enough data to display analytics. Save a few daily logs first!")
    else:
        # Convert Date column to actual datetime objects for Pandas processing
        df_all["Date"] = pd.to_datetime(df_all["Date"])
        
        # --- SECTION 1: TREND GRAPH ---
        st.markdown("#### 📈 Revenue Trends")
        
        trend_grouping = st.radio("Group Data By:", ["Weekly", "Monthly"], horizontal=True)
        
        # Aggregate data based on selection and format date strings beautifully
        if trend_grouping == "Weekly":
            trend_df = df_all.groupby(df_all["Date"].dt.to_period("W"))["Revenue"].sum().reset_index()
            # Formats week to e.g., "Week of Jun 15" instead of "2026-06-15/2026-06-21"
            trend_df["Date"] = trend_df["Date"].dt.start_time.dt.strftime("Week of %b %d")
        else: # Monthly
            trend_df = df_all.groupby(df_all["Date"].dt.to_period("M"))["Revenue"].sum().reset_index()
            # Formats month to e.g., "June 2026"
            trend_df["Date"] = trend_df["Date"].dt.start_time.dt.strftime("%B %Y")
            
        trend_df = trend_df.set_index("Date")
        
        # Adding a custom color to the line chart
        st.line_chart(trend_df, y="Revenue", color="#009688") # Teal accent color
        
        st.divider()
        
        col_charts1, col_charts2 = st.columns(2)
        
        with col_charts1:
            # --- SECTION 2: TOP SELLERS ---
            st.markdown("#### 🏆 All-Time Top Sellers")
            top_sellers = df_all.groupby("Drink Profile")["Qty"].sum().sort_values(ascending=False).head(10)
            st.bar_chart(top_sellers, horizontal=True, color="#FF9800") # Orange accent color
            
        with col_charts2:
            # --- SECTION 3: REVENUE BREAKDOWN ---
            st.markdown("#### 💰 Lifetime Revenue Split")
            lifetime_rev = df_all["Revenue"].sum()
            lifetime_qr = df_all["QR Revenue"].sum()
            lifetime_cash = lifetime_rev - lifetime_qr
            
            # Map the color directly to the Payment Method category
            split_df = pd.DataFrame({
                "Payment Method": ["Cash", "QR"],
                "Amount": [lifetime_cash, lifetime_qr]
            })
            
            st.bar_chart(split_df, x="Payment Method", y="Amount", color="Payment Method")

        st.divider()

        # --- SECTION 4: DAY-TO-DAY COMPARISON ---
        st.markdown("#### ⚖️ Compare Specific Dates")
        comp1, comp2 = st.columns(2)
        
        today = datetime.now().date()
        
        with comp1:
            date_a = st.date_input("Select Date A", value=today - pd.Timedelta(days=1), max_value=today)
            df_a = df_all[df_all["Date"].dt.date == date_a]
            
            rev_a = df_a["Revenue"].sum() if not df_a.empty else 0.0
            qr_a = df_a["QR Revenue"].sum() if not df_a.empty else 0.0
            cash_a = rev_a - qr_a
            
            st.metric("Total Revenue (Date A)", f"RM {rev_a:.2f}")
            st.metric("Cash / QR Split", f"RM {cash_a:.2f} / RM {qr_a:.2f}")
            st.metric("Total Cups Sold", f"{df_a['Qty'].sum() if not df_a.empty else 0}")

        with comp2:
            date_b = st.date_input("Select Date B", value=today, max_value=today)
            df_b = df_all[df_all["Date"].dt.date == date_b]
            
            rev_b = df_b["Revenue"].sum() if not df_b.empty else 0.0
            qr_b = df_b["QR Revenue"].sum() if not df_b.empty else 0.0
            cash_b = rev_b - qr_b
            
            # Calculate difference vs Date A for the primary metric
            delta_rev = rev_b - rev_a if not df_a.empty else None
            
            st.metric(
                "Total Revenue (Date B)", 
                f"RM {rev_b:.2f}", 
                delta=f"{delta_rev:.2f} RM" if delta_rev is not None else None
            )
            
            st.metric("Cash / QR Split", f"RM {cash_b:.2f} / RM {qr_b:.2f}")
            st.metric("Total Cups Sold", f"{df_b['Qty'].sum() if not df_b.empty else 0}")