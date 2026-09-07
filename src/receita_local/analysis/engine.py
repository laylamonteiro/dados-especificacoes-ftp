from __future__ import annotations

from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

import numpy as np
import pandas as pd

from receita_local.domain.models import AnalysisResult, ParameterRule, RecipeItem, Requirement


def _round(value: float, step: float | None) -> float:
    if not step:
        return float(value)
    d, s = Decimal(str(value)), Decimal(str(step))
    return float((d / s).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * s)


def robust_medoid(frame: pd.DataFrame, columns: list[str], minimum_overlap: int = 2) -> Any:
    """Medoid observado com distância normalizada por IQR. Determinístico e vetorizado.

    Pares sem sobreposição mínima de variáveis não recebem distância; nenhum valor
    ausente é imputado para fabricar um vetor completo.
    """
    if frame.empty:
        raise ValueError("Não há registros para escolher uma condição de referência.")
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce") if columns else pd.DataFrame(index=frame.index)
    scale = (numeric.quantile(.75) - numeric.quantile(.25)).replace(0, np.nan) if columns else pd.Series(dtype=float)
    usable = [c for c in columns if pd.notna(scale.get(c))]
    if not usable:
        return frame.index[0]
    z = numeric[usable].sub(numeric[usable].median()).div(scale[usable])
    matrix = z.to_numpy(dtype=float)
    present = ~np.isnan(matrix)
    filled = np.nan_to_num(matrix, nan=0.0)
    required = min(minimum_overlap, len(usable))
    scores = np.full(len(matrix), np.inf)
    for i in range(len(matrix)):
        common = present & present[i]
        counts = common.sum(axis=1)
        squared = (((filled - filled[i]) * common) ** 2).sum(axis=1)
        eligible = counts >= required
        if eligible.any():
            scores[i] = float(np.mean(np.sqrt(squared[eligible] / counts[eligible])))
    # Empate resolvido pela primeira posição observada: mesma entrada, mesma saída.
    return frame.index[int(np.argmin(scores))]


def partition_conditions(frame: pd.DataFrame, condition_columns: list[str]) -> list[dict[str, Any]]:
    """Separa condições incompatíveis. Grupos ordenados por nº de registros (desc) e chave (asc)."""
    columns = [c for c in condition_columns if c in frame]
    if not columns:
        return [{"key": {}, "label": "todos os registros", "records": len(frame), "index": frame.index}]
    groups = []
    for values, subset in frame.groupby([frame[c].astype(str) for c in columns], dropna=False, sort=True):
        values = values if isinstance(values, tuple) else (values,)
        key = dict(zip(columns, (str(v) for v in values)))
        groups.append({"key": key, "label": "; ".join(f"{k}={v}" for k, v in key.items()),
                       "records": len(subset), "index": subset.index})
    return sorted(groups, key=lambda g: (-g["records"], g["label"]))


def identify_blocks(frame: pd.DataFrame, time_column: str, max_gap_minutes: float = 180) -> dict[str, Any]:
    """Ordena temporalmente e conta blocos de produção. Lacunas longas não são atravessadas."""
    if time_column not in frame:
        return {"blocks": None, "ordered": frame, "note": "sem coluna temporal confirmada"}
    stamps = pd.to_datetime(frame[time_column], errors="coerce")
    valid = stamps.dropna().sort_values()
    if valid.empty:
        return {"blocks": None, "ordered": frame, "note": "coluna temporal sem valores válidos"}
    gaps = valid.diff() > pd.Timedelta(minutes=max_gap_minutes)
    blocks = int(gaps.sum()) + 1
    return {"blocks": blocks, "ordered": frame.loc[stamps.sort_values().index],
            "note": f"{blocks} blocos separados por lacunas acima de {max_gap_minutes:g} min"}


