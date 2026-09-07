from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import pandas as pd
from openpyxl import load_workbook

# Rótulos de estatística observados nas planilhas de referência. A lista é explícita
# de propósito: nada é excluído por heurística silenciosa.
STATISTIC_LABELS = {
    "média", "media", "mediana", "desvio padrão", "desvio padrao", "desvio",
    "target", "mínimo", "minimo", "máximo", "maximo", "amplitude",
    "limite superior", "limite inferior", "lsc", "lic", "lse", "lie",
    "+3sigma", "-3sigma", "3sigma", "+3 sigma", "-3 sigma", "sigma",
    "cp", "cpk", "pp", "ppk", "contagem", "total", "n",
    "campo padrão", "campo padrao", "campo real", "campo sugerido",
    "padrão das ftps", "padrao das ftps", "aplicado", "estatítica", "estatística", "estatistica",
}

TIMESTAMP_TOKENS = ("data", "date", "timestamp", "data/hora")


@dataclass
class ImportReview:
    sheet: str
    header_row: int
    frame: pd.DataFrame
    excluded: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    mapping: dict[str, str] = field(default_factory=dict)
    timestamp_column: str | None = None

    @property
    def exclusion_summary(self) -> dict[str, int]:
        out: dict[str, int] = {}
        for item in self.excluded:
            out[item["reason"]] = out.get(item["reason"], 0) + 1
        return out


def _names(values: list[Any]) -> list[str]:
    seen: dict[str, int] = {}
    result = []
    for i, value in enumerate(values):
        base = str(value).strip() if value not in (None, "") else f"coluna_{i + 1}"
        n = seen.get(base, 0)
        seen[base] = n + 1
        result.append(base if n == 0 else f"{base}__{n + 1}")
    return result


def _normalize(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value).strip().lower())


def inspect_workbook(path: str | Path) -> dict[str, Any]:
    try:
        wb_formula = load_workbook(path, read_only=True, data_only=False, keep_vba=False)
        wb_values = load_workbook(path, read_only=True, data_only=True, keep_vba=False)
    except (PermissionError, OSError) as exc:
        raise ValueError("Arquivo indisponível localmente. No OneDrive, mantenha-o neste dispositivo.") from exc
    sheets, formula_without_cache = [], []
    for wf, wv in zip(wb_formula.worksheets, wb_values.worksheets):
        sheets.append({"name": wf.title, "rows": wf.max_row, "columns": wf.max_column,
                       "empty": wf.max_row is None or wf.max_row <= 1})
        for rf, rv in zip(wf.iter_rows(), wv.iter_rows()):
            for cf, cv in zip(rf, rv):
                if isinstance(cf.value, str) and cf.value.startswith("=") and cv.value is None:
                    formula_without_cache.append(f"{wf.title}!{cf.coordinate}")
    return {"sheets": sheets, "formula_without_cache": formula_without_cache[:100]}


def detect_header(path: str | Path, sheet: str, max_rows: int = 40) -> int:
    raw = pd.read_excel(path, sheet_name=sheet, header=None, nrows=max_rows, dtype=object)
    if raw.empty:
        raise ValueError(f"A aba '{sheet}' não tem linhas para importar. Escolha outra aba.")
    tokens = ("data", "hora", "lote", "ordem", "gramatura", "receita", "parâmetro")
    scores = [sum(any(t in str(v).lower() for t in tokens) for v in row if pd.notna(v)) for row in raw.values]
    if max(scores) == 0:
        raise ValueError(
            f"Não foi possível reconhecer um cabeçalho nas primeiras {max_rows} linhas da aba '{sheet}'. "
            "Informe a linha de cabeçalho manualmente.")
    return int(max(range(len(scores)), key=scores.__getitem__))


def detect_timestamp_column(columns: list[str]) -> str | None:
    for name in columns:
        if name == "_source_row":
            continue
        normalized = _normalize(name)
        if any(normalized == t or normalized.startswith(t) for t in TIMESTAMP_TOKENS):
            return name
    return None


def import_sheet(path: str | Path, sheet: str, header_row: int | None = None, *,
                 timestamp_column: str | None = None, require_timestamp: bool = True) -> ImportReview:
    header_row = detect_header(path, sheet) if header_row is None else header_row
    raw = pd.read_excel(path, sheet_name=sheet, header=None, dtype=object)
    if header_row >= len(raw):
        raise ValueError(f"A linha de cabeçalho {header_row + 1} está fora da aba '{sheet}'.")
    names = _names(raw.iloc[header_row].tolist())
    data = raw.iloc[header_row + 1 :].copy()
    data.columns = names
    data.insert(0, "_source_row", range(header_row + 2, header_row + 2 + len(data)))

    stamp = timestamp_column or detect_timestamp_column(names)
    if stamp is not None and stamp not in data.columns:
        raise ValueError(f"A coluna de data '{stamp}' não existe na aba '{sheet}'.")
    parsed_stamp = (pd.to_datetime(data[stamp], errors="coerce")
                    if (stamp is not None and require_timestamp) else None)

    excluded, keep = [], []
    header_norm = {_normalize(n) for n in names}
    for idx, row in data.iterrows():
        populated = [v for k, v in row.items() if k != "_source_row" and pd.notna(v) and str(v).strip()]
        vals = {_normalize(v) for v in populated}
        reason = None
        if not populated:
            reason = "linha vazia"
        elif len(vals & header_norm) >= max(2, min(4, len(populated) // 2)):
            reason = "cabeçalho repetido"
        elif vals & STATISTIC_LABELS:
            reason = "estatística agregada"
        elif parsed_stamp is not None and pd.isna(parsed_stamp.loc[idx]):
            # Registro de produção exige data válida; agregados no rodapé não têm.
            reason = f"sem data válida em '{stamp}' (não é registro de produção)"
        if reason:
            excluded.append({"row": int(row["_source_row"]), "reason": reason})
        else:
            keep.append(idx)

    frame = data.loc[keep].reset_index(drop=True)
    warnings = []
    duplicated = int(frame.drop(columns="_source_row").duplicated().sum())
    if duplicated:
        warnings.append(f"{duplicated} linhas duplicadas preservadas para revisão")
    if stamp is None:
        warnings.append("Nenhuma coluna de data reconhecida: registros não puderam ser separados de agregados por data.")
    if frame.empty:
        warnings.append("Nenhum registro aceito. Revise a linha de cabeçalho antes de prosseguir.")
    return ImportReview(sheet, header_row + 1, frame, excluded, warnings, timestamp_column=stamp)
