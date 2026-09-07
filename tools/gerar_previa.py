"""Gera uma prévia estática da interface a partir da aplicação real.

As telas são capturadas do Streamlit em execução, usando **exclusivamente o modo
demonstração sintético**. Nenhum arquivo de produção é aberto, e o script recusa
prosseguir se encontrar sinal de dado real, porque a prévia é publicada em uma
página pública.
"""
from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
TELAS = [
    ("produtos", "Produtos e análises", "Lista de análises já realizadas, com o alias do produto."),
    ("nova-analise", "Nova análise", "Seleção dos três arquivos e carga da demonstração sintética."),
    ("revisao", "Revisão da importação", "Aba, linha de cabeçalho, registros aceitos e motivo de cada exclusão."),
    ("regras", "Regras e hipóteses", "Parâmetros, separação de condições e requisitos lidos da especificação."),
    ("diagnostico", "Diagnóstico dos dados", "Qualidade por propriedade e modo vinculado."),
    ("receita", "Receita proposta", "Faixas, evidências e pendências da proposta exploratória."),
    ("historico", "Histórico e exportação", "Versões preservadas e exportação em Excel e PDF."),
]


def porta_livre() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0)); return s.getsockname()[1]


def aguardar(url: str, tentativas: int = 120) -> None:
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    for _ in range(tentativas):
        try:
            opener.open(f"{url}/_stcore/health", timeout=1); return
        except Exception:
            time.sleep(1)
    raise RuntimeError("A aplicação não respondeu para a captura da prévia.")


ARQUIVOS_PROIBIDOS = ("Claude.zip", "KSEA8BR45*.xlsx", "KSEA8BR45*.pdf", "*DADOS FTP*")


def recusar_dados_reais() -> None:
    """A prévia vai para uma página pública: nada de produção pode estar presente."""
    encontrados = [str(a.relative_to(RAIZ)) for padrao in ARQUIVOS_PROIBIDOS for a in RAIZ.glob(padrao)]
    if encontrados:
        raise SystemExit("Prévia abortada: arquivos de produção presentes na árvore -> "
                         + ", ".join(sorted(encontrados)))


def capturar(destino: Path) -> list[tuple[str, str, str]]:
    from playwright.sync_api import sync_playwright

    destino.mkdir(parents=True, exist_ok=True)
    dados = Path(tempfile.mkdtemp(prefix="previa_"))
    porta = porta_livre()
    ambiente = {**os.environ, "XDG_DATA_HOME": str(dados), "LOCALAPPDATA": str(dados),
                "STREAMLIT_GLOBAL_DEVELOPMENT_MODE": "false", "STREAMLIT_SERVER_HEADLESS": "true",
                "STREAMLIT_BROWSER_GATHER_USAGE_STATS": "false",
                "STREAMLIT_CLIENT_TOOLBAR_MODE": "minimal",
                "PYTHONPATH": str(RAIZ / "src")}
    processo = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(RAIZ / "src/receita_local/ui/app.py"),
         "--server.address", "127.0.0.1", "--server.port", str(porta),
         "--server.headless", "true", "--browser.gatherUsageStats", "false"],
        env=ambiente, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    url = f"http://127.0.0.1:{porta}"
    capturadas = []
    try:
        aguardar(url)
        with sync_playwright() as p:
            # Em ambientes com o Chromium pré-instalado fora da árvore do Playwright,
            # aponta para o binário existente em vez de baixar outro.
            executavel = os.environ.get("CHROMIUM_EXECUTAVEL")
            opcoes = {"executable_path": executavel} if executavel else {}
            navegador = p.chromium.launch(**opcoes)
            pagina = navegador.new_page(viewport={"width": 1440, "height": 1000}, device_scale_factor=2)
            pagina.goto(url, wait_until="networkidle")
            pagina.wait_for_selector("text=Receita Local", timeout=60000)

            # Carrega apenas a demonstração sintética.
            pagina.get_by_text("Nova análise", exact=True).first.click()
            pagina.wait_for_timeout(1500)
            pagina.get_by_role("button", name="Carregar demonstração sintética (sem arquivos reais)").click()
            pagina.wait_for_timeout(2500)

            for chave, rotulo, _descricao in TELAS:
                pagina.get_by_text(rotulo, exact=True).first.click()
                pagina.wait_for_timeout(1800)
                if chave == "receita":
                    botao = pagina.get_by_role("button", name="Gerar proposta determinística")
                    if botao.count():
                        botao.first.click(); pagina.wait_for_timeout(3000)
                arquivo = destino / f"{chave}.png"
                pagina.screenshot(path=str(arquivo), full_page=True)
                capturadas.append((chave, rotulo, _descricao))
                print(f"  capturada: {rotulo} -> {arquivo.name} ({arquivo.stat().st_size // 1024} KB)")
            navegador.close()
    finally:
        processo.terminate()
        try: processo.wait(timeout=15)
        except subprocess.TimeoutExpired: processo.kill()
        shutil.rmtree(dados, ignore_errors=True)
    return capturadas


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--destino", default="site")
    parser.add_argument("--versao", default="desenvolvimento")
    args = parser.parse_args()
    recusar_dados_reais()
    destino = Path(args.destino)
    telas = capturar(destino / "telas")
    (destino / "index.html").write_text(pagina_html(telas, args.versao), encoding="utf-8")
    print(f"Prévia gerada em {destino}/index.html")
    return 0


