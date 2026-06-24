import json
import os
import pandas as pd
from datetime import datetime
from config import MENU_FILE, SETTINGS_FILE, SALES_DIR, DEFAULT_MENU, DEFAULT_SETTINGS, TIN_DRINKS

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

def get_price(menu_dict, drink, drink_type, size="-"):
    if not drink or not drink_type:
        return 0.0
        
    target_type = "Cold" if (drink_type == "Hot" and size == "Big") else drink_type
    temps = menu_dict.get(drink, {}).get("temperature", [])
    
    # Check for requested price mapping first
    for t in temps:
        if t["type"] == target_type:
            return t["price"]
            
    # Fallback to standard price lookup
    for t in temps:
        if t["type"] == drink_type:
            return t["price"]
            
    return 0.0

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
                    size = row.get("size", "-")
                    qty = row.get("qty", 0)
                    if "Kopi" in drink:
                        day_expected_g += (small_g if "Hot" in dtype and size != "Big" else big_g) * qty
                
                day_expected_kg = day_expected_g / 1000.0
                    
                for row in day_data:
                    drink = row.get("drink", "")
                    drink_type = row.get("type", "")
                    if not drink or not drink_type: continue
                    
                    qty = row.get("qty", 0)
                    size = row.get("size", "-")
                    is_tapau = row.get("tapau", False)
                    is_qr = row.get("qr", False)
                    is_kosong = row.get("kosong", False)
                    
                    effective_tapau = is_tapau and not is_tin_drink(drink)
                    base_price = get_price(menu_dict, drink, drink_type, size)
                    extra = 0.20 if effective_tapau else 0.0
                    unit_price = base_price + extra
                    row_revenue = unit_price * qty
                    
                    display_name = f"{drink} - {drink_type}"
                    if drink_type == "Hot" and size in ["Small", "Big"]:
                        display_name += f" ({size})"
                    if is_kosong:
                        display_name += " (Kosong)"
                    
                    item_coffee_g = 0.0
                    if "Kopi" in drink:
                        item_coffee_g = (small_g if "Hot" in drink_type and size != "Big" else big_g) * qty

                    all_records.append({
                        "Date": valid_date,
                        "Drink Base": drink,
                        "Drink Type": drink_type,
                        "Drink Profile": display_name,
                        "Qty": qty,
                        "Base Price": base_price,
                        "Unit Price": unit_price,
                        "Takeaway Fee": extra * qty,
                        "Revenue": row_revenue,
                        "Cash Revenue": 0.0 if is_qr else row_revenue,
                        "QR Revenue": row_revenue if is_qr else 0.0,
                        "Payment Method": "QR" if is_qr else "Cash",
                        "Takeaway": qty if effective_tapau else 0,
                        "Kosong": qty if is_kosong else 0,
                        "Is Takeaway": effective_tapau,
                        "Is Kosong": is_kosong,
                        "Expected Coffee (kg)": item_coffee_g / 1000.0,
                        "Day Actual Coffee (kg)": actual_kg,
                        "Day Expected Coffee (kg)": day_expected_kg
                    })
            except ValueError:
                continue 
                
    return pd.DataFrame(all_records)

# --- Data Cleaning Helpers ---
def is_blank_value(value):
    return value is None or pd.isna(value) or str(value).strip() == ""

def clean_text(value):
    if is_blank_value(value): return ""
    return str(value).strip()

def is_tin_drink(drink):
    return clean_text(drink) in TIN_DRINKS

def parse_qty(value):
    if is_blank_value(value): return 1
    try: return max(int(value), 1)
    except (TypeError, ValueError): return 1

def parse_bool(value):
    if is_blank_value(value): return False
    if isinstance(value, bool): return value
    return str(value).strip().lower() in {"true", "1", "yes", "y"}

def clean_sales_rows(rows):
    clean_rows = []
    for row in rows:
        drink = clean_text(row.get("drink"))
        drink_type = clean_text(row.get("type"))
        if not drink and not drink_type: continue
        clean_rows.append({
            "drink": drink,
            "type": drink_type,
            "size": clean_text(row.get("size", "-")),
            "qty": parse_qty(row.get("qty", 1)),
            "kosong": parse_bool(row.get("kosong", False)),
            "tapau": False if is_tin_drink(drink) else parse_bool(row.get("tapau", False)),
            "qr": parse_bool(row.get("qr", False)),
        })
    return clean_rows