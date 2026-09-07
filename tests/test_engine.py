import pandas as pd

from receita_local.analysis.engine import evaluate_quality, generate_exploratory_recipe, link_records
from receita_local.domain.models import ParameterRule, Requirement


def test_observed_target_constant_category_missing_and_repeatable():
    df = pd.DataFrame({"ordem":["001","001","002"], "temp":[10.,12.,14.], "const":[5,5,5], "tipo":["A","A","B"]})
    rules = [ParameterRule("temp",precision=1),ParameterRule("const"),ParameterRule("tipo",kind="categorical"),ParameterRule("sem_dado")]
    a = generate_exploratory_recipe(df,rules,order_column="ordem").to_dict()
    b = generate_exploratory_recipe(df,rules,order_column="ordem").to_dict()
    assert a == b
    assert next(x for x in a["items"] if x["parameter"]=="temp")["target"] in df.temp.tolist()
    constant = next(x for x in a["items"] if x["parameter"]=="const")
    assert constant["lower"] is None and constant["status"] == "tolerância pendente"
    assert next(x for x in a["items"] if x["parameter"]=="tipo")["target"] == "A"
    assert next(x for x in a["items"] if x["parameter"]=="sem_dado")["lower"] is None


def test_conflicting_constraint_is_not_silently_resolved():
    result=generate_exploratory_recipe(pd.DataFrame({"x":[1,2,3]}),[ParameterRule("x",minimum=10,maximum=20,confirmed=True)])
    assert result.items[0].status == "conflito" and result.pending


def test_quality_unilateral_and_missing_is_inconclusive():
    lab=pd.DataFrame({"p":["umidade","umidade"],"v":[4,7]})
    out=evaluate_quality(lab,[Requirement("umidade",maximum=6),Requirement("gramatura",minimum=10)],"p","v")
    assert [x["status"] for x in out] == ["não conforme","inconclusivo"]


def test_link_does_not_expand_many_to_many():
    out=link_records(pd.DataFrame({"lote":["1","1","2"]}),pd.DataFrame({"lote":["1","1","3"]}),"lote","lote")
    assert out["ambiguous"] == ["1"] and out["keys_linked"] == []
