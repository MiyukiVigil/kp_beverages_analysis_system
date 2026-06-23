import pandas as pd
import io
import os
import tempfile
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

from fpdf import FPDF
from datetime import datetime
from openpyxl.utils import get_column_letter


# ==========================================================
# EXCEL EXPORT (SAFE)
# ==========================================================

def generate_excel(sheets_dict):
    output = io.BytesIO()

    if not sheets_dict:
        sheets_dict = {
            "System Status": pd.DataFrame(
                {"Status": ["No data available to export"]}
            )
        }

    with pd.ExcelWriter(output, engine="openpyxl") as writer:

        for sheet_name, df in sheets_dict.items():

            safe_sheet_name = str(sheet_name).replace("/", "_").replace("\\", "_")[:31]

            if df is None or df.empty:
                df = pd.DataFrame({"Status": ["No data available"]})

            df.to_excel(writer, index=False, sheet_name=safe_sheet_name)

            try:
                worksheet = writer.sheets[safe_sheet_name]

                for idx, col in enumerate(df.columns):
                    series = df[col]

                    max_len = max(
                        (
                            series.astype(str).map(len).max()
                            if not series.empty else 0
                        ),
                        len(str(col))
                    ) + 2

                    col_letter = get_column_letter(idx + 1)

                    worksheet.column_dimensions[col_letter].width = min(max_len, 50)

            except Exception:
                pass

    return output.getvalue()


# ==========================================================
# PDF REPORT CLASS (PROFESSIONAL STYLE)
# ==========================================================

class BusinessPDFReport(FPDF):

    def header(self):
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(30, 30, 30)

        self.cell(
            0,
            10,
            "KOPITIAM BUSINESS PERFORMANCE REPORT",
            ln=True,
            align="C"
        )

        self.set_draw_color(200, 200, 200)
        self.line(10, 22, 200, 22)

        self.ln(10)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(120, 120, 120)

        self.cell(
            0,
            10,
            f"Page {self.page_no()}",
            align="C"
        )


# ==========================================================
# KPI BOX
# ==========================================================

def draw_kpi(pdf, label, value):
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_fill_color(245, 245, 245)

    pdf.cell(95, 10, label, border=1, fill=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(95, 10, str(value), border=1, ln=True)


# ==========================================================
# SAFE CHART GENERATOR (FIXED DATE OVERLAP)
# ==========================================================

def create_chart(series, title, chart_type="line"):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".png")

    plt.figure(figsize=(10, 4))

    if series is None or len(series) == 0 or series.sum() == 0:
        plt.text(0.5, 0.5, "No Data Available", ha="center", va="center")
        plt.title(title)
        plt.savefig(temp.name)
        plt.close()
        return temp.name

    series = series.fillna(0)

    # =========================
    # LINE CHART (SMART DATES)
    # =========================
    if chart_type == "line":
        ax = series.plot(kind="line")

        if isinstance(series.index, pd.DatetimeIndex):
            locator = mdates.AutoDateLocator(minticks=4, maxticks=8)
            formatter = mdates.ConciseDateFormatter(locator)

            ax.xaxis.set_major_locator(locator)
            ax.xaxis.set_major_formatter(formatter)
            plt.xticks(rotation=25)

    # =========================
    # BAR CHART
    # =========================
    elif chart_type == "bar":
        series.plot(kind="bar")
        plt.xticks(rotation=35, ha="right")

    # =========================
    # PIE CHART (SAFE)
    # =========================
    elif chart_type == "pie":
        series = series[series > 0]

        if len(series) == 0:
            plt.text(0.5, 0.5, "No Data Available", ha="center", va="center")
        else:
            series.plot(kind="pie", autopct="%1.1f%%")

    plt.title(title, fontsize=12, fontweight="bold")
    plt.tight_layout()
    plt.savefig(temp.name)
    plt.close()

    return temp.name


# ==========================================================
# MAIN PDF GENERATOR
# ==========================================================

