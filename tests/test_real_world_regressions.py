"""Regressões observadas nos arquivos de referência do estudo de caso.

As fixtures são sintéticas mas reproduzem exatamente as armadilhas encontradas:
rodapé de estatísticas sem data, cabeçalho repetido, aba vazia e a tabela de
requisitos do PDF com limites unilaterais.
"""
from __future__ import annotations

import inspect
import socket

import numpy as np
import pandas as pd
import pytest
from openpyxl import Workbook

from receita_local.analysis.engine import (evaluate_quality_columns, generate_exploratory_recipe,
                                           identify_blocks, partition_conditions, robust_medoid)
from receita_local.domain.models import ParameterRule, Requirement
from receita_local.importers.excel import import_sheet
from receita_local.importers.pdf import parse_requirements

SPEC_TEXT = """3 - Propriedades Físicas - Produto
Propriedade Método Unidade Mínimo Objetivo Máximo Observações
Gramatura Slitter PRC-04617 g/m² 40,5 45 49,5 -
Resistência MD PRC-04809 N/5cm 65 100 - -
3A - Propriedades Físicas - Processo (Controle interno)
Propriedade Método Unidade Mínimo Objetivo Máximo Observações
Gramatura Winder PRC-04617 g/m² 39,0 43,0 47,0 -
Capacidade de Absorção PRC-36520 g/g 9 - - -
Espessura após bobinamento PRC-04607 mm 0,50 0,65 0,80 -
Aparência PRC-22801 Visual Conforme Amostra Padrão -
"""


def process_workbook(path):
    wb = Workbook(); ws = wb.active; ws.title = "PARAMETROS DE PROCESSO "
    ws.append(["regra textual introdutória"])
    ws.append(["Date", "Time", "Receita", "Ordem", "Temp", "Const"])
    for day in range(1, 6):
        ws.append([f"2026-04-0{day}", "08:00:00", "KSEI8BR45", "144138", 10 + day, 7])
    for day in range(1, 5):
        ws.append([f"2026-05-0{day}", "08:00:00", "KSEI8BR45", "146748", 40 + day, 7])
    ws.append(["Date", "Time", "Receita", "Ordem", "Temp", "Const"])   # cabeçalho ao final
    ws.append([None, None, None, None, "Média", 7])
    ws.append([None, None, None, None, 999, 999])                      # +3sigma sem rótulo
    ws.append([None, None, None, "+3sigma", 888, 888])
    wb.save(path)


def test_rodape_de_estatisticas_nao_vira_registro_de_producao(tmp_path):
    path = tmp_path / "processo com acento ç.xlsx"; process_workbook(path)
    review = import_sheet(path, "PARAMETROS DE PROCESSO ")
    assert len(review.frame) == 9, "só as linhas com data são registros de produção"
    assert review.timestamp_column == "Date"
    reasons = set(review.exclusion_summary)
    assert "cabeçalho repetido" in reasons and "estatística agregada" in reasons
    assert any("sem data válida" in r for r in reasons)
    assert 999 not in pd.to_numeric(review.frame["Temp"], errors="coerce").tolist()


def test_limites_nao_sao_inventados_a_partir_de_estatisticas(tmp_path):
    """`Const` é constante na produção; só o rodapé lhe daria uma tolerância."""
    path = tmp_path / "processo.xlsx"; process_workbook(path)
    frame = import_sheet(path, "PARAMETROS DE PROCESSO ").frame
    recipe = generate_exploratory_recipe(frame, [ParameterRule("Const", precision=0.1)])
    item = recipe.items[0]
    assert item.lower is None and item.upper is None
    assert item.status == "tolerância pendente" and recipe.pending


def test_aba_vazia_gera_mensagem_acionavel_e_nao_stack_trace(tmp_path):
    wb = Workbook(); wb.active.title = "SLITTER"; wb.save(tmp_path / "lab.xlsx")
    with pytest.raises(ValueError, match="não tem linhas para importar"):
        import_sheet(tmp_path / "lab.xlsx", "SLITTER")


