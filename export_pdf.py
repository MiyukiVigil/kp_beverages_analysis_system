from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors

def export_pdf(data, path):
    doc = SimpleDocTemplate(path)

    table = [["Name", "Price"]]

    for d in data:
        table.append([
            d["name"],
            d["price"] if d["price"] is not None else ""
        ])

    t = Table(table)

    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.grey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("GRID", (0,0), (-1,-1), 0.5, colors.black),
        ("PADDING", (0,0), (-1,-1), 6),
    ]))

    doc.build([t])