def pagina_html(telas: list[tuple[str, str, str]], versao: str) -> str:
    from html import escape
    cartoes = "\n".join(
        f'''    <figure class="tela">
      <a href="telas/{chave}.png"><img src="telas/{chave}.png" alt="{escape(rotulo)}" loading="lazy"></a>
      <figcaption><strong>{escape(rotulo)}</strong><span>{escape(descricao)}</span></figcaption>
    </figure>''' for chave, rotulo, descricao in telas)
    return PAGINA.replace("{{CARTOES}}", cartoes).replace("{{VERSAO}}", escape(versao))


PAGINA = """<!doctype html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="robots" content="noindex">
<title>Receita Local — prévia da interface</title>
<style>
  :root { color-scheme: light dark; --fundo:#fbfaf9; --texto:#1c1b19; --suave:#5f5c57;
          --borda:#e2ded8; --cartao:#fff; --destaque:#8a5a2b; }
  @media (prefers-color-scheme: dark) {
    :root { --fundo:#16150f; --texto:#efece6; --suave:#a8a49c; --borda:#2e2b25; --cartao:#1d1b16; --destaque:#d9a066; }
  }
  * { box-sizing: border-box; }
  body { margin:0; background:var(--fundo); color:var(--texto); font:16px/1.6 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  .envelope { max-width:1180px; margin:0 auto; padding:48px 24px 80px; }
  h1 { font-size:2rem; margin:0 0 8px; letter-spacing:-.02em; }
  .sub { color:var(--suave); margin:0 0 28px; max-width:62ch; }
  .aviso { border:1px solid var(--borda); border-left:4px solid var(--destaque); background:var(--cartao);
           padding:16px 20px; border-radius:8px; margin-bottom:40px; }
  .aviso strong { color:var(--destaque); }
  .grade { display:grid; gap:40px; }
  .tela { margin:0; background:var(--cartao); border:1px solid var(--borda); border-radius:12px; overflow:hidden; }
  .tela img { display:block; width:100%; height:auto; border-bottom:1px solid var(--borda); }
  figcaption { padding:16px 20px; display:flex; flex-direction:column; gap:4px; }
  figcaption span { color:var(--suave); font-size:.92rem; }
  footer { margin-top:56px; padding-top:24px; border-top:1px solid var(--borda); color:var(--suave); font-size:.9rem; }
  code { background:var(--fundo); padding:2px 6px; border-radius:4px; font-size:.88em; }
</style>
</head>
<body>
<div class="envelope">
  <h1>Receita Local — prévia da interface</h1>
  <p class="sub">Telas capturadas da aplicação em execução, para ver a cara do programa sem instalar nada.
  A aplicação de verdade roda no computador do usuário e abre em <code>http://127.0.0.1:8531</code>.</p>

  <div class="aviso">
    <strong>Somente dados sintéticos.</strong> Todas as capturas usam o modo demonstração do aplicativo.
    Nenhum arquivo de produção, resultado laboratorial ou especificação real aparece aqui.
    Esta página é uma prévia visual: não processa arquivos e não substitui o aplicativo.
  </div>

  <div class="grade">
{{CARTOES}}
  </div>

  <footer>Gerado automaticamente a partir da versão {{VERSAO}}.</footer>
</div>
</body>
</html>
"""


if __name__ == "__main__":
    raise SystemExit(main())