def test_condicoes_incompativeis_sao_separadas_antes_da_referencia(tmp_path):
    path = tmp_path / "processo.xlsx"; process_workbook(path)
    frame = import_sheet(path, "PARAMETROS DE PROCESSO ").frame
    groups = partition_conditions(frame, ["Ordem"])
    assert [g["records"] for g in groups] == [5, 4]
    recipe = generate_exploratory_recipe(frame, [ParameterRule("Temp", precision=1)],
                                         condition_columns=["Ordem"], order_column="Ordem", time_column="Date")
    # A ordem 144138 (Temp 11..15) foi escolhida; a receita não mistura a faixa 41..44.
    assert recipe.items[0].upper is not None and recipe.items[0].upper <= 15
    assert any("não combinadas" in e for e in recipe.evidence)
    assert any("apenas para a condição selecionada" in a for a in recipe.assumptions)


def test_blocos_de_producao_nao_atravessam_lacunas(tmp_path):
    path = tmp_path / "processo.xlsx"; process_workbook(path)
    frame = import_sheet(path, "PARAMETROS DE PROCESSO ").frame
    info = identify_blocks(frame, "Date", max_gap_minutes=180)
    assert info["blocks"] == 9, "cada dia é um bloco separado por lacuna longa"


def test_target_ausente_na_referencia_nao_e_imputado_por_mediana():
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0], "b": [np.nan, 5.0, 6.0, 50.0]})
    frame.loc[0, "b"] = np.nan
    recipe = generate_exploratory_recipe(frame, [ParameterRule("a"), ParameterRule("b")])
    item = next(i for i in recipe.items if i.parameter == "b")
    if item.status == "pendente":
        assert item.target is None and any("não foi imputado" in p for p in recipe.pending)
    else:
        assert item.target in frame["b"].dropna().tolist()


def test_medoid_e_deterministico_e_ignora_colunas_constantes():
    frame = pd.DataFrame({"x": [1.0, 2.0, 2.1, 2.2, 90.0], "fixo": [5, 5, 5, 5, 5]})
    assert robust_medoid(frame, ["x", "fixo"]) == robust_medoid(frame, ["x", "fixo"])
    assert robust_medoid(frame, ["x", "fixo"]) in [1, 2, 3]      # nunca o extremo 90


def test_requisitos_do_pdf_preservam_criterio_etapa_e_limites_unilaterais():
    reqs = parse_requirements(SPEC_TEXT)
    assert len(reqs) == 6
    by_key = {r.key: r for r in reqs}
    cliente = next(r for r in reqs if r.property == "Resistência MD")
    assert cliente.criterion == "requisito do cliente"
    assert cliente.minimum == 65 and cliente.maximum is None, "limite unilateral não vira zero"
    assert next(r for r in reqs if r.property == "Gramatura Winder").stage == "Winder"
    assert next(r for r in reqs if r.property == "Gramatura Slitter").stage == "Slitter"
    assert next(r for r in reqs if "bobinamento" in r.property).stage == "após bobinamento"
    aparencia = next(r for r in reqs if r.property == "Aparência")
    assert aparencia.kind == "qualitative" and "Conforme" in aparencia.target_text
    # cliente e controle interno coexistem sem colidir
    assert len({r.key for r in reqs}) == len(reqs)


def test_qualidade_sem_mapeamento_confirmado_fica_inconclusiva():
    lab = pd.DataFrame({"Gramatura.": [41.0, 44.0, 52.0], "Seção": ["S1", "S1", "S2"]})
    reqs = parse_requirements(SPEC_TEXT)
    gramatura = next(r for r in reqs if r.property == "Gramatura Slitter")
    sem_mapa = evaluate_quality_columns(lab, [gramatura], {})
    assert sem_mapa[0]["status"] == "inconclusivo", "ausência de teste nunca é aprovação"
    com_mapa = evaluate_quality_columns(lab, [gramatura], {gramatura.key: "Gramatura."}, section_column="Seção")
    assert com_mapa[0]["status"] == "não conforme" and com_mapa[0]["fora_do_limite"] == 1
    assert com_mapa[0]["seções"] == "S1, S2"


