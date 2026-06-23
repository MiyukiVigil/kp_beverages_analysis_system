import streamlit as st
import pandas as pd
from utils import (load_menu, save_menu, load_sales, save_sales, get_price, 
                   clean_sales_rows, clean_text, is_tin_drink)
from exporter import generate_excel, generate_pdf

def render_pos_terminal(selected_date_str, settings):
    menu = load_menu()
    DRINK_OPTIONS = list(menu.keys())
    TYPE_OPTIONS = sorted({
        temp["type"] for drink_data in menu.values() 
        for temp in drink_data.get("temperature", []) if temp.get("type")
    })

    if "current_date" not in st.session_state or st.session_state.current_date != selected_date_str:
        st.session_state.current_date = selected_date_str
        sales_data = load_sales(selected_date_str)
        st.session_state.day_transactions = sales_data["transactions"]
        st.session_state.actual_kg = sales_data["actual_kg"]

    st.title("Sales Log Terminal")
    tab1, tab2 = st.tabs(["Transaction Entry", "Daily Reconciliation"])

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
                    is_tapau = st.checkbox("Takeaway", disabled=tapau_disabled)
                with mod3:
                    is_qr = st.checkbox("QR/Digital Payment")
            with action_col:
                st.markdown("&nbsp;", unsafe_allow_html=True)
                if st.button("Append to Ledger", type="primary", use_container_width=True):
                    st.session_state.day_transactions.append({
                        "drink": selected_drink, "type": selected_type, "qty": add_qty,
                        "kosong": is_kosong, "tapau": is_tapau, "qr": is_qr
                    })
                    st.rerun()

        st.subheader(f"Ledger Overview: {selected_date_str}")
        with st.container(border=True):
            invalid_rows = []

            if not st.session_state.day_transactions:
                st.info(f"The transaction ledger for {selected_date_str} is currently empty.")
                edited_data = []
                day_total = cash_total = qr_total = 0.0
            else:
                df_log = pd.DataFrame(st.session_state.day_transactions)
                for column, default in {"drink": "", "type": "", "qty": 1, "kosong": False, "tapau": False, "qr": False}.items():
                    if column not in df_log.columns: df_log[column] = default

                df_log = df_log[["drink", "type", "qty", "kosong", "tapau", "qr"]]
                drink_opts = sorted({*DRINK_OPTIONS, *[clean_text(v) for v in df_log["drink"] if clean_text(v)]})
                type_opts = sorted({*TYPE_OPTIONS, *[clean_text(v) for v in df_log["type"] if clean_text(v)]})
                
                edited_df = st.data_editor(
                    df_log, num_rows="dynamic", use_container_width=True,
                    column_config={
                        "drink": st.column_config.SelectboxColumn("Beverage", options=drink_opts, required=True),
                        "type": st.column_config.SelectboxColumn("Variant", options=type_opts, required=True),
                        "qty": st.column_config.NumberColumn("Volume", min_value=1, step=1),
                        "kosong": "Kosong", "tapau": "Takeaway (+0.20)", "qr": "Digital Payment"
                    }
                )
                
                edited_data = clean_sales_rows(edited_df.to_dict('records'))
                st.session_state.day_transactions = edited_data
                
                day_total = qr_total = 0.0
                invalid_rows = []
                
                for item in edited_data:
                    if not item.get("drink") or not item.get("type"): continue
                    
                    base_price = get_price(menu, item["drink"], item["type"])
                    if base_price == 0.0:
                        invalid_rows.append(f"{item['drink']} - {item['type']}")
                        continue

                    extra = 0.20 if item.get("tapau") and not is_tin_drink(item.get("drink")) else 0.0
                    row_val = (base_price + extra) * item.get("qty", 1)
                    
                    day_total += row_val
                    if item.get("qr"): qr_total += row_val
                        
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
            input_actual_kg = st.number_input("Physical Coffee Grounds Utilized (kg)", min_value=0.0, step=0.100, format="%.3f", value=float(st.session_state.actual_kg))

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
            p_total = p_qr = p_takeaway = expected_coffee_used_g = 0.0 
            
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
            
            with inv_col1: st.metric("System Expected Usage", f"{expected_kg:.3f} kg")
            with inv_col2: st.metric("Physical Record", f"{saved_actual_kg:.3f} kg")
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
                        lambda x: f"{x['drink']} - {x['type']} (Kosong)" if x.get("kosong", False) else f"{x['drink']} - {x['type']}", axis=1)
                    past_summary = past_df.groupby("Display Item")["qty"].sum().reset_index().sort_values(by="qty", ascending=False)
                    st.dataframe(past_summary, hide_index=True, use_container_width=True, column_config={"Display Item": "Item Classification", "qty": "Volume"})
                    
                    st.markdown("#### Daily Operations Export")
                    daily_metrics = {
                        "Gross Revenue": f"RM {p_total:.2f}", "Cash Expected": f"RM {p_cash:.2f}",
                        "Digital Remittances": f"RM {p_qr:.2f}", "Total Output Volume": str(int(total_cups)),
                        "Inventory Utilized": f"{saved_actual_kg:.3f} kg"
                    }
                    excel_sheets = {"Performance Summary": past_summary, "Raw Ledger": past_df.drop(columns=["Display Item"], errors='ignore')}
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