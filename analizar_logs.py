"""Punto de entrada del analizador de logs.

Uso: python analizar_logs.py [archivo] [--gui] [--sin-detalle]
"""

import sys

from analizador_logs.cli import main

if __name__ == "__main__":
    sys.exit(main())
