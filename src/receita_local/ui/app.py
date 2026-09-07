from __future__ import annotations

import json, os, sys, tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
if str(ROOT / "src") not in sys.path: sys.path.insert(0, str(ROOT / "src"))

from receita_local.analysis.engine import generate_exploratory_recipe
from receita_local.domain.models import ParameterRule
from receita_local.exports.writers import excel_bytes, pdf_bytes
from receita_local.importers.excel import import_sheet, inspect_workbook
from receita_local.importers.pdf import extract_specification
from receita_local.storage.repository import Repository

st.set_page_config(page_title="Receita Local", layout="wide")
repo = Repository()
st.title("🏭 Receita Local")
st.caption("Processamento 100% local • modo exploratório • não garante receita ideal")

page = st.sidebar.radio("Tela", ["Produtos e análises", "Nova análise", "Revisão e diagnóstico", "Regras e hipóteses", "Receita proposta", "Histórico e exportação"])
if st.sidebar.button("Encerrar aplicativo"):
    marker = os.environ.get("RECEITA_STOP_FILE")
    if marker: Path(marker).write_text("stop", encoding="utf-8")
    st.success("Encerramento solicitado. Esta aba pode ser fechada.")

if page == "Produtos e análises":
    st.subheader("Análises recentes")
    st.dataframe(pd.DataFrame(repo.list_analyses()), use_container_width=True)
    st.info("KSEA8BR45 ↔ KSEI8BR45 é um alias permitido somente quando explicitamente confirmado e salvo.")

elif page == "Nova análise":
    st.subheader("1. Seleção de arquivos")
    st.session_state["product"] = st.text_input("Produto", st.session_state.get("product", "KSEA8BR45"))
    st.checkbox("Confirmo alias KSEA8BR45 = KSEI8BR45", key="alias")
    uploads = st.file_uploader("PDF de especificação e dois Excel", type=["pdf","xlsx"], accept_multiple_files=True)
    if st.button("Carregar demonstração sintética (sem arquivos reais)"):
        st.session_state["product"] = "DEMO-SINTETICO"
        st.session_state["process"] = pd.read_csv(ROOT / "fixtures/demo/processo.csv", dtype={"ordem": str})
        st.session_state["rules"] = [ParameterRule("temperatura", unit="°C", precision=1).__dict__, ParameterRule("velocidade", unit="m/min", precision=1).__dict__, ParameterRule("configuracao",kind="categorical",unit="categoria").__dict__]
        st.session_state["docs"] = []
        st.success("Demonstração identificada e carregada; ela não representa dados industriais reais.")
    if st.button("Importar cópias de trabalho", disabled=len(uploads or []) != 3):
        docs, paths = [], []
        for upload in uploads:
            tmp = Path(tempfile.gettempdir()) / upload.name; tmp.write_bytes(upload.getbuffer()); paths.append(tmp); docs.append(repo.import_file(tmp))
        st.session_state["docs"], st.session_state["paths"] = docs, [str(p) for p in paths]
        pdf = next((p for p in paths if p.suffix.lower()==".pdf"), None)
        if pdf:
            reqs, warnings, _ = extract_specification(pdf); st.session_state["requirements"] = [r.__dict__ for r in reqs]; st.session_state["pdf_warnings"] = warnings
        st.success("Arquivos copiados, hash SHA-256 registrado; originais inalterados.")
        st.json(docs)

elif page == "Revisão e diagnóstico":
    st.subheader("2. Revisão da importação")
    excel_paths = [Path(p) for p in st.session_state.get("paths", []) if p.lower().endswith(".xlsx")]
    if not excel_paths: st.warning("Importe os arquivos primeiro.")
    else:
        chosen = st.selectbox("Arquivo de processo", excel_paths, format_func=lambda p:p.name)
        info = inspect_workbook(chosen); sheet = st.selectbox("Aba", [s["name"] for s in info["sheets"]])
        detected = import_sheet(chosen, sheet)
        header = st.number_input("Linha de cabeçalho", 1, 200, detected.header_row)
        review = import_sheet(chosen, sheet, int(header)-1)
        st.write(f"Aceitos: {len(review.frame)} | Excluídos: {len(review.excluded)}")
        st.dataframe(review.frame.head(100), use_container_width=True)
        with st.expander("Exclusões e alertas"): st.json({"excluded":review.excluded,"warnings":review.warnings,"formulas_sem_cache":info["formula_without_cache"]})
        if st.button("Confirmar dados de processo"): st.session_state["process"] = review.frame; st.success("Revisão preservada nesta sessão.")

