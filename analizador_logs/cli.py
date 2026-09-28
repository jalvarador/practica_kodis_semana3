"""Interfaz de línea de comandos (RF1, RNF2, RNF3).

Uso:
    python analizar_logs.py ruta/al/archivo.log
    python analizar_logs.py                  # pide la ruta por teclado
    python analizar_logs.py --gui            # abre un selector de archivos
    python analizar_logs.py archivo.log --sin-detalle
    python analizar_logs.py archivo.log --max-detalle 0   # todas las líneas con problemas
"""

from __future__ import annotations

import argparse
import codecs
import os
import sys
from pathlib import Path
from typing import Iterator

from .parser import analizar_linea, es_linea_vacia
from .reporte import formatear_reporte
from .resumen import LIMITE_DETALLE, Resumen

# Bytes que se inspeccionan para decidir si el archivo es binario (mismo criterio que git/grep).
_BYTES_MUESTRA = 8192


class ErrorArchivo(Exception):
    """Error de entrada que se muestra al usuario sin traza."""


def _entero_no_negativo(valor: str) -> int:
    n = int(valor)
    if n < 0:
        raise argparse.ArgumentTypeError("debe ser 0 o mayor")
    return n


def _crear_parser_args() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="analizar_logs",
        description="Analiza un archivo de logs y muestra un resumen por consola.",
    )
    p.add_argument("archivo", nargs="?", help="ruta del archivo de logs a analizar")
    p.add_argument("--gui", action="store_true",
                   help="elegir el archivo con una ventana de seleccion")
    p.add_argument("--sin-detalle", action="store_true",
                   help="no listar las lineas con problemas")
    p.add_argument("--max-detalle", type=_entero_no_negativo, default=LIMITE_DETALLE,
                   metavar="N",
                   help=f"maximo de lineas con problemas a listar (defecto {LIMITE_DETALLE}; "
                        "0 = todas)")
    return p


def _elegir_con_gui() -> str | None:
    # D7: import local; si tkinter no está disponible el modo consola sigue funcionando.
    try:
        import tkinter as tk
        from tkinter import filedialog
    except ImportError:
        print("tkinter no esta disponible; indique la ruta por teclado.", file=sys.stderr)
        return None
    try:
        raiz = tk.Tk()
    except tk.TclError:
        # tkinter instalado pero sin entorno gráfico (servidor, SSH, contenedor).
        print("No hay entorno grafico; indique la ruta por teclado.", file=sys.stderr)
        return None
    raiz.withdraw()
    ruta = filedialog.askopenfilename(
        title="Seleccione el archivo de logs",
        filetypes=[("Logs y texto", "*.log *.txt"), ("Todos los archivos", "*.*")],
    )
    raiz.destroy()
    return ruta or None


def obtener_ruta(args: argparse.Namespace) -> Path:
    """RF1: argumento > selector gráfico > pregunta por teclado."""
    ruta = args.archivo
    if ruta is None and args.gui:
        ruta = _elegir_con_gui()
    if ruta is None:
        try:
            ruta = input("Ruta del archivo de logs: ")
        except EOFError:  # entrada cerrada (p. ej. ejecutado sin terminal)
            ruta = ""
    # Quitar comillas: al arrastrar un archivo a la consola de Windows se pegan con ellas.
    ruta = ruta.strip().strip('"').strip("'")
    if not ruta:
        raise ErrorArchivo("No se indico ningun archivo.")
    return Path(ruta).expanduser()


def _elegir_codificacion(ruta: Path) -> str:
    """D6: decide la codificación mirando el BOM y, si no hay, probando UTF-8."""
    with ruta.open("rb") as f:
        muestra = f.read(_BYTES_MUESTRA)

    # UTF-16 con BOM: lo que escribe `>` en PowerShell 5.1 y "Unicode" en el Bloc de notas.
    # Hay que comprobarlo antes que los nulos: en UTF-16 casi un byte de cada dos es 0.
    if muestra.startswith((codecs.BOM_UTF16_LE, codecs.BOM_UTF16_BE)):
        return "utf-16"
    if b"\x00" in muestra:
        raise ErrorArchivo(f"El archivo no parece un archivo de texto: {ruta}")

    # Se valida la decodificación completa antes de analizar nada, para no contar dos
    # veces las líneas si hubiera que reintentar. latin-1 nunca falla: es el respaldo.
    try:
        with ruta.open(encoding="utf-8-sig") as f:
            for _ in f:
                pass
        return "utf-8-sig"
    except UnicodeDecodeError:
        return "latin-1"


def _leer_lineas(ruta: Path) -> Iterator[str]:
    """RNF3: lee línea a línea en vez de cargar todo el archivo."""
    codificacion = _elegir_codificacion(ruta)
    try:
        with ruta.open(encoding=codificacion) as f:
            yield from f
    except UnicodeError as e:  # p. ej. UTF-16 con un número impar de bytes (truncado)
        raise ErrorArchivo(f"No se pudo decodificar el archivo como {codificacion}: {ruta}") from e


def analizar_archivo(ruta: Path, limite_detalle: int | None = LIMITE_DETALLE) -> Resumen:
    if not ruta.exists():
        raise ErrorArchivo(f"El archivo no existe: {ruta}")
    if not ruta.is_file():
        raise ErrorArchivo(f"La ruta no es un archivo: {ruta}")

    resumen = Resumen(limite_detalle=limite_detalle)
    try:
        for numero, linea in enumerate(_leer_lineas(ruta), start=1):
            if es_linea_vacia(linea):
                resumen.agregar_vacia()
            else:
                resumen.agregar(analizar_linea(linea, numero))
    except PermissionError as e:
        raise ErrorArchivo(f"Sin permiso para leer el archivo: {ruta}") from e
    return resumen


def _imprimir(texto: str) -> bool:
    """Escribe en stdout. Devuelve False si el receptor cerró la tubería (`| head`)."""
    try:
        print(texto)
        sys.stdout.flush()
        return True
    except (BrokenPipeError, OSError):
        # En Windows una tubería cerrada da OSError(EINVAL) en vez de BrokenPipeError.
        # Se redirige stdout a devnull para que Python no vuelva a fallar al cerrar
        # (receta de la documentación oficial, módulo `signal`, sección "SIGPIPE").
        try:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
        except (OSError, ValueError, AttributeError):
            pass
        return False


def main(argv: list[str] | None = None) -> int:
    """D8: devuelve el código de salida en vez de llamar a sys.exit (facilita las pruebas)."""
    # El texto propio es ASCII (RNF4), pero el contenido del log o la ruta pueden no
    # serlo: se reemplazan los caracteres no representables en vez de lanzar
    # UnicodeEncodeError.
    for flujo in (sys.stdout, sys.stderr):
        if hasattr(flujo, "reconfigure"):
            flujo.reconfigure(errors="replace")

    args = _crear_parser_args().parse_args(argv)
    if args.sin_detalle:
        limite = 0
    else:
        limite = None if args.max_detalle == 0 else args.max_detalle

    try:
        ruta = obtener_ruta(args)
        resumen = analizar_archivo(ruta, limite)
    except ErrorArchivo as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        # 130 = 128 + SIGINT, la convención de los shells para "cancelado con Ctrl+C".
        print("\nAnalisis cancelado.", file=sys.stderr)
        return 130

    reporte = formatear_reporte(resumen, str(ruta), detalle=not args.sin_detalle)
    return 0 if _imprimir(reporte) else 1
