from __future__ import annotations

import sys, tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
if str(ROOT / "src") not in sys.path: sys.path.insert(0, str(ROOT / "src"))

from receita_local.analysis.engine import (evaluate_quality_columns, generate_exploratory_recipe,
                                           link_records, partition_conditions)
from receita_local.domain.models import ParameterRule, Requirement
from receita_local.exports.writers import excel_bytes, pdf_bytes
from receita_local.importers.excel import ImportReview, import_sheet, inspect_workbook
from receita_local.importers.pdf import extract_specification
from receita_local.storage.repository import Repository

def _version() -> str:
    # No pacote onedir o VERSAO.txt fica ao lado do .exe, não dentro de _internal.
    for candidate in (ROOT / "VERSAO.txt", ROOT.parent / "VERSAO.txt"):
        if candidate.exists():
            return candidate.read_text(encoding="utf-8").strip()
    return "0.2.0-dev"


VERSION = _version()

st.set_page_config(page_title="Receita Local", layout="wide")


@st.cache_resource
def get_repository() -> Repository:
    return Repository()


repo = get_repository()
state = st.session_state


def friendly(action, *args, **kwargs):
    """Executa mostrando mensagem acionável em vez de stack trace."""
    try:
        return action(*args, **kwargs)
    except ValueError as exc:
        st.error(str(exc)); return None
    except Exception as exc:  # noqa: BLE001 - a interface nunca mostra traceback
        st.error(f"Não foi possível concluir a operação: {type(exc).__name__}. Consulte os logs locais.")
        st.caption(str(exc)[:300]); return None


def review_panel(label: str, key: str) -> None:
    """Seleção de arquivo/aba/cabeçalho com prévia e motivos de exclusão."""
    paths = [Path(p) for p in state.get("paths", []) if p.lower().endswith(".xlsx")]
    if not paths:
        st.warning("Importe os arquivos na tela **Nova análise** primeiro."); return
    chosen = st.selectbox(f"Arquivo — {label}", paths, format_func=lambda p: p.name, key=f"file_{key}")
    info = friendly(inspect_workbook, chosen)
    if info is None: return
    names = [s["name"] for s in info["sheets"]]
    marks = {s["name"]: (" (vazia)" if s["empty"] else f" ({s['rows']} linhas)") for s in info["sheets"]}
    sheet = st.selectbox(f"Aba — {label}", names, format_func=lambda n: n + marks[n], key=f"sheet_{key}")

    detected = friendly(import_sheet, chosen, sheet)
    if detected is None: return
    header = st.number_input(f"Linha de cabeçalho — {label}", 1, 500, detected.header_row, key=f"header_{key}")
    review: ImportReview | None = friendly(import_sheet, chosen, sheet, int(header) - 1)
    if review is None: return

    c1, c2, c3 = st.columns(3)
    c1.metric("Registros aceitos", len(review.frame))
    c2.metric("Linhas excluídas", len(review.excluded))
    c3.metric("Coluna de data", review.timestamp_column or "não reconhecida")
    st.dataframe(review.frame.head(100), width="stretch")
    for warning in review.warnings: st.warning(warning)
    with st.expander("Motivos de exclusão e fórmulas sem cache"):
        st.write("**Exclusões por motivo:**", review.exclusion_summary)
        st.dataframe(pd.DataFrame(review.excluded), width="stretch")
        if info["formula_without_cache"]:
            st.error("Células com fórmula sem valor em cache — o dado não pode ser lido sem abrir no Excel:")
            st.write(info["formula_without_cache"])
    if st.button(f"Confirmar {label}", key=f"confirm_{key}", disabled=review.frame.empty):
        state[key] = review.frame
        state[f"{key}_meta"] = {"arquivo": chosen.name, "aba": sheet, "linha_cabecalho": int(header),
                                "aceitos": len(review.frame), "excluidos": review.exclusion_summary,
                                "coluna_data": review.timestamp_column}
        st.success(f"{label}: {len(review.frame)} registros confirmados para esta análise.")