def generate_exploratory_recipe(frame: pd.DataFrame, rules: list[ParameterRule], *,
                                machine: str = "não confirmada", qlow: float = .10,
                                qhigh: float = .90, order_column: str | None = None,
                                time_column: str | None = None,
                                condition_columns: list[str] | None = None,
                                max_gap_minutes: float = 180) -> AnalysisResult:
    if frame.empty:
        return AnalysisResult("exploratório", [], pending=["Nenhum registro de processo aceito"])

    assumptions = ["Qualidade avaliada separadamente; sem join temporal artificial",
                   "Subconjunto chamado condição recorrente, não estabilidade estatística"]
    evidence: list[str] = []

    # 2. Separar condições incompatíveis antes de escolher qualquer referência.
    groups = partition_conditions(frame, condition_columns or [])
    selected = groups[0]
    subset = frame.loc[selected["index"]]
    if len(groups) > 1:
        alternatives = "; ".join(f"{g['label']} ({g['records']} reg.)" for g in groups[1:6])
        evidence.append(f"Condição selecionada: {selected['label']} — {selected['records']} de {len(frame)} registros.")
        evidence.append(f"Outras condições não combinadas nesta receita: {alternatives}")
        assumptions.append("Receita vale apenas para a condição selecionada; demais condições exigem análise própria.")
    elif condition_columns:
        evidence.append(f"Condição única identificada: {selected['label']}.")

    # 3-4. Ordenação temporal e blocos de produção.
    blocks_info = identify_blocks(subset, time_column, max_gap_minutes) if time_column else None
    if blocks_info:
        subset = blocks_info["ordered"]
        evidence.append(f"Sequência temporal por '{time_column}': {blocks_info['note']}.")

    numeric_rules = [r for r in rules if r.kind == "numeric" and r.name in subset]
    numeric_columns = [r.name for r in numeric_rules]
    medoid_idx = robust_medoid(subset, numeric_columns) if numeric_columns else subset.index[0]
    reference = subset.loc[medoid_idx]
    conditions = selected["label"] if condition_columns else "; ".join(
        f"{c}={reference[c]}" for c in (condition_columns or []) if c in subset and pd.notna(reference[c]))

    items, pending = [], []
    for rule in rules:
        series = subset[rule.name] if rule.name in subset else pd.Series(dtype=object)
        if rule.kind == "categorical":
            values = series.dropna().astype(str)
            target = Counter(values).most_common(1)[0][0] if len(values) else rule.fixed
            status = "proposto" if target is not None else "pendente"
            items.append(RecipeItem(machine, rule.name, rule.unit, target=target, conditions=conditions,
                                    evidence=f"categoria modal; n={len(values)}", status=status))
            if target is None:
                pending.append(f"{rule.name}: sem dados ou regra confirmada")
            continue
        if rule.kind != "numeric":
            continue
        values = pd.to_numeric(series, errors="coerce").dropna()
        if values.empty:
            if rule.confirmed and rule.fixed is not None:
                items.append(RecipeItem(machine, rule.name, rule.unit, target=rule.fixed,
                                        lower=rule.fixed, upper=rule.fixed, origin="regra técnica confirmada"))
            else:
                items.append(RecipeItem(machine, rule.name, rule.unit, status="pendente"))
                pending.append(f"{rule.name}: sem dados; nenhum limite foi inventado")
            continue

        observed = pd.to_numeric(pd.Series([reference.get(rule.name)]), errors="coerce").iloc[0]
        if pd.isna(observed):
            # Sem valor na condição de referência: não se inventa um target por mediana.
            items.append(RecipeItem(machine, rule.name, rule.unit, conditions=conditions,
                                    evidence=f"parâmetro ausente na condição de referência; n={len(values)}",
                                    status="pendente"))
            pending.append(f"{rule.name}: ausente na condição de referência; target não foi imputado")
            continue
        target = float(observed)

        if values.nunique() == 1:
            items.append(RecipeItem(machine, rule.name, rule.unit, target=_round(target, rule.precision),
                                    conditions=conditions, evidence=f"valor constante observado; n={len(values)}",
                                    status="tolerância pendente"))
            pending.append(f"{rule.name}: sem evidência para tolerância")
            continue

        lo, hi = float(values.quantile(qlow)), float(values.quantile(qhigh))
        conflict = rule.confirmed and ((rule.minimum is not None and hi < rule.minimum) or
                                       (rule.maximum is not None and lo > rule.maximum) or
                                       (rule.minimum is not None and rule.maximum is not None and rule.minimum > rule.maximum))
        if conflict:
            items.append(RecipeItem(machine, rule.name, rule.unit, target=_round(target, rule.precision),
                                    evidence=f"quantis {qlow:g}/{qhigh:g}; n={len(values)}", status="conflito"))
            pending.append(f"{rule.name}: conflito entre histórico e restrição confirmada")
            continue
        lo = max(lo, rule.minimum) if rule.confirmed and rule.minimum is not None else lo
        hi = min(hi, rule.maximum) if rule.confirmed and rule.maximum is not None else hi
        target = min(max(target, lo), hi)
        items.append(RecipeItem(machine, rule.name, rule.unit, _round(target, rule.precision),
                                _round(lo, rule.precision), _round(hi, rule.precision), conditions,
                                evidence=f"vetor observado + quantis {qlow:g}/{qhigh:g}; n={len(values)}"))

    orders = subset[order_column].nunique(dropna=True) if order_column and order_column in subset else "não identificado"
    evidence.insert(0, f"{len(subset)} registros; {orders} ordens (registros não tratados como produções independentes)")
    evidence.append("Faixas marginais não garantem que qualquer combinação funcione; preserve a condição conjunta.")
    return AnalysisResult("exploratório", items, evidence, pending, assumptions,
                          reference={k: None if pd.isna(v) else v for k, v in reference.to_dict().items()})


