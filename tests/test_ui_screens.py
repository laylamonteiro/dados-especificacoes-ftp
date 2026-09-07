"""Todas as telas precisam renderizar sem exceção e sem stack trace na interface."""
from __future__ import annotations

import pandas as pd
import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

APP = "src/receita_local/ui/app.py"
SCREENS = ["Produtos e análises", "Nova análise", "Revisão da importação", "Regras e hipóteses",
           "Diagnóstico dos dados", "Receita proposta", "Histórico e exportação"]


def seeded_app(tmp_path, monkeypatch) -> AppTest:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path))
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    st.cache_resource.clear()   # cada teste usa seu próprio banco
    at = AppTest.from_file(APP, default_timeout=90)
    at.session_state["process"] = pd.DataFrame({
        "_source_row": [2, 3, 4, 5], "Date": pd.date_range("2026-04-01", periods=4),
        "Ordem": ["1", "1", "2", "2"], "Temp": [10.0, 12.0, 40.0, 42.0], "Const": [7, 7, 7, 7]})
    at.session_state["lab"] = pd.DataFrame({"_source_row": [2, 3], "Gramatura.": [41.0, 52.0], "Seção": ["S1", "S2"]})
    at.session_state["requirements"] = [
        {"property": "Gramatura Slitter", "stage": "Slitter", "unit": "g/m²", "minimum": 40.5,
         "target": 45.0, "maximum": 49.5, "criterion": "requisito do cliente", "source": "pdf",
         "kind": "numeric", "target_text": None, "method": "PRC-04617"}]
    at.session_state["rules"] = [ParameterRuleDict("Temp"), ParameterRuleDict("Const")]
    at.session_state["engine_config"] = {"condition_columns": ["Ordem"], "order_column": "Ordem",
                                         "time_column": "Date", "qlow": 0.1, "qhigh": 0.9, "max_gap_minutes": 180}
    at.session_state["product"] = "PRODUTO-TESTE"
    at.session_state["process_meta"] = {"arquivo": "sintetico.xlsx", "aceitos": 4}
    at.session_state["lab_meta"] = {"arquivo": "lab.xlsx", "aceitos": 2}
    return at


def ParameterRuleDict(name: str) -> dict:
    return {"name": name, "kind": "numeric", "unit": "—", "adjustable": True, "precision": 0.1,
            "minimum": None, "maximum": None, "fixed": None, "confirmed": False, "source": "teste"}


@pytest.mark.parametrize("screen", SCREENS)
def test_tela_renderiza_sem_excecao(screen, tmp_path, monkeypatch):
    at = seeded_app(tmp_path, monkeypatch)
    at.run()
    assert not at.exception, f"exceção ao carregar: {at.exception}"
    at.sidebar.radio[0].set_value(screen).run()
    assert not at.exception, f"exceção em '{screen}': {at.exception}"
    assert not at.error, f"erro exibido em '{screen}': {[e.value for e in at.error]}"


def test_receita_gerada_pela_interface_e_salva_no_historico(tmp_path, monkeypatch):
    at = seeded_app(tmp_path, monkeypatch)
    at.run()
    at.sidebar.radio[0].set_value("Receita proposta").run()
    next(b for b in at.button if "Gerar proposta" in b.label).click().run()
    assert not at.exception
    assert any("Análise salva" in s.value for s in at.success)
    result = at.session_state["result"]
    assert result["mode"] == "exploratório" and result["items"]
    # a receita usou apenas a condição selecionada, não misturou as duas ordens
    temp = next(i for i in result["items"] if i["parameter"] == "Temp")
    assert temp["upper"] <= 12.0 or temp["lower"] >= 40.0
    assert any("Qualidade não avaliada" in p for p in result["pending"])

    # reabrir pelo histórico não recalcula: a receita salva é lida como está
    aid = at.session_state["analysis_id"]
    at.sidebar.radio[0].set_value("Histórico e exportação").run()
    assert not at.exception
    assert any("PRODUTO-TESTE" in str(box.options) for box in at.selectbox), \
        "a análise salva precisa aparecer no histórico"

    from receita_local.exports.writers import excel_bytes, pdf_bytes
    from receita_local.storage.repository import Repository
    stored = Repository(tmp_path / "ReceitasProcesso").get_version(aid, 1)
    assert stored["items"] == result["items"], "o histórico devolve exatamente o que foi calculado"
    assert excel_bytes(stored, {"id": aid}).startswith(b"PK")
    assert pdf_bytes(stored, {"id": aid}).startswith(b"%PDF")
