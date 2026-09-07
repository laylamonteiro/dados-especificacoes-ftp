from __future__ import annotations

import os, socket, subprocess, sys, time, urllib.request, webbrowser
from pathlib import Path

from receita_local.storage.repository import data_dir


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0)); return sock.getsockname()[1]


def run_streamlit_child(app: Path, port: int) -> int:
    """Executa Streamlit dentro do binário PyInstaller sem iniciar outro serviço externo."""
    # Executável empacotado com console=False pode não ter stdout/stderr; sem isso
    # qualquer print do Streamlit derruba o processo filho em silêncio.
    if sys.stdout is None or sys.stderr is None:
        sink = open(data_dir() / "logs" / "streamlit.log", "a", encoding="utf-8", buffering=1)
        if sys.stdout is None: sys.stdout = sink
        if sys.stderr is None: sys.stderr = sink
    from streamlit.web import bootstrap

    bootstrap.run(str(app), False, [], {
        "server.address": "127.0.0.1",
        "server.port": port,
        "server.headless": True,
        "browser.gatherUsageStats": False,
    })
    return 0


def show_error(message: str) -> None:
    """Mostra o erro mesmo quando o executável foi empacotado sem console."""
    sys.stderr.write(f"{message}\n")
    if sys.platform == "win32":
        safe = message.replace("'", "''")
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Add-Type -AssemblyName PresentationFramework; "
                        f"[System.Windows.MessageBox]::Show('{safe}','Receita Local')"], check=False)


def publish_address(root: Path, port: int) -> Path:
    """Deixa o endereço em disco: se o navegador abrir a aba errada ou não abrir,
    o usuário tem onde encontrar a URL sem depender de terminal."""
    marker = root / "ENDERECO_DO_APLICATIVO.txt"
    marker.write_text(
        f"http://127.0.0.1:{port}\n\n"
        "Cole este endereço no navegador se a aplicação não abrir sozinha.\n"
        "Ele vale apenas enquanto o ReceitaLocal.exe estiver aberto e só funciona neste computador.\n",
        encoding="utf-8")
    return marker


def main() -> int:
    root = data_dir()
    logs = root / "logs"
    logs.mkdir(parents=True, exist_ok=True)
    lock, stop = root / "application.lock", root / "stop.request"
    address = root / "ENDERECO_DO_APLICATIVO.txt"
    if lock.exists():
        try:
            pid, port = lock.read_text().split(":")
            urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=1)
            publish_address(root, int(port))
            webbrowser.open(f"http://127.0.0.1:{port}"); return 0
        except Exception: lock.unlink(missing_ok=True)
    configured_port = os.environ.get("RECEITA_FIXED_PORT")
    port = int(configured_port) if configured_port else free_port()
    stop.unlink(missing_ok=True); lock.write_text(f"{os.getpid()}:{port}")
    os.environ.update(STREAMLIT_BROWSER_GATHER_USAGE_STATS="false", RECEITA_STOP_FILE=str(stop))
    bundle = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    app = bundle / "src/receita_local/ui/app.py"
    if getattr(sys, "frozen", False):
        cmd = [sys.executable, "--streamlit-child", str(app), str(port)]
    else:
        cmd = [sys.executable, "-m", "streamlit", "run", str(app), "--server.address", "127.0.0.1", "--server.port", str(port), "--server.headless", "true", "--browser.gatherUsageStats", "false"]
    log = open(logs / "launcher.log", "a", encoding="utf-8")
    process = subprocess.Popen(cmd, stdout=log, stderr=log)
    try:
        for _ in range(120):
            if process.poll() is not None: raise RuntimeError("O servidor encerrou durante a inicialização. Consulte logs/launcher.log.")
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{port}/_stcore/health", timeout=.5); break
            except Exception: time.sleep(.25)
        else: raise RuntimeError("Tempo esgotado ao iniciar a interface.")
        publish_address(root, port)
        log.write(f"Aplicação disponível em http://127.0.0.1:{port}\n"); log.flush()
        if os.environ.get("RECEITA_NO_BROWSER") != "1":
            webbrowser.open(f"http://127.0.0.1:{port}")
        while process.poll() is None and not stop.exists(): time.sleep(.5)
        if process.poll() is None: process.terminate(); process.wait(timeout=10)
        return 0
    except Exception as exc:
        log.write(f"Falha de inicialização: {exc}\n"); log.flush()
        show_error(f"{exc}\n\nDetalhes em: {logs / 'launcher.log'}")
        return 1
    finally:
        lock.unlink(missing_ok=True); stop.unlink(missing_ok=True)
        address.unlink(missing_ok=True)   # endereço vencido confunde mais do que ajuda
        log.close()


if __name__ == "__main__":
    if len(sys.argv) == 4 and sys.argv[1] == "--streamlit-child":
        (data_dir() / "logs").mkdir(parents=True, exist_ok=True)
        raise SystemExit(run_streamlit_child(Path(sys.argv[2]), int(sys.argv[3])))
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException as exc:  # nenhuma falha pode encerrar o executável em silêncio
        show_error(f"Falha inesperada ao iniciar: {exc}")
        raise SystemExit(1)