def _classify(values: pd.Series, req: Requirement) -> tuple[str, int]:
    if values.empty:
        return "inconclusivo", 0
    outside = pd.Series(False, index=values.index)
    if req.minimum is not None:
        outside |= values < req.minimum
    if req.maximum is not None:
        outside |= values > req.maximum
    if req.minimum is None and req.maximum is None:
        return "inconclusivo", 0
    return ("não conforme" if outside.any() else "conforme"), int(outside.sum())


def evaluate_quality(lab: pd.DataFrame, requirements: list[Requirement], property_column: str,
                     value_column: str, *, stage_column: str | None = None,
                     section_column: str | None = None) -> list[dict[str, Any]]:
    """Formato longo (uma linha por ensaio). Ausência de teste nunca é aprovação."""
    output = []
    for req in requirements:
        subset = lab[lab[property_column].astype(str) == req.property] if property_column in lab else pd.DataFrame()
        if stage_column and stage_column in subset and req.stage not in ("", "não confirmada"):
            subset = subset[subset[stage_column].astype(str) == req.stage]
        vals = pd.to_numeric(subset[value_column], errors="coerce").dropna() if value_column in subset else pd.Series(dtype=float)
        status, outside = _classify(vals, req)
        row = {"propriedade": req.property, "etapa": req.stage, "status": status,
               "resultados": len(vals), "fora_do_limite": outside, "total_registros": len(subset),
               "limite_inferior": req.minimum, "limite_superior": req.maximum}
        if section_column and section_column in subset and not subset.empty:
            row["seções"] = ", ".join(sorted(subset[section_column].dropna().astype(str).unique())[:10])
        output.append(row)
    return output


def evaluate_quality_columns(lab: pd.DataFrame, requirements: list[Requirement],
                             mapping: dict[str, str], *, section_column: str | None = None) -> list[dict[str, Any]]:
    """Formato largo (uma coluna por propriedade), como nas planilhas de laboratório.

    `mapping` liga propriedade -> coluna e precisa ser confirmado pelo usuário:
    nenhuma equivalência é adivinhada.
    """
    output = []
    for req in requirements:
        column = mapping.get(req.key) or mapping.get(req.property)
        if req.kind != "numeric":
            output.append({"requisito": req.key, "propriedade": req.property, "etapa": req.stage,
                           "critério": req.criterion, "status": "inconclusivo", "resultados": 0,
                           "fora_do_limite": 0, "total_registros": 0, "limite_inferior": None,
                           "limite_superior": None, "observação": f"qualitativo: {req.target_text or 'sem critério numérico'}"})
            continue
        if not column or column not in lab:
            output.append({"requisito": req.key, "propriedade": req.property, "etapa": req.stage,
                           "critério": req.criterion, "status": "inconclusivo",
                           "resultados": 0, "fora_do_limite": 0, "total_registros": 0,
                           "limite_inferior": req.minimum, "limite_superior": req.maximum,
                           "observação": "coluna não mapeada"})
            continue
        vals = pd.to_numeric(lab[column], errors="coerce").dropna()
        status, outside = _classify(vals, req)
        row = {"requisito": req.key, "propriedade": req.property, "etapa": req.stage,
               "critério": req.criterion, "status": status,
               "resultados": len(vals), "fora_do_limite": outside, "total_registros": len(lab),
               "limite_inferior": req.minimum, "limite_superior": req.maximum, "coluna": column}
        if section_column and section_column in lab:
            row["seções"] = ", ".join(sorted(lab[section_column].dropna().astype(str).unique())[:10])
        output.append(row)
    return output


def link_records(process: pd.DataFrame, lab: pd.DataFrame, process_key: str, lab_key: str) -> dict[str, Any]:
    if not process_key or not lab_key or process_key not in process or lab_key not in lab:
        raise ValueError("Modo vinculado requer chaves confirmadas existentes")
    pc, lc = process[process_key].astype(str).value_counts(), lab[lab_key].astype(str).value_counts()
    common = set(pc.index) & set(lc.index)
    ambiguous = {k for k in common if pc[k] > 1 and lc[k] > 1}
    safe = common - ambiguous
    return {"keys_linked": sorted(safe), "ambiguous": sorted(ambiguous),
            "process_unmatched": int((~process[process_key].astype(str).isin(common)).sum()),
            "lab_unmatched": int((~lab[lab_key].astype(str).isin(common)).sum()),
            "coverage": len(safe) / max(1, len(set(process[process_key].astype(str))))}