elif page == "Regras e hipóteses":
    st.subheader("3. Regras configuráveis")
    frame = st.session_state.get("process")
    if frame is None: st.warning("Confirme a importação primeiro.")
    else:
        choices = [c for c in frame.columns if c != "_source_row"]
        selected = st.multiselect("Parâmetros numéricos", choices)
        categories = st.multiselect("Condições categóricas", [c for c in choices if c not in selected])
        unit = st.text_input("Unidade padrão (marque como não confirmada quando desconhecida)", "não confirmada")
        if st.button("Salvar regras para a análise"):
            st.session_state["rules"] = [ParameterRule(x, unit=unit).__dict__ for x in selected] + [ParameterRule(x,kind="categorical",unit="categoria").__dict__ for x in categories]
            st.success("Regras salvas; nenhuma unidade ou equivalência foi inferida silenciosamente.")
    st.write("Hipóteses fixas: qualidade separada; especificação atual é referência exploratória; datas divergentes não criam vínculo.")

elif page == "Receita proposta":
    st.subheader("4. Receita exploratória")
    frame, raw_rules = st.session_state.get("process"), st.session_state.get("rules", [])
    if frame is None or not raw_rules: st.warning("Confirme dados e regras primeiro.")
    elif st.button("Gerar proposta determinística"):
        result = generate_exploratory_recipe(frame, [ParameterRule(**r) for r in raw_rules])
        if st.session_state.get("alias"): result.assumptions.append("Alias explícito confirmado: KSEA8BR45 = KSEI8BR45")
        payload = result.to_dict(); aid = repo.save_analysis(st.session_state.get("product","sem produto"), {"quantis":[.1,.9],"alias_confirmado":st.session_state.get("alias",False)}, payload, [d["id"] for d in st.session_state.get("docs",[])])
        st.session_state["result"], st.session_state["analysis_id"] = payload, aid
        st.success(f"Análise salva: {aid}")
    if "result" in st.session_state:
        result=st.session_state["result"]; st.dataframe(pd.DataFrame(result["items"]),use_container_width=True); st.warning("Proposta preliminar. Revisada pelo usuário não significa validada em produção."); st.json({"evidências":result["evidence"],"pendências":result["pending"],"hipóteses":result["assumptions"]})

else:
    st.subheader("5. Histórico imutável e exportação")
    analyses = repo.list_analyses()
    if not analyses: st.info("Nenhuma análise salva.")
    else:
        aid = st.selectbox("Análise", [a["id"] for a in analyses], format_func=lambda x: next(a["product"]+" — "+a["created_at"] for a in analyses if a["id"]==x))
        result = repo.get_analysis(aid); st.dataframe(pd.DataFrame(result.get("items",[])),use_container_width=True)
        meta={"id":aid,"versão":1,"algoritmo":result.get("algorithm_version")}
        st.download_button("Baixar Excel",excel_bytes(result,meta),f"receita-{aid[:8]}.xlsx")
        st.download_button("Baixar PDF",pdf_bytes(result,meta),f"receita-{aid[:8]}.pdf")
        justification=st.text_input("Justificativa da revisão manual")
        if st.button("Salvar nova versão revisada",disabled=not justification): st.success(f"Versão {repo.save_revision(aid,result,justification)} salva; não é validação em produção.")
        confirm=st.checkbox("Confirmo exclusão desta análise")
        if st.button("Excluir análise",disabled=not confirm): repo.delete_analysis(aid); st.success("Análise excluída; arquivos compartilhados foram preservados.")
