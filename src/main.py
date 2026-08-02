"""Punto de entrada principal para el Extractor de Comprobantes."""

import subprocess
import sys
from pathlib import Path


def run_app():
    """Ejecuta la interfaz de Streamlit."""
    app_path = Path(__file__).parent / "ui" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app_path)], check=False)



if __name__ == "__main__":
    run_app()