st.title("🏭 Receita Local")
st.caption(f"Processamento 100% local • modo exploratório • não garante receita ideal • versão {VERSION}")

page = st.sidebar.radio("Tela", ["Produtos e análises", "Nova análise", "Revisão da importação",
                                 "Regras e hipóteses", "Diagnóstico dos dados", "Receita proposta",
                                 "Histórico e exportação"])
st.sidebar.divider()
st.sidebar.caption(f"Processo: {'✅' if 'process' in state else '—'}  |  Laboratório: {'✅' if 'lab' in state else '—'}")
if st.sidebar.button("Encerrar aplicativo"):
    import os
    marker = os.environ.get("RECEITA_STOP_FILE")
    if marker: Path(marker).write_text("stop", encoding="utf-8")
    st.success("Encerramento solicitado. Esta aba pode ser fechada.")

if page == "Produtos e análises":
    st.subheader("Análises recentes")
    analyses = repo.list_analyses()
    st.dataframe(pd.DataFrame(analyses) if analyses else pd.DataFrame(columns=["id", "product", "created_at"]),
                 width="stretch")
    st.info("KSEA8BR45 ↔ KSEI8BR45 é um alias permitido somente quando explicitamente confirmado e salvo.")

elif page == "Nova análise":
    st.subheader("1. Seleção de arquivos")
    state["product"] = st.text_input("Produto", state.get("product", "KSEA8BR45"))
    if st.checkbox("Confirmo alias KSEA8BR45 = KSEI8BR45", key="alias", value=state.get("alias", False)):
        repo.save_alias(state["product"], "KSEI8BR45")
    uploads = st.file_uploader("PDF de especificação e os dois Excel", type=["pdf", "xlsx"], accept_multiple_files=True)

    if st.button("Carregar demonstração sintética (sem arquivos reais)"):
        state["product"] = "DEMO-SINTETICO"
        state["process"] = pd.read_csv(ROOT / "fixtures/demo/processo.csv", dtype={"ordem": str})
        state["process_meta"] = {"arquivo": "processo.csv (demonstração)", "aceitos": None}
        state["rules"] = [ParameterRule("temperatura", unit="°C", precision=1).__dict__,
                          ParameterRule("velocidade", unit="m/min", precision=1).__dict__,
                          ParameterRule("configuracao", kind="categorical", unit="categoria").__dict__]
        state["docs"] = []; state["demo"] = True
        st.success("Demonstração identificada e carregada; ela não representa dados industriais reais.")

    if st.button("Importar cópias de trabalho", disabled=not uploads):
        docs, paths = [], []
        for upload in uploads:
            tmp = Path(tempfile.mkdtemp(prefix="receita_")) / upload.name
            tmp.write_bytes(upload.getbuffer()); paths.append(tmp); docs.append(repo.import_file(tmp))
        state["docs"], state["paths"], state["demo"] = docs, [str(p) for p in paths], False
        pdf = next((p for p in paths if p.suffix.lower() == ".pdf"), None)
        if pdf:
            extracted = friendly(extract_specification, pdf)
            if extracted:
                reqs, warnings, text = extracted
                state["requirements"] = [r.__dict__ for r in reqs]
                state["pdf_warnings"] = warnings
                state["pdf_text"] = text
        st.success("Arquivos copiados, hash SHA-256 registrado; os originais não foram alterados.")
        st.dataframe(pd.DataFrame(docs)[["name", "sha256", "duplicate"]], width="stretch")

elif page == "Revisão da importação":
    st.subheader("2. Revisão da importação")
    st.caption("Nenhum mapeamento é adivinhado: confirme aba, cabeçalho e exclusões de cada arquivo.")
    tab_process, tab_lab = st.tabs(["Parâmetros de processo", "Resultados laboratoriais"])
    with tab_process: review_panel("processo", "process")
    with tab_lab: review_panel("laboratório", "lab")

