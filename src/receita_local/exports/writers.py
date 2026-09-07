from __future__ import annotations

import io
from typing import Any

import pandas as pd
from openpyxl.styles import Font
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, TableStyle


def _safe(value: Any) -> Any:
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return "PENDENTE" if value is None else value


def excel_bytes(result: dict, metadata: dict) -> bytes:
    stream = io.BytesIO()
    sheets = {
        "Receita": result.get("items", []),
        "Condições e regras": [{"texto": x} for x in result.get("assumptions", [])],
        "Evidências": [{"texto": x} for x in result.get("evidence", [])],
        "Qualidade": result.get("quality", []),
        "Pendências": [{"texto": x} for x in result.get("pending", [])],
        "Metadados da análise": [{"campo": k, "valor": v} for k, v in metadata.items()],
    }
    with pd.ExcelWriter(stream, engine="openpyxl") as writer:
        for name, rows in sheets.items():
            safe = [{k: _safe(v) for k, v in row.items()} for row in rows] or [{"informacao": "SEM REGISTROS"}]
            pd.DataFrame(safe).to_excel(writer, sheet_name=name[:31], index=False)
            ws = writer.book[name[:31]]; ws.freeze_panes = "A2"; ws.auto_filter.ref = ws.dimensions
            for cell in ws[1]: cell.font = Font(bold=True)
            for col in ws.columns: ws.column_dimensions[col[0].column_letter].width = min(45, max(12, max(len(str(c.value or "")) for c in col) + 2))
    return stream.getvalue()


def pdf_bytes(result: dict, metadata: dict) -> bytes:
    stream, styles = io.BytesIO(), getSampleStyleSheet()
    doc = SimpleDocTemplate(stream, pagesize=landscape(A4), leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    story = [Paragraph("Receita de processo proposta", styles["Title"]),
             Paragraph(f"Versão: {metadata.get('versão', 1)} | Modo: {result.get('mode', 'exploratório')}", styles["Normal"]), Spacer(1, 5*mm)]
    headers = ["Máquina", "Parâmetro", "Unidade", "Target", "Inferior", "Superior", "Status"]
    keys = ["machine", "parameter", "unit", "target", "lower", "upper", "status"]
    rows = [headers] + [[Paragraph(str(_safe(item.get(k))), styles["BodyText"]) for k in keys] for item in result.get("items", [])]
    table = LongTable(rows, repeatRows=1, colWidths=[37*mm,45*mm,28*mm,25*mm,25*mm,25*mm,35*mm])
    table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.lightgrey), ("GRID",(0,0),(-1,-1),.3,colors.grey), ("VALIGN",(0,0),(-1,-1),"TOP")]))
    story += [table, PageBreak(), Paragraph("Evidências, hipóteses e limitações", styles["Heading1"])]
    for section in ("evidence", "assumptions", "pending"):
        story.append(Paragraph(section.capitalize(), styles["Heading2"]))
        story.extend(Paragraph("• " + str(x), styles["BodyText"]) for x in result.get(section, []))
    story.append(Paragraph("Esta proposta não garante uma receita ideal nem validação industrial. Faixas marginais não garantem combinações.", styles["BodyText"]))
    doc.build(story); return stream.getvalue()
