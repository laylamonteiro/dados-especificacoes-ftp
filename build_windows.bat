@echo off
setlocal
py -3.12 -m venv .venv-build || exit /b 1
call .venv-build\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements-dev.txt || exit /b 1
pytest || exit /b 1
pyinstaller --noconfirm --clean ReceitaLocal.spec || exit /b 1
copy docs\GUIA_WINDOWS.md dist\ReceitaLocal\LEIA-ME.txt
echo 0.1.0>dist\ReceitaLocal\VERSAO.txt
powershell -NoProfile -Command "Compress-Archive -Path dist\ReceitaLocal -DestinationPath dist\ReceitaLocal-0.1.0-win-x64.zip -Force"
echo Pacote criado em dist\ReceitaLocal-0.1.0-win-x64.zip