def test_quantis_incoerentes_sao_recusados_em_vez_de_gerar_faixa_invertida():
    frame = pd.DataFrame({"a": [1.0, 2.0, 3.0, 4.0]})
    with pytest.raises(ValueError, match="Quantis incoerentes"):
        generate_exploratory_recipe(frame, [ParameterRule("a")], qlow=.9, qhigh=.1)
    recipe = generate_exploratory_recipe(frame, [ParameterRule("a")], qlow=.1, qhigh=.9)
    item = recipe.items[0]
    assert item.lower <= item.target <= item.upper


def test_health_check_alcanca_o_servidor_local_apesar_do_proxy(monkeypatch):
    """Em rede corporativa o proxy captura até o loopback. Sem contorná-lo o health
    check conversaria com o proxy, e uma resposta dele faria o launcher abrir o
    navegador acreditando que a aplicação subiu."""
    import threading
    import urllib.error
    import urllib.request
    from http.server import BaseHTTPRequestHandler, HTTPServer

    from receita_local.launcher.main import direct_opener

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200); self.end_headers(); self.wfile.write(b"ok")

        def log_message(self, *args):
            pass

    server = HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}/_stcore/health"
    try:
        # Proxy apontando para uma porta fechada: quem passar por ele falha.
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0)); dead = probe.getsockname()[1]
        for name in ("http_proxy", "HTTP_PROXY", "https_proxy", "HTTPS_PROXY"):
            monkeypatch.setenv(name, f"http://127.0.0.1:{dead}")
        for name in ("no_proxy", "NO_PROXY"):
            monkeypatch.setenv(name, "")

        assert direct_opener().open(url, timeout=5).read() == b"ok"

        with pytest.raises(urllib.error.URLError):
            urllib.request.urlopen(url, timeout=5)   # comportamento anterior
    finally:
        server.shutdown(); server.server_close()


def test_aviso_de_proxy_so_aparece_quando_o_loopback_seria_capturado(monkeypatch):
    from receita_local.launcher import main

    monkeypatch.setattr(main.urllib.request, "getproxies", dict)
    assert main.loopback_proxy_warning() == "", "sem proxy não pode haver aviso falso"

    monkeypatch.setattr(main.urllib.request, "getproxies", lambda: {"http": "http://proxy.corp:8080"})
    monkeypatch.setattr(main.urllib.request, "proxy_bypass", lambda host: True)
    assert main.loopback_proxy_warning() == "", "proxy com bypass de loopback está correto"

    monkeypatch.setattr(main.urllib.request, "proxy_bypass", lambda host: False)
    warning = main.loopback_proxy_warning()
    assert "proxy" in warning.lower() and "127.0.0.1" in warning


def test_launcher_desliga_o_modo_desenvolvimento_do_streamlit():
    """Dentro do PyInstaller o caminho do pacote não contém site-packages, então o
    Streamlit liga global.developmentMode sozinho: passa a ignorar a porta pedida,
    escuta na 8501, devolve 404 em `/` e manda o navegador para a 3000 do servidor
    Node de desenvolvimento, que não existe no pacote."""
    from receita_local.launcher.main import streamlit_environment

    env = streamlit_environment(54321)
    assert env["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] == "false"
    assert env["STREAMLIT_SERVER_PORT"] == "54321"
    assert env["STREAMLIT_SERVER_ADDRESS"] == "127.0.0.1"


def test_streamlit_em_modo_desenvolvimento_recusaria_a_porta_escolhida():
    """Prova a condição que a configuração acima evita, na própria biblioteca."""
    from streamlit import config

    source = inspect.getsource(config._check_conflicts)
    assert "server.port does not work when global.developmentMode is true" in source
    # _global_development_mode é decorado e vira um ConfigOption; lemos o módulo.
    module = inspect.getsource(config)
    default = module[module.index("def _global_development_mode"):][:600]
    assert "site-packages" in default and "dist-packages" in default, (
        "o padrão do Streamlit depende do caminho do pacote; dentro do PyInstaller "
        "nenhum dos marcadores existe e o modo desenvolvimento é ligado"
    )
