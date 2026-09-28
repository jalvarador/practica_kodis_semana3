"""Formato del resumen para consola (RF4).

Devuelve un str en lugar de imprimir directamente: así las pruebas pueden
comprobar el texto y el CLI decide dónde escribirlo.
El texto propio es ASCII (RNF4) y el contenido del log se sanea antes de mostrarse.
"""

from __future__ import annotations

from .resumen import Resumen

ANCHO = 64
_MAX_TEXTO = 60


def _porcentaje(parte: int, total: int) -> str:
    return f"{(parte / total * 100):5.1f}%" if total else "  0.0%"


def _fila(etiqueta: str, valor: int, total: int | None = None) -> str:
    pct = f"  ({_porcentaje(valor, total)})" if total is not None else ""
    return f"  {etiqueta:<38}{valor:>6}{pct}"


def _sanear(texto: str) -> str:
    """Escapa los caracteres de control (RNF4): una línea del log con "ESC[2J" no debe
    poder borrar la pantalla ni cambiar colores. Se muestra como "\\x1b[2J"."""
    return "".join(
        c if c.isprintable() else c.encode("unicode_escape").decode("ascii") for c in texto
    )


def _recortar(texto: str) -> str:
    # Se sanea antes de recortar para que el límite cuente lo que realmente se ve.
    texto = _sanear(texto.strip())
    return texto if len(texto) <= _MAX_TEXTO else texto[: _MAX_TEXTO - 3] + "..."


def formatear_reporte(resumen: Resumen, nombre_archivo: str, detalle: bool = True) -> str:
    total = resumen.total_eventos
    lineas = [
        "=" * ANCHO,
        " RESUMEN DE ANALISIS DE LOGS".center(ANCHO),
        "=" * ANCHO,
        f"  Archivo: {_sanear(nombre_archivo)}",
        "",
        _fila("Total de eventos", total),
    ]
    if resumen.lineas_vacias:
        lineas.append(_fila("Lineas vacias (ignoradas)", resumen.lineas_vacias))

    lineas += ["", "  Eventos por tipo", "  " + "-" * (ANCHO - 4)]
    for nivel in resumen.niveles_reporte:
        lineas.append(_fila(nivel, resumen.eventos_de(nivel), total))

    lineas += ["", "  Fecha", "  " + "-" * (ANCHO - 4)]
    lineas.append(_fila("Con fecha valida", resumen.con_fecha_valida, total))
    lineas.append(_fila("Sin fecha", resumen.sin_fecha, total))
    lineas.append(_fila("Con fecha u hora invalida", resumen.con_fecha_invalida, total))
    if resumen.fecha_no_evaluada:
        lineas.append(_fila("No evaluada (sin nivel reconocible)",
                            resumen.fecha_no_evaluada, total))

    lineas += ["", "  " + "-" * (ANCHO - 4)]
    lineas.append(_fila("Lineas mal formateadas o incompletas",
                        resumen.mal_formateadas_o_incompletas, total))
    lineas.append("=" * ANCHO)

    if total == 0:
        lineas += ["", "  El archivo no contiene eventos."]
    elif resumen.mal_formateadas_o_incompletas == 0:
        # Se decide por el conteo y no por `problemas`, que puede estar vacío por el
        # límite de detalle (--sin-detalle) aunque haya errores.
        lineas += ["", "  Todas las lineas estan bien formadas."]
    elif detalle and resumen.problemas:
        lineas += ["", "  Detalle de lineas con problemas", "  " + "-" * (ANCHO - 4)]
        for r in resumen.problemas:
            # Ancho 7: los números de línea de archivos de millones de líneas no descuadran.
            lineas.append(f"  L{r.numero:<7} {r.estado.value:<22} | {_recortar(r.texto)}")
        if resumen.problemas_omitidos:
            lineas.append(f"  ... y {resumen.problemas_omitidos} lineas mas "
                          "(use --max-detalle 0 para verlas todas)")

    return "\n".join(lineas)
