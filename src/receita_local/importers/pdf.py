from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from receita_local.domain.models import Requirement


def extract_specification(path: str | Path) -> tuple[list[Requirement], list[str], str]:
    requirements, warnings, all_text = [], [], []
    with pdfplumber.open(path) as pdf:
        for page_no, page in enumerate(pdf.pages, 1):
            text = page.extract_text() or ""
            all_text.append(text)
            for table in page.extract_tables():
                for row_no, row in enumerate(table or [], 1):
                    cells = [str(x).strip() if x is not None else "" for x in row]
                    numbers = []
                    for cell in cells[1:]:
                        match = re.fullmatch(r"\s*(-?\d+(?:[.,]\d+)?)\s*", cell)
                        numbers.append(float(match.group(1).replace(",", ".")) if match else None)
                    if cells and cells[0] and any(v is not None for v in numbers):
                        values = [v for v in numbers if v is not None]
                        requirements.append(Requirement(cells[0], minimum=values[0] if len(values) > 1 else None,
                                                        maximum=values[-1], source=f"página {page_no}, tabela linha {row_no}"))
    text = "\n".join(all_text)
    if not text.strip():
        warnings.append("PDF sem texto utilizável; OCR não está no MVP. Cadastre requisitos manualmente.")
    if requirements:
        warnings.append("Requisitos extraídos são propostas: confirme etapa, unidade e semântica dos limites.")
    return requirements, warnings, text
