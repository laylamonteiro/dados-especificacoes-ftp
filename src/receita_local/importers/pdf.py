from __future__ import annotations

import re
from pathlib import Path

import pdfplumber

from receita_local.domain.models import Requirement

METHOD = re.compile(r"^(?P<property>.+?)\s+(?P<method>[A-Z]{2,4}-\d{3,6})\s+(?P<unit>\S+)\s+(?P<rest>.+)$")
SECTION = re.compile(r"^\s*(?P<number>\d+[A-Z]?)\s*-\s*(?P<title>.+)$")
HEADER = re.compile(r"propriedade\s+m[ée]todo\s+unidade", re.IGNORECASE)
STAGES = ("espessura após bobinamento", "após bobinamento", "slitter", "winder")


def _number(token: str) -> float | None:
    """'-' e vazio significam limite ausente (unilateral); nunca viram zero."""
    token = token.strip()
    if token in ("", "-", "--", "n/a", "N/A"):
        return None
    try:
        return float(token.replace(".", "").replace(",", ".") if re.fullmatch(r"-?\d{1,3}(\.\d{3})+(,\d+)?", token)
                     else token.replace(",", "."))
    except ValueError:
        return None


def _is_limit(token: str) -> bool:
    return token.strip() in ("-", "--") or _number(token) is not None


def _stage(property_name: str) -> str:
    lowered = property_name.lower()
    for stage in STAGES:
        if stage in lowered:
            return "após bobinamento" if "bobinamento" in stage else stage.capitalize()
    return "não confirmada"


def extract_metadata(text: str) -> dict[str, str]:
    fields = {
        "produto": r"C[óo]digo do Produto:?\s*(\S+)",
        "especificacao": r"C[óo]digo da Especifia?[çc][ãa]o:?\s*(\S+)",
        "numero_especificacao": r"N[úu]mero Especifica[çc][ãa]o:?\s*(\S+)",
        "cliente": r"Cliente:?\s*(.+)",
        "site": r"Site:?\s*(.+)",
        "data_documento": r"Data do Documento:?\s*(\S+)",
    }
    out = {}
    for key, pattern in fields.items():
        match = re.search(pattern, text)
        if match:
            out[key] = match.group(1).strip()
    return out


def parse_requirements(text: str) -> list[Requirement]:
    """Lê as tabelas de propriedades a partir do texto, preservando limites unilaterais.

    Distingue requisito do cliente de controle interno pela seção do documento e
    registra a etapa (Winder/Slitter/após bobinamento) quando o nome a declara.
    """
    requirements: list[Requirement] = []
    criterion = "não confirmado"
    for line_no, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        section = SECTION.match(line)
        if section and "propriedade" in section.group("title").lower():
            title = section.group("title").lower()
            criterion = "controle interno" if "interno" in title or "processo" in title else "requisito do cliente"
            continue
        if HEADER.search(line):
            continue
        match = METHOD.match(line)
        if not match:
            continue
        tokens = match.group("rest").split()
        name = match.group("property").strip()
        common = dict(stage=_stage(name), unit=match.group("unit"), criterion=criterion,
                      method=match.group("method"), source=f"linha {line_no} do PDF")
        if len(tokens) >= 3 and all(_is_limit(t) for t in tokens[:3]):
            requirements.append(Requirement(name, minimum=_number(tokens[0]), target=_number(tokens[1]),
                                            maximum=_number(tokens[2]), **common))
        else:
            observation = " ".join(t for t in tokens if t != "-").strip()
            requirements.append(Requirement(name, kind="qualitative", target_text=observation or None, **common))
    return requirements


def extract_specification(path: str | Path) -> tuple[list[Requirement], list[str], str]:
    warnings, pages = [], []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            pages.append(page.extract_text() or "")
    text = "\n".join(pages)
    if not text.strip():
        warnings.append("PDF sem texto utilizável; OCR não está no MVP. Cadastre os requisitos manualmente.")
        return [], warnings, text

    requirements = parse_requirements(text)
    if not requirements:
        warnings.append("O texto do PDF foi lido, mas nenhuma linha de requisito foi reconhecida. "
                        "Cadastre os requisitos manualmente em Regras e hipóteses.")
        return [], warnings, text

    warnings.append("Requisitos extraídos são propostas: confirme etapa, unidade e semântica dos limites.")
    unilateral = [r.property for r in requirements if r.kind == "numeric" and (r.minimum is None) != (r.maximum is None)]
    if unilateral:
        warnings.append(f"{len(unilateral)} requisitos têm limite unilateral e foram preservados assim: "
                        + ", ".join(sorted(set(unilateral))[:6]))
    if any(r.kind == "qualitative" for r in requirements):
        warnings.append("Requisitos qualitativos (ex.: Aparência) não têm limites numéricos e ficam fora do cálculo.")
    return requirements, warnings, text
