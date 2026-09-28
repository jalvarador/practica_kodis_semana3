"""Permite ejecutar: python -m analizador_logs [archivo]."""

import sys

from .cli import main

sys.exit(main())