elif page == "Regras e hipóteses":
    st.subheader("3. Regras, requisitos e hipóteses")
    frame = state.get("process")
    if frame is None:
        st.warning("Confirme os dados de processo na tela **Revisão da importação** primeiro.")
    else:
        choices = [c for c in frame.columns if c != "_source_row"]
        st.markdown("#### Parâmetros de processo")
        selected = st.multiselect("Parâmetros numéricos (ajustáveis)", choices, default=state.get("sel_numeric", []))
        categories = st.multiselect("Parâmetros categóricos", [c for c in choices if c not in selected],
                                    default=state.get("sel_categorical", []))
        st.markdown("#### Separação de condições e sequência")
        conditions = st.multiselect("Colunas que separam condições incompatíveis (máquina, receita, ordem…)",
                                    [c for c in choices if c not in selected], default=state.get("sel_conditions", []))
        col1, col2 = st.columns(2)
        order_column = col1.selectbox("Coluna de ordem de fabricação", ["(nenhuma)"] + choices,
                                      index=0, key="order_col")
        time_column = col2.selectbox("Coluna temporal", ["(nenhuma)"] + choices, index=0, key="time_col")
        col3, col4, col5 = st.columns(3)
        qlow = col3.number_input("Quantil inferior", 0.0, 0.5, 0.10, 0.01)
        qhigh = col4.number_input("Quantil superior", 0.5, 1.0, 0.90, 0.01)
        gap = col5.number_input("Lacuna que separa blocos (min)", 5, 2880, 180, 5)
        unit = st.text_input("Unidade padrão dos numéricos", "não confirmada")
        precision = st.number_input("Precisão/incremento operacional (0 = sem arredondamento)", 0.0, 1000.0, 0.0, 0.1)

        if conditions:
            groups = partition_conditions(frame, conditions)
            st.caption("Condições encontradas (a receita usa a de maior número de registros):")
            st.dataframe(pd.DataFrame([{"condição": g["label"], "registros": g["records"]} for g in groups]),
                         width="stretch")

        if st.button("Salvar regras para a análise"):
            state["sel_numeric"], state["sel_categorical"], state["sel_conditions"] = selected, categories, conditions
            state["rules"] = ([ParameterRule(x, unit=unit, precision=precision or None).__dict__ for x in selected] +
                              [ParameterRule(x, kind="categorical", unit="categoria").__dict__ for x in categories])
            state["engine_config"] = {"qlow": qlow, "qhigh": qhigh, "max_gap_minutes": gap,
                                      "condition_columns": conditions,
                                      "order_column": None if order_column == "(nenhuma)" else order_column,
                                      "time_column": None if time_column == "(nenhuma)" else time_column}
            st.success("Regras salvas; nenhuma unidade, etapa ou equivalência foi inferida silenciosamente.")

    st.divider()
    st.markdown("#### Requisitos da especificação")
    for warning in state.get("pdf_warnings", []): st.warning(warning)
    extracted = state.get("requirements", [])
    if not extracted and state.get("pdf_text"):
        st.error("Nenhum requisito foi extraído automaticamente do PDF. Cadastre os requisitos manualmente abaixo — "
                 "nada é inferido do texto sem confirmação.")
    base = pd.DataFrame(extracted) if extracted else pd.DataFrame(
        [{"property": "", "stage": "não confirmada", "unit": "não confirmada",
          "minimum": None, "target": None, "maximum": None, "criterion": "manual", "source": "cadastro manual"}])
    edited = st.data_editor(base, num_rows="dynamic", width="stretch", key="req_editor",
                            column_config={"property": "Propriedade", "stage": "Etapa", "unit": "Unidade",
                                           "minimum": "Mínimo", "target": "Alvo", "maximum": "Máximo",
                                           "criterion": "Critério", "source": "Origem"})
    if st.button("Salvar requisitos"):
        rows = [r for r in edited.to_dict("records") if str(r.get("property") or "").strip()]
        state["requirements"] = rows
        st.success(f"{len(rows)} requisitos salvos. Limites unilaterais (só mínimo ou só máximo) são preservados.")

