from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = collect_all('streamlit')
datas += [('src', 'src'), ('fixtures', 'fixtures')]
a = Analysis(['src/receita_local/launcher/main.py'], pathex=['src'], binaries=binaries, datas=datas,
             hiddenimports=hiddenimports + ['openpyxl','pdfplumber','reportlab'], excludes=['tkinter'])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='ReceitaLocal', console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='ReceitaLocal')
