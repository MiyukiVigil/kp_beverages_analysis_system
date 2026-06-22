import streamlit as st
import json
import os
import pandas as pd
from datetime import datetime

MENU_FILE = "menu.json"
SALES_FILE = "sales.json"


# ---------------- LOAD / SAVE ----------------

def load_json(file, default):
    if os.path.exists(file):
        with open(file, "r") as f:
            return json.load(f)
    return default


def save_json(file, data):
    with open(file, "w") as f:
        json.dump(data, f, indent=4)


menu = load_json(MENU_FILE, {})
sales_data = load_json(SALES_FILE, {})

today = str(datetime.now().date())

if today not in sales_data:
    sales_data[today] = []


# ---------------- HELPERS ----------------

def get_drinks():
    return list(menu.keys())


def get_variants(drink):
    return list(menu.get(drink, {}).keys())


def get_price(drink, variant):
    return menu.get(drink, {}).get(variant, 0.0)


# ---------------- INIT TABLE ----------------

if "df" not in st.session_state:
    st.session_state.df = pd.DataFrame([{
        "drink": get_drinks()[0] if menu else "",
        "variant": get_variants(get_drinks()[0])[0] if menu else "",
        "qty": 1,
        "takeaway": False,
        "qr": False
    }])


# ---------------- UI ----------------

st.title("☕ Café POS - Excel Style Table")

st.subheader(f"🧾 Order Entry ({today})")


# --- TABLE EDITOR (REAL GRID INPUT) ---
edited_df = st.data_editor(
    st.session_state.df,
    num_rows="dynamic",
    use_container_width=True,
    column_config={
        "drink": st.column_config.SelectboxColumn(
            "Drink",
            options=get_drinks()
        ),
        "variant": st.column_config.TextColumn("Variant"),
        "qty": st.column_config.NumberColumn("Qty", min_value=1, step=1),
        "takeaway": st.column_config.CheckboxColumn("Takeaway (+0.20)"),
        "qr": st.column_config.CheckboxColumn("QR Payment")
    }
)


st.session_state.df = edited_df


# ---------------- ADD ROW ----------------

col1, col2 = st.columns(2)

with col1:
    if st.button("➕ Add Row"):
        st.session_state.df = pd.concat([
            st.session_state.df,
            pd.DataFrame([{
                "drink": get_drinks()[0] if menu else "",
                "variant": get_variants(get_drinks()[0])[0] if menu else "",
                "qty": 1,
                "takeaway": False,
                "qr": False
            }])
        ], ignore_index=True)
        st.rerun()


# ---------------- SAVE ----------------

with col2:
    if st.button("💾 Save Order"):

        total = 0
        saved = []

        for _, row in st.session_state.df.iterrows():

            drink = row["drink"]
            variant = row["variant"]
            qty = int(row["qty"])

            price = get_price(drink, variant)

            extra = 0.20 if row["takeaway"] else 0
            unit = price + extra

            line_total = unit * qty
            total += line_total

            saved.append({
                "time": datetime.now().strftime("%H:%M:%S"),
                "drink": drink,
                "variant": variant,
                "qty": qty,
                "takeaway": bool(row["takeaway"]),
                "qr": bool(row["qr"]),
                "unit_price": unit,
                "total": line_total
            })

        sales_data[today].extend(saved)
        save_json(SALES_FILE, sales_data)

        st.success(f"Saved! Total RM {total:.2f}")

        # reset table
        st.session_state.df = pd.DataFrame([{
            "drink": get_drinks()[0] if menu else "",
            "variant": get_variants(get_drinks()[0])[0] if menu else "",
            "qty": 1,
            "takeaway": False,
            "qr": False
        }])


# ---------------- SUMMARY ----------------

st.divider()
st.subheader("📊 Daily Summary")

today_sales = sales_data.get(today, [])

if today_sales:
    df = pd.DataFrame(today_sales)

    summary = df.groupby(["drink", "variant"])["qty"].sum().reset_index()
    summary["item"] = summary["drink"] + " " + summary["variant"]

    st.table(summary[["item", "qty"]])

    total_sales = df["total"].sum()
    cash_sales = df[df["qr"] == False]["total"].sum()

    col1, col2 = st.columns(2)
    col1.metric("Total Sales", f"RM {total_sales:.2f}")
    col2.metric("Cash Only", f"RM {cash_sales:.2f}")

    st.dataframe(df, use_container_width=True)
else:
    st.info("No sales yet today.")