elif page == "Diagnóstico dos dados":
    st.subheader("4. Diagnóstico dos dados")
    if "process_meta" in state:
        st.markdown("**Processo**"); st.json(state["process_meta"])
    if "lab_meta" in state:
        st.markdown("**Laboratório**"); st.json(state["lab_meta"])
    if "process_meta" not in state and "lab_meta" not in state:
        st.warning("Confirme ao menos um arquivo na tela **Revisão da importação**.")

    lab, process = state.get("lab"), state.get("process")
    if lab is not None:
        st.markdown("#### Avaliação de qualidade por propriedade")
        requirements = state.get("requirements", [])
        if not requirements:
            st.warning("Cadastre os requisitos em **Regras e hipóteses** para avaliar conformidade.")
        else:
            lab_columns = ["(não mapeada)"] + [c for c in lab.columns if c != "_source_row"]
            st.caption("Ligue cada requisito à coluna correspondente do laboratório. Sem mapeamento confirmado o "
                       "resultado fica **inconclusivo** — ausência de teste nunca é aprovação.")
            objects = [Requirement(**{k: v for k, v in r.items() if k in Requirement.__dataclass_fields__})
                       for r in requirements]
            mapping = dict(state.get("quality_mapping", {}))
            for i, req in enumerate(objects):
                if req.kind != "numeric":
                    st.caption(f"{req.key}: qualitativo, avaliado fora do cálculo numérico."); continue
                current = mapping.get(req.key, "(não mapeada)")
                index = lab_columns.index(current) if current in lab_columns else 0
                mapping[req.key] = st.selectbox(f"{req.key} — {req.unit}", lab_columns, index=index, key=f"map_{i}")
            section = st.selectbox("Coluna de seção (opcional)", ["(nenhuma)"] + lab_columns[1:], key="sec_col")
            if st.button("Avaliar qualidade"):
                state["quality_mapping"] = {k: v for k, v in mapping.items() if v != "(não mapeada)"}
                state["quality"] = evaluate_quality_columns(
                    lab, objects, state["quality_mapping"],
                    section_column=None if section == "(nenhuma)" else section)
                st.success("Qualidade avaliada por propriedade, sem decisão de aprovação do lote.")
        if state.get("quality"):
            st.dataframe(pd.DataFrame(state["quality"]), width="stretch")
            st.info("Sem regra confirmada de aceitação por lote, o aplicativo não emite aprovação da produção.")

    if lab is not None and process is not None:
        st.markdown("#### Modo vinculado (opcional)")
        st.caption("Só habilite com uma chave de correspondência válida. Datas divergentes não criam vínculo.")
        c1, c2 = st.columns(2)
        pk = c1.selectbox("Chave no processo", ["(nenhuma)"] + list(process.columns), key="pk")
        lk = c2.selectbox("Chave no laboratório", ["(nenhuma)"] + list(lab.columns), key="lk")
        if st.button("Avaliar vínculo", disabled=pk == "(nenhuma)" or lk == "(nenhuma)"):
            result = friendly(link_records, process, lab, pk, lk)
            if result:
                st.json({"chaves vinculadas": len(result["keys_linked"]), "ambíguas": result["ambiguous"],
                         "processo sem correspondência": result["process_unmatched"],
                         "laboratório sem correspondência": result["lab_unmatched"],
                         "cobertura": round(result["coverage"], 3)})
                if not result["keys_linked"]:
                    st.warning("Nenhuma chave vinculada com segurança: o modo vinculado permanece indisponível.")

