"""Verifica que a interface realmente funciona, não apenas que o servidor responde.

Uma resposta 200 em `/` prova que o Streamlit serviu o esqueleto da página. Não
prova que a aplicação carrega, que o motor roda nem que a receita aparece. Este
script abre a aplicação em um navegador real e percorre o fluxo mínimo do MVP,
usando somente o modo demonstração sintético.
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def verificar(url: str, capturas: Path) -> None:
    from playwright.sync_api import sync_playwright

    capturas.mkdir(parents=True, exist_ok=True)
    executavel = os.environ.get("CHROMIUM_EXECUTAVEL")
    with sync_playwright() as p:
        navegador = p.chromium.launch(**({"executable_path": executavel} if executavel else {}))
        pagina = navegador.new_page(viewport={"width": 1440, "height": 1000})
        erros: list[str] = []
        pagina.on("pageerror", lambda e: erros.append(str(e)))
        try:
            pagina.goto(url, wait_until="networkidle", timeout=90000)

            # 1. A aplicação carregou de fato (título renderizado pelo front-end).
            pagina.wait_for_selector("text=Receita Local", timeout=60000)
            print("  [ok] a interface carregou")

            # 2. As sete telas estão disponíveis. Espera em vez de contar na hora:
            # a barra lateral do Streamlit termina de montar depois do título.
            for tela in ("Produtos e análises", "Nova análise", "Revisão da importação",
                         "Regras e hipóteses", "Diagnóstico dos dados", "Receita proposta",
                         "Histórico e exportação"):
                pagina.wait_for_selector(f"text={tela}", state="attached", timeout=30000)
            print("  [ok] as sete telas estão na navegação")

            # 3. Modo demonstração sintético.
            pagina.get_by_text("Nova análise", exact=True).first.click()
            pagina.wait_for_timeout(1500)
            pagina.get_by_role("button", name="Carregar demonstração sintética (sem arquivos reais)").click()
            pagina.wait_for_selector("text=não representa dados industriais reais", timeout=30000)
            print("  [ok] demonstração sintética carregada")

            # 4. O motor roda e a receita aparece na tela.
            pagina.get_by_text("Receita proposta", exact=True).first.click()
            pagina.wait_for_timeout(1500)
            pagina.get_by_role("button", name="Gerar proposta determinística").click()
            pagina.wait_for_selector("text=Análise salva", timeout=60000)
            # A tabela do Streamlit desenha em canvas: os cabeçalhos existem no DOM
            # para acessibilidade, mas não contam como visíveis.
            for esperado in ("Parâmetro", "Limite inferior", "Limite superior", "temperatura"):
                pagina.wait_for_selector(f"text={esperado}", state="attached", timeout=30000)
            print("  [ok] receita gerada e exibida com rótulos em português")

            # 5. O histórico reabre a análise salva.
            pagina.get_by_text("Histórico e exportação", exact=True).first.click()
            pagina.wait_for_selector("text=Baixar Excel", state="attached", timeout=30000)
            pagina.wait_for_selector("text=Baixar PDF", state="attached", timeout=30000)
            print("  [ok] histórico e exportações disponíveis")

            if erros:
                raise AssertionError("erros de JavaScript na página: " + "; ".join(erros[:3]))
            pagina.screenshot(path=str(capturas / "verificacao-ok.png"), full_page=True)
        except Exception:
            pagina.screenshot(path=str(capturas / "verificacao-falhou.png"), full_page=True)
            print(f"  conteúdo visível: {pagina.inner_text('body')[:400]!r}", file=sys.stderr)
            raise
        finally:
            navegador.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True)
    parser.add_argument("--capturas", default="capturas-verificacao")
    args = parser.parse_args()
    verificar(args.url.rstrip("/"), Path(args.capturas))
    print("Interface verificada com sucesso.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
