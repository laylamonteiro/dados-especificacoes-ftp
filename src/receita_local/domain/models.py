from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Requirement:
    property: str
    stage: str = "não confirmada"
    unit: str = "não confirmada"
    minimum: float | None = None
    target: float | None = None
    maximum: float | None = None
    criterion: str = "proposto"
    source: str = ""


@dataclass
class ParameterRule:
    name: str
    kind: str = "numeric"  # numeric, categorical, identifier, context
    unit: str = "não confirmada"
    adjustable: bool = True
    precision: float | None = None
    minimum: float | None = None
    maximum: float | None = None
    fixed: Any = None
    confirmed: bool = False
    source: str = "usuário"


@dataclass
class RecipeItem:
    machine: str
    parameter: str
    unit: str
    target: Any = None
    lower: float | None = None
    upper: float | None = None
    conditions: str = ""
    origin: str = "histórico observado"
    evidence: str = ""
    status: str = "proposto"


@dataclass
class AnalysisResult:
    mode: str
    items: list[RecipeItem]
    evidence: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    quality: list[dict[str, Any]] = field(default_factory=list)
    reference: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "algorithm_version": "exploratory-medoid-v1"}
