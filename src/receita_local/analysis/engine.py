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


def robust_medoid(frame: pd.DataFrame, columns: list[str], minimum_overlap: int = 2) -> int:
    numeric = frame[columns].apply(pd.to_numeric, errors="coerce")
    scale = (numeric.quantile(.75) - numeric.quantile(.25)).replace(0, np.nan)
    usable = [c for c in columns if pd.notna(scale[c])]
    if not usable:
        return int(frame.index[0])
    z = numeric[usable].sub(numeric[usable].median()).div(scale[usable])
    scores = []
    for idx, row in z.iterrows():
        distances = []
        for jdx, other in z.iterrows():
            common = row.notna() & other.notna()
            if int(common.sum()) >= min(minimum_overlap, len(usable)):
                distances.append(float(np.sqrt(np.mean((row[common] - other[common]) ** 2))))
        scores.append((np.mean(distances) if distances else np.inf, str(idx), idx))
    return min(scores)[2]


def generate_exploratory_recipe(frame: pd.DataFrame, rules: list[ParameterRule], *,
                                machine: str = "não confirmada", qlow: float = .10,
                                qhigh: float = .90, order_column: str | None = None,
                                condition_columns: list[str] | None = None) -> AnalysisResult:
    if frame.empty:
        return AnalysisResult("exploratório", [], pending=["Nenhum registro de processo aceito"])
    numeric_rules = [r for r in rules if r.kind == "numeric" and r.name in frame]
    categorical = [r for r in rules if r.kind == "categorical" and r.name in frame]
    numeric_columns = [r.name for r in numeric_rules]
    medoid_idx = robust_medoid(frame, numeric_columns) if numeric_columns else frame.index[0]
    reference = frame.loc[medoid_idx]
    conditions = "; ".join(f"{c}={reference[c]}" for c in (condition_columns or []) if c in frame and pd.notna(reference[c]))
    items, pending = [], []
    for rule in rules:
        series = frame[rule.name] if rule.name in frame else pd.Series(dtype=object)
        if rule.kind == "categorical":
            values = series.dropna().astype(str)
            target = Counter(values).most_common(1)[0][0] if len(values) else rule.fixed
            status = "proposto" if target is not None else "pendente"
            items.append(RecipeItem(machine, rule.name, rule.unit, target=target, conditions=conditions,
                                    evidence=f"categoria modal; n={len(values)}", status=status))
            if target is None: pending.append(f"{rule.name}: sem dados ou regra confirmada")
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
        target = pd.to_numeric(pd.Series([reference.get(rule.name)]), errors="coerce").iloc[0]
        target = float(target) if pd.notna(target) else float(values.median())
        if values.nunique() == 1:
            item = RecipeItem(machine, rule.name, rule.unit, target=_round(target, rule.precision),
                              conditions=conditions, evidence=f"valor constante observado; n={len(values)}",
                              status="tolerância pendente")
            pending.append(f"{rule.name}: sem evidência para tolerância")
        else:
            lo, hi = float(values.quantile(qlow)), float(values.quantile(qhigh))
            conflict = rule.confirmed and ((rule.minimum is not None and hi < rule.minimum) or
                                            (rule.maximum is not None and lo > rule.maximum) or
                                            (rule.minimum is not None and rule.maximum is not None and rule.minimum > rule.maximum))
            if conflict:
                item = RecipeItem(machine, rule.name, rule.unit, target=_round(target, rule.precision),
                                  evidence=f"quantis {qlow:g}/{qhigh:g}; n={len(values)}", status="conflito")
                pending.append(f"{rule.name}: conflito entre histórico e restrição confirmada")
            else:
                lo = max(lo, rule.minimum) if rule.confirmed and rule.minimum is not None else lo
                hi = min(hi, rule.maximum) if rule.confirmed and rule.maximum is not None else hi
                target = min(max(target, lo), hi)
                item = RecipeItem(machine, rule.name, rule.unit, _round(target, rule.precision),
                                  _round(lo, rule.precision), _round(hi, rule.precision), conditions,
                                  evidence=f"vetor observado + quantis {qlow:g}/{qhigh:g}; n={len(values)}")
            items.append(item); continue
        items.append(item)
    orders = frame[order_column].nunique(dropna=True) if order_column and order_column in frame else "não identificado"
    evidence = [f"{len(frame)} registros; {orders} ordens (registros não tratados como produções independentes)",
                "Faixas marginais não garantem que qualquer combinação funcione; preserve a condição conjunta."]
    return AnalysisResult("exploratório", items, evidence, pending,
                          ["Qualidade avaliada separadamente; sem join temporal artificial", "Subconjunto chamado condição recorrente, não estabilidade"],
                          reference={k: None if pd.isna(v) else v for k, v in reference.to_dict().items()})


def evaluate_quality(lab: pd.DataFrame, requirements: list[Requirement], property_column: str,
                     value_column: str) -> list[dict[str, Any]]:
    output = []
    for req in requirements:
        subset = lab[lab[property_column].astype(str) == req.property] if property_column in lab else pd.DataFrame()
        vals = pd.to_numeric(subset[value_column], errors="coerce").dropna() if value_column in subset else pd.Series(dtype=float)
        if vals.empty: status = "inconclusivo"
        elif ((req.minimum is not None and (vals < req.minimum).any()) or
              (req.maximum is not None and (vals > req.maximum).any())): status = "não conforme"
        else: status = "conforme"
        output.append({"propriedade": req.property, "etapa": req.stage, "status": status,
                       "resultados": len(vals), "total_registros": len(subset)})
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
