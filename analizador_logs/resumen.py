"""Acumulación de resultados para el resumen (RF3)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .parser import NIVEL_DESCONOCIDO, NIVELES_VALIDOS, Estado, ResultadoLinea

LIMITE_DETALLE = 50

_SIN_NIVEL_RECONOCIBLE = (Estado.SIN_NIVEL, Estado.NIVEL_DESCONOCIDO)


@dataclass
class Resumen:
    """Se alimenta de un resultado cada vez (D5). No guarda el archivo completo: solo
    contadores y, como mucho, `limite_detalle` líneas problemáticas para mostrarlas
    (RNF3). `None` = sin límite; `0` = no guardar ninguna."""

    limite_detalle: int | None = LIMITE_DETALLE
    total_eventos: int = 0
    lineas_vacias: int = 0
    por_nivel: Counter = field(default_factory=Counter)
    por_estado: Counter = field(default_factory=Counter)
    por_fecha: Counter = field(default_factory=Counter)
    problemas: list[ResultadoLinea] = field(default_factory=list)

    def agregar(self, resultado: ResultadoLinea) -> None:
        self.total_eventos += 1
        self.por_nivel[resultado.nivel] += 1
        self.por_estado[resultado.estado] += 1
        self.por_fecha[self._categoria_fecha(resultado)] += 1
        if resultado.estado.es_problema and (
            self.limite_detalle is None or len(self.problemas) < self.limite_detalle
        ):
            self.problemas.append(resultado)

    def agregar_vacia(self) -> None:
        # Las líneas vacías no son eventos (spec, sección 3), pero se cuentan
        # aparte para que el usuario sepa que se ignoraron.
        self.lineas_vacias += 1

    @staticmethod
    def _categoria_fecha(r: ResultadoLinea) -> str:
        # Se clasifica al agregar (y no recorriendo `problemas` después) porque
        # `problemas` puede estar recortado por el límite de detalle.
        if r.estado in _SIN_NIVEL_RECONOCIBLE:
            # Sin nivel reconocible, la línea se descarta antes de mirar la fecha.
            return "no_evaluada"
        if r.estado is Estado.FECHA_INVALIDA:
            return "invalida"
        # SIN_MENSAJE puede tener fecha válida ("[ERROR] 2025-01-10").
        return "valida" if r.fecha is not None else "sin_fecha"

    # --- Métricas derivadas ------------------------------------------------------

    def eventos_de(self, nivel: str) -> int:
        return self.por_nivel[nivel]

    @property
    def niveles_reporte(self) -> tuple[str, ...]:
        return (*NIVELES_VALIDOS, NIVEL_DESCONOCIDO)

    @property
    def con_fecha_valida(self) -> int:
        return self.por_fecha["valida"]

    @property
    def sin_fecha(self) -> int:
        return self.por_fecha["sin_fecha"]

    @property
    def con_fecha_invalida(self) -> int:
        return self.por_fecha["invalida"]

    @property
    def fecha_no_evaluada(self) -> int:
        # Se informa aparte para que las cuatro cifras de fecha sumen el total.
        return self.por_fecha["no_evaluada"]

    @property
    def mal_formateadas_o_incompletas(self) -> int:
        return self.total_eventos - self.por_estado[Estado.VALIDA]

    @property
    def problemas_omitidos(self) -> int:
        """Líneas con problemas que no se guardaron por el límite de detalle."""
        return self.mal_formateadas_o_incompletas - len(self.problemas)
