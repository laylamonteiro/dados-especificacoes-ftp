OPS = {"eq", "ne", "lt", "le", "gt", "ge", "in"}


def validate_declarative_rule(rule: dict) -> None:
    """Reject executable/free-form expressions; only a small declarative grammar is accepted."""
    if rule.get("operator") not in OPS or "field" not in rule or "value" not in rule:
        raise ValueError("Regra inválida: use field, operator permitido e value")