def generate_pdf(df, title, date_range_str, metrics=None):

    pdf = BusinessPDFReport()
    chart_files = []

    df = df.copy()

    # =========================
    # SAFE COLUMN HANDLING
    # =========================
    if "Date" not in df.columns:
        df["Date"] = pd.to_datetime(datetime.now())

    if "Revenue" not in df.columns:
        df["Revenue"] = df.get("Qty", 0) * 1.0

    if "QR Revenue" not in df.columns:
        df["QR Revenue"] = 0

    if "Drink Profile" not in df.columns:
        df["Drink Profile"] = "Unknown"

    if "Drink Type" not in df.columns:
        df["Drink Type"] = "Unknown"

    if "Qty" not in df.columns:
        df["Qty"] = 0

    # =========================
    # KPI CALCULATIONS
    # =========================
    revenue = float(df["Revenue"].sum())
    qr_revenue = float(df["QR Revenue"].sum())
    cash_revenue = revenue - qr_revenue
    cups = int(df["Qty"].sum())
    avg = revenue / cups if cups > 0 else 0

    try:
        best_seller = (
            df.groupby("Drink Profile")["Qty"]
            .sum()
            .idxmax()
        )
    except Exception:
        best_seller = "N/A"

    # =========================
    # PAGE 1 - EXECUTIVE SUMMARY
    # =========================

    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True)

    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(90, 90, 90)

    pdf.cell(0, 6, f"Reporting Period: {date_range_str}", ln=True)
    pdf.cell(0, 6, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

    pdf.ln(10)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, "Executive Summary", ln=True)

    pdf.ln(3)

    draw_kpi(pdf, "Total Revenue", f"RM {revenue:,.2f}")
    draw_kpi(pdf, "Cash Revenue", f"RM {cash_revenue:,.2f}")
    draw_kpi(pdf, "QR Revenue", f"RM {qr_revenue:,.2f}")
    draw_kpi(pdf, "Total Cups Sold", cups)
    draw_kpi(pdf, "Avg Per Cup", f"RM {avg:.2f}")
    draw_kpi(pdf, "Best Seller", best_seller)

    # =========================
    # PAGE 2 - DAILY TREND
    # =========================

    if "Revenue" in df.columns:

        daily = df.groupby(df["Date"].dt.date)["Revenue"].sum()

        chart = create_chart(daily, "Daily Revenue Trend", "line")
        chart_files.append(chart)

        pdf.add_page()
        pdf.set_font("Helvetica", "B", 14)
        pdf.cell(0, 10, "Revenue Trend", ln=True)
        pdf.image(chart, x=10, w=180)

    # =========================
    # PAGE 3 - TOP DRINKS
    # =========================

    top = (
        df.groupby("Drink Profile")["Qty"]
        .sum()
        .sort_values(ascending=False)
        .head(10)
    )

    chart = create_chart(top, "Top Selling Drinks", "bar")
    chart_files.append(chart)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Top Selling Drinks", ln=True)
    pdf.image(chart, x=10, w=180)

    # =========================
    # PAGE 4 - PAYMENT BREAKDOWN
    # =========================

    payment = pd.Series({
        "Cash": cash_revenue,
        "QR": qr_revenue
    })

    chart = create_chart(payment, "Payment Breakdown", "pie")
    chart_files.append(chart)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Payment Breakdown", ln=True)
    pdf.image(chart, x=15, w=160)

    # =========================
    # PAGE 5 - HOT VS COLD
    # =========================

    hot_cold = df.groupby("Drink Type")["Qty"].sum()

    chart = create_chart(hot_cold, "Hot vs Cold Drinks", "pie")
    chart_files.append(chart)

    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "Hot vs Cold Drinks", ln=True)
    pdf.image(chart, x=15, w=160)

    # =========================
    # CLEANUP
    # =========================

    result = bytes(pdf.output())

    for f in chart_files:
        try:
            os.remove(f)
        except Exception:
            pass

    return result