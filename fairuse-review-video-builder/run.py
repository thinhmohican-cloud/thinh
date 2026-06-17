"""Launcher for Streamlit UI."""
from __future__ import annotations
import subprocess, sys
if __name__ == "__main__":
    subprocess.run([sys.executable, "-m", "streamlit", "run", "app/ui.py"], check=True)