elif page == "Receita proposta":
    st.subheader("5. Receita exploratória")
    frame, raw_rules = state.get("process"), state.get("rules", [])
    if frame is None or not raw_rules:
        st.warning("Confirme dados de processo e regras primeiro.")
    elif st.button("Gerar proposta determinística"):
        config = dict(state.get("engine_config", {}))
        result = friendly(generate_exploratory_recipe, frame, [ParameterRule(**r) for r in raw_rules], **config)
        if result is not None:
            if state.get("alias"):
                result.assumptions.append("Alias explícito confirmado: KSEA8BR45 = KSEI8BR45")
            if state.get("demo"):
                result.assumptions.append("DADOS SINTÉTICOS DE DEMONSTRAÇÃO — não representam produção real")
            result.quality = state.get("quality", [])
            if not result.quality:
                result.pending.append("Qualidade não avaliada: requisitos ou mapeamento do laboratório ausentes")
            payload = result.to_dict()
            payload["versao_aplicativo"] = VERSION
            aid = repo.save_analysis(state.get("product", "sem produto"),
                                     {**config, "alias_confirmado": state.get("alias", False),
                                      "regras": raw_rules, "requisitos": state.get("requirements", []),
                                      "mapeamento_qualidade": state.get("quality_mapping", {}),
                                      "importacao_processo": state.get("process_meta", {}),
                                      "importacao_laboratorio": state.get("lab_meta", {}),
                                      "versao_aplicativo": VERSION},
                                     payload, [d["id"] for d in state.get("docs", [])])
            state["result"], state["analysis_id"] = payload, aid
            st.success(f"Análise salva: {aid}")
    if "result" in state:
        result = state["result"]
        st.markdown("**Configuração de referência (condição conjunta observada)**")
        reference = {k: v for k, v in result.get("reference", {}).items() if v is not None}
        st.json(reference, expanded=False)
        st.dataframe(pd.DataFrame(result["items"]), width="stretch")
        st.warning("Proposta preliminar. **Revisada pelo usuário** não significa **validada em produção**.")
        c1, c2, c3 = st.columns(3)
        with c1: st.markdown("**Evidências**"); st.write(result["evidence"])
        with c2: st.markdown("**Pendências**"); st.write(result["pending"] or ["nenhuma"])
        with c3: st.markdown("**Hipóteses**"); st.write(result["assumptions"])
        if result.get("quality"):
            st.markdown("**Qualidade**"); st.dataframe(pd.DataFrame(result["quality"]), width="stretch")

else:
    st.subheader("6. Histórico e exportação")
    analyses = repo.list_analyses()
    if not analyses:
        st.info("Nenhuma análise salva.")
    else:
        aid = st.selectbox("Análise", [a["id"] for a in analyses],
                           format_func=lambda x: next(a["product"] + " — " + a["created_at"] for a in analyses if a["id"] == x))
        versions = repo.list_versions(aid)
        chosen = st.selectbox("Versão", [v["version"] for v in versions],
                              format_func=lambda v: f"v{v} — " + next(x["justification"] for x in versions if x["version"] == v))
        result = repo.get_version(aid, chosen)
        st.caption("Receitas históricas são reabertas como foram salvas; nada é recalculado silenciosamente.")
        st.dataframe(pd.DataFrame(result.get("items", [])), width="stretch")
        if result.get("quality"):
            st.markdown("**Qualidade**"); st.dataframe(pd.DataFrame(result["quality"]), width="stretch")
        with st.expander("Configuração e hipóteses registradas"): st.json(repo.get_config(aid))

        meta = {"id": aid, "versão": chosen, "algoritmo": result.get("algorithm_version"),
                "aplicativo": result.get("versao_aplicativo", VERSION)}
        c1, c2 = st.columns(2)
        c1.download_button("Baixar Excel", excel_bytes(result, meta), f"receita-{aid[:8]}-v{chosen}.xlsx",
                           width="stretch")
        c2.download_button("Baixar PDF", pdf_bytes(result, meta), f"receita-{aid[:8]}-v{chosen}.pdf",
                           width="stretch")
        st.divider()
        justification = st.text_input("Justificativa da revisão manual")
        if st.button("Salvar nova versão revisada", disabled=not justification):
            st.success(f"Versão {repo.save_revision(aid, result, justification)} salva; não é validação em produção.")
        confirm = st.checkbox("Confirmo a exclusão desta análise e dos dados associados")
        if st.button("Excluir análise", disabled=not confirm):
            repo.delete_analysis(aid); st.success("Análise excluída; arquivos compartilhados foram preservados.")
