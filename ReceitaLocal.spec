# Empacotamento onedir para Windows 10/11 x64.
import sys

sys.path.insert(0, "src")

from PyInstaller.utils.hooks import collect_all, collect_submodules

datas, binaries, hiddenimports = collect_all("streamlit")
datas += [("src", "src"), ("fixtures", "fixtures")]

# O launcher importa apenas receita_local.storage; o resto da aplicação é
# carregado pelo Streamlit ao executar app.py. Sem declarar os submódulos aqui, o
# pacote levava um receita_local incompleto que sombreava a cópia em _internal/src
# e derrubava a interface com ModuleNotFoundError.
hiddenimports += collect_submodules("receita_local")
hiddenimports += ["openpyxl", "pdfplumber", "reportlab"]

a = Analysis(["src/receita_local/launcher/main.py"], pathex=["src"], binaries=binaries,
             datas=datas, hiddenimports=hiddenimports, excludes=["tkinter"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="ReceitaLocal", console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="ReceitaLocal")
