import streamlit as st
import pandas as pd
from datetime import datetime
from utils import load_all_historical_sales, load_menu
from exporter import generate_excel, generate_pdf

def render_analytics_dashboard(settings):
    menu = load_menu()
    st.title("Sales Analysis Reports")
    st.info("Choose dates below to see sales and coffee usage.")
    
    df_all = load_all_historical_sales(menu, settings)
    
    if df_all.empty:
        st.warning("Insufficient data points. Proceed to POS Terminal to append transactional records.")
        return

    df_all["Date"] = pd.to_datetime(df_all["Date"])
    min_date = df_all["Date"].min().date()
    max_date = df_all["Date"].max().date()
    
    st.markdown("### Date Filter")
    date_selection = st.date_input("Date Range", value=(min_date, max_date), min_value=min_date, max_value=max_date)
    
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
        return

    st.markdown("### Sales Over Time")
    trend_grouping = st.radio("Group By:", ["Daily", "Weekly", "Monthly"], horizontal=True)
    
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

    st.markdown("### Coffee Powder Usage")
    day_inventory = df_filtered.drop_duplicates(subset=["Date"]).copy()
    
    if day_inventory["Day Actual Coffee (kg)"].sum() == 0.0:
        st.info("Statistical models will populate as closing inventory weights are recorded in standard operating procedures.")
    else:
        col_inv1, col_inv2 = st.columns(2)
        with col_inv1:
            st.markdown("#### Coffee Powder Used Over Time")
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
            st.markdown("#### Expected vs Actual Coffee Powder Used")
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
        st.markdown("#### Best-Selling Drinks (Filtered)")
        top_sellers = df_filtered.groupby("Drink Profile")["Qty"].sum().sort_values(ascending=False).head(10)
        st.bar_chart(top_sellers, horizontal=True, color="#0d6efd") 
        
    with col_charts2:
        st.markdown("#### Hot vs Cold Coffee Sales")
        coffee_sales = df_filtered[df_filtered["Drink Base"].str.contains("Kopi", na=False)]
        if not coffee_sales.empty:
            size_df = coffee_sales.groupby("Drink Type")["Qty"].sum().reset_index()
            size_df["Categorical Mapping"] = size_df["Drink Type"].map({"Hot": "Primary Volume (Hot)", "Cold": "Secondary Volume (Cold)"}).fillna("Other")
            st.bar_chart(size_df, x="Categorical Mapping", y="Qty", color="Categorical Mapping")
        else:
            st.caption("Awaiting data vector inputs for coffee metrics.")
            
    st.divider()
    st.markdown("#### Download Reports")
    st.caption("Generates consolidated business reports based on current filter configurations.")
    filtered_summary = df_filtered.groupby("Drink Profile")["Qty"].sum().reset_index().sort_values(by="Qty", ascending=False)
    
    rep_rev, rep_qr = df_filtered["Revenue"].sum(), df_filtered["QR Revenue"].sum()
    rep_cash, rep_cups = rep_rev - rep_qr, df_filtered["Qty"].sum()
    
    period_metrics = {
        "Aggregate Gross Revenue": f"RM {rep_rev:.2f}", "Cash Remittances": f"RM {rep_cash:.2f}",
        "Digital Collections (Cashless QR)": f"RM {rep_qr:.2f}", "Aggregate Output Volume": str(int(rep_cups))
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
    with rep_col1: st.download_button(label="Extract Selection to Excel", data=export_excel, file_name="Filtered_Analytics_Report.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)
    with rep_col2: st.download_button(label="Extract Selection to PDF", data=export_pdf, file_name="Filtered_Analytics_Report.pdf", mime="application/pdf", use_container_width=True)

    st.divider()
    st.markdown("#### Comparison Between Two Date Ranges")
    comp1, comp2 = st.columns(2)
    today = datetime.now().date()
    
    def get_range_data(date_val, df):
        if isinstance(date_val, tuple) and len(date_val) == 2: start_d, end_d = date_val
        elif isinstance(date_val, tuple) and len(date_val) == 1: start_d = end_d = date_val[0]
        else: start_d = end_d = date_val
        return df.loc[(df["Date"].dt.date >= start_d) & (df["Date"].dt.date <= end_d)]

    with comp1:
        default_start_a = max(min_date, today - pd.Timedelta(days=7))
        date_a = st.date_input("First Date Range", value=(default_start_a, today), min_value=min_date, max_value=max_date, key="comp_a")
        df_a = get_range_data(date_a, df_all)
        rev_a, qr_a = df_a["Revenue"].sum() if not df_a.empty else 0.0, df_a["QR Revenue"].sum() if not df_a.empty else 0.0
        cash_a = rev_a - qr_a
        st.metric("First Period Sales", f"RM {rev_a:.2f}")
        st.metric("Cash / QR Payments", f"RM {cash_a:.2f} / RM {qr_a:.2f}")
        st.metric("Total Cups Sold", f"{df_a['Qty'].sum() if not df_a.empty else 0}")

    with comp2:
        default_start_b = max(min_date, default_start_a - pd.Timedelta(days=7))
        default_end_b = max(min_date, default_start_a - pd.Timedelta(days=1))
        date_b = st.date_input("Second Date Range", value=(default_start_b, default_end_b), min_value=min_date, max_value=max_date, key="comp_b")
        df_b = get_range_data(date_b, df_all)
        rev_b, qr_b = df_b["Revenue"].sum() if not df_b.empty else 0.0, df_b["QR Revenue"].sum() if not df_b.empty else 0.0
        cash_b = rev_b - qr_b
        delta_rev = rev_b - rev_a if not df_a.empty else None
        st.metric("Second Period Sales", f"RM {rev_b:.2f}", delta=f"{delta_rev:.2f} RM" if delta_rev is not None else None)
        st.metric("Cash / QR Payments", f"RM {cash_b:.2f} / RM {qr_b:.2f}")
        st.metric("Total Cups Sold", f"{df_b['Qty'].sum() if not df_b.empty else 0}")