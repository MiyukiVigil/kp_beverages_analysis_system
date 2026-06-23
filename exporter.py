import pandas as pd
import io
from fpdf import FPDF
from datetime import datetime

def generate_excel(sheets_dict):
    """
    Converts a dictionary of Pandas DataFrames into a multi-sheet Excel workbook.
    Auto-adjusts column widths for readability.
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        for sheet_name, df in sheets_dict.items():
            # Excel sheet names are capped at 31 characters
            safe_sheet_name = sheet_name[:31]
            
            # Handle empty dataframes gracefully
            if df.empty:
                df = pd.DataFrame({"Status": ["No data available for this period"]})
                
            df.to_excel(writer, index=False, sheet_name=safe_sheet_name)
            
            # Auto-adjust column widths
            worksheet = writer.sheets[safe_sheet_name]
            for idx, col in enumerate(df.columns):
                series = df[col]
                # Calculate the maximum length of the data in the column
                max_len = max((
                    series.astype(str).map(len).max() if not series.empty else 0,
                    len(str(col))
                )) + 2
                # Cap the maximum width to prevent massive columns
                worksheet.column_dimensions[chr(65 + idx)].width = min(max_len, 50)
                
    return output.getvalue()

class BusinessPDFReport(FPDF):
    def header(self):
        self.set_font('helvetica', 'B', 16)
        self.set_text_color(40, 40, 40)
        self.cell(0, 10, 'Kopitiam Business Performance Report', border=0, align='C')
        self.ln(15)

    def footer(self):
        self.set_y(-15)
        self.set_font('helvetica', 'I', 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, f'Page {self.page_no()}', align='C')

def generate_pdf(df, title, date_range_str, metrics=None):
    """
    Generates a professional PDF report with KPI summaries and a formatted data table.
    """
    pdf = BusinessPDFReport()
    pdf.add_page()
    
    # --- Report Metadata ---
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 8, title, ln=True)
    
    pdf.set_font("helvetica", "", 10)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 6, f"Reporting Period: {date_range_str}", ln=True)
    pdf.cell(0, 6, f"Generated On: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)
    pdf.ln(8)
    
    # --- KPI Summary Box ---
    if metrics:
        pdf.set_font("helvetica", "B", 11)
        pdf.set_text_color(0, 0, 0)
        pdf.set_fill_color(240, 240, 245)
        pdf.cell(0, 8, " Key Performance Indicators", border=1, ln=True, fill=True)
        
        pdf.set_font("helvetica", "", 10)
        for key, value in metrics.items():
            pdf.cell(70, 8, f"  {key}:", border=1)
            pdf.cell(0, 8, f"  {value}", border=1, ln=True)
        pdf.ln(10)
        
    # --- Data Table Setup ---
    pdf.set_font("helvetica", "B", 10)
    pdf.set_fill_color(220, 220, 220)
    
    num_cols = len(df.columns)
    if num_cols == 0:
        pdf.cell(0, 10, "No data available.", align='C')
        return bytes(pdf.output())
        
    # Dynamically distribute column widths
    col_width = pdf.epw / num_cols
    line_height = 8
    
    # Table Header Row
    for col in df.columns:
        pdf.cell(col_width, line_height, str(col)[:25], border=1, align='C', fill=True)
    pdf.ln(line_height)
    
    # Table Data Rows
    pdf.set_font("helvetica", "", 9)
    fill = False
    for _, row in df.iterrows():
        # Handle page breaks cleanly
        if pdf.get_y() > 260:
            pdf.add_page()
            pdf.set_font("helvetica", "B", 10)
            for col in df.columns:
                pdf.cell(col_width, line_height, str(col)[:25], border=1, align='C', fill=True)
            pdf.ln(line_height)
            pdf.set_font("helvetica", "", 9)
            
        pdf.set_fill_color(248, 248, 248)
        for item in row:
            # Format numbers properly
            if isinstance(item, float):
                val = f"{item:.2f}"
            else:
                val = str(item)
            pdf.cell(col_width, line_height, val[:35], border=1, align='C', fill=fill)
        pdf.ln(line_height)
        fill = not fill # Toggle row background color

    return bytes(pdf.output())