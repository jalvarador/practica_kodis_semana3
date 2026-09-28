"""Análisis de una línea de log (RF2).

Formato esperado (ver specs/01_spec.md, sección 2):

    [NIVEL] AAAA-MM-DD [HH:MM:SS] Mensaje

Este módulo no toca archivos ni consola: recibe un texto y devuelve un
ResultadoLinea. Así se puede probar cada criterio de aceptación de forma aislada.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

NIVELES_VALIDOS = ("INFO", "WARNING", "ERROR")
NIVEL_DESCONOCIDO = "DESCONOCIDO"

# Viñetas que aparecen en los ejemplos del enunciado ("· [INFO] ...").
_VINETAS = "·•-* \t"

# La etiqueta es "lo que haya entre los primeros corchetes". Se captura cualquier
# contenido (incluso vacío) para poder distinguir "[DEBUG]" (nivel desconocido)
# de una línea que ni siquiera tiene corchetes (sin nivel).
_RE_ETIQUETA = re.compile(r"^\[(?P<etiqueta>[^\]]*)\]\s*(?P<resto>.*)$")

# Decisión D3: un token "parece una fecha" si tiene la forma número-sep-número-sep-número.
# Exigir DOS separadores evita confundir un mensaje como "3.5 segundos" con una fecha rota,
# y el lookahead final (?![-/.]\d) evita confundir una IP como "10.0.0.1" (cuatro grupos).
_RE_PARECE_FECHA = re.compile(r"^\d{1,4}[-/.]\d{1,2}[-/.]\d{1,4}(?![-/.]\d)")
_RE_PARECE_HORA = re.compile(r"^\d{1,2}:\d{1,2}")

# Decisión D2: la regex solo comprueba la FORMA exacta (AAAA-MM-DD con ceros).
# Si el día/mes existe lo decide datetime.strptime, porque una regex sola
# aceptaría "2025-13-45" o "2025-02-30".
_RE_FECHA_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_RE_HORA_ISO = re.compile(r"^\d{2}:\d{2}:\d{2}$")


class Estado(Enum):
    """Estados mutuamente excluyentes de una línea (spec, sección 3)."""

    VALIDA = "Valida"
    SIN_FECHA = "Sin fecha"
    FECHA_INVALIDA = "Fecha u hora invalida"
    SIN_MENSAJE = "Sin mensaje"
    NIVEL_DESCONOCIDO = "Nivel desconocido"
    SIN_NIVEL = "Sin nivel"

    @property
    def es_problema(self) -> bool:
        """True si la línea cuenta como mal formateada o incompleta (D4)."""
        return self is not Estado.VALIDA


@dataclass(frozen=True)
class ResultadoLinea:
    numero: int
    texto: str
    nivel: str
    estado: Estado
    fecha: datetime | None = None
    mensaje: str = ""


def _validar_fecha(token: str) -> datetime | None:
    """Devuelve la fecha si el token es AAAA-MM-DD y existe en el calendario."""
    if not _RE_FECHA_ISO.match(token):
        return None
    try:
        return datetime.strptime(token, "%Y-%m-%d")
    except ValueError:
        return None


def _validar_hora(token: str) -> datetime | None:
    if not _RE_HORA_ISO.match(token):
        return None
    try:
        return datetime.strptime(token, "%H:%M:%S")
    except ValueError:
        return None


def es_linea_vacia(texto: str) -> bool:
    return not texto.strip()


def analizar_linea(texto: str, numero: int = 0) -> ResultadoLinea:
    """Clasifica una línea no vacía. Orden de evaluación: nivel -> fecha/hora -> mensaje."""
    original = texto.rstrip("\r\n")
    limpio = original.strip().lstrip(_VINETAS)

    # 1) Nivel ---------------------------------------------------------------
    coincidencia = _RE_ETIQUETA.match(limpio)
    if coincidencia is None:
        return ResultadoLinea(numero, original, NIVEL_DESCONOCIDO, Estado.SIN_NIVEL,
                              mensaje=limpio)

    # Se acepta "[info]" o "[Info]": el nivel se normaliza a mayúsculas.
    nivel = coincidencia["etiqueta"].strip().upper()
    resto = coincidencia["resto"].strip()
    if nivel not in NIVELES_VALIDOS:
        return ResultadoLinea(numero, original, NIVEL_DESCONOCIDO,
                              Estado.NIVEL_DESCONOCIDO, mensaje=resto)

    # 2) Fecha (y hora opcional) ----------------------------------------------
    tokens = resto.split(maxsplit=1)
    primero = tokens[0] if tokens else ""

    if not _RE_PARECE_FECHA.match(primero):
        # No hay nada con forma de fecha: todo el resto es el mensaje.
        estado = Estado.SIN_FECHA if resto else Estado.SIN_MENSAJE
        return ResultadoLinea(numero, original, nivel, estado, mensaje=resto)

    fecha = _validar_fecha(primero)
    if fecha is None:
        return ResultadoLinea(numero, original, nivel, Estado.FECHA_INVALIDA,
                              mensaje=tokens[1] if len(tokens) > 1 else "")

    resto = tokens[1] if len(tokens) > 1 else ""
    tokens = resto.split(maxsplit=1)
    if tokens and _RE_PARECE_HORA.match(tokens[0]):
        hora = _validar_hora(tokens[0])
        if hora is None:
            return ResultadoLinea(numero, original, nivel, Estado.FECHA_INVALIDA,
                                  fecha=None, mensaje=tokens[1] if len(tokens) > 1 else "")
        fecha = fecha.replace(hour=hora.hour, minute=hora.minute, second=hora.second)
        resto = tokens[1] if len(tokens) > 1 else ""

    # 3) Mensaje --------------------------------------------------------------
    if not resto:
        return ResultadoLinea(numero, original, nivel, Estado.SIN_MENSAJE, fecha=fecha)

    return ResultadoLinea(numero, original, nivel, Estado.VALIDA, fecha=fecha, mensaje=resto)
