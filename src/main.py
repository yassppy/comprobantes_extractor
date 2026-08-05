"""Punto de entrada principal para el Extractor de Comprobantes."""

import asyncio
import subprocess
import sys
from pathlib import Path

# Fix: en Windows con Python 3.13, el ProactorEventLoop lanza ConnectionResetError
# al cerrar conexiones del navegador. SelectorEventLoop evita ese ruido.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


def run_app():
    """Ejecuta la interfaz de Streamlit."""
    app_path = Path(__file__).parent / "ui" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False)


if __name__ == "__main__":
    run_app()
