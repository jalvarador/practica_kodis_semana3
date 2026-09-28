"""Pruebas del acumulador Resumen (RF3)."""

import unittest

from analizador_logs.parser import analizar_linea
from analizador_logs.resumen import Resumen


def resumen_de(*lineas, limite=None):
    r = Resumen(limite_detalle=limite)
    for n, linea in enumerate(lineas, start=1):
        if linea.strip():
            r.agregar(analizar_linea(linea, n))
        else:
            r.agregar_vacia()
    return r


class TestResumen(unittest.TestCase):
    def test_vacio(self):
        r = Resumen()
        self.assertEqual(r.total_eventos, 0)
        self.assertEqual(r.mal_formateadas_o_incompletas, 0)

    def test_conteos_por_nivel_y_problemas(self):
        r = resumen_de(
            "[INFO] 2025-01-10 a",
            "[INFO] 2025-01-10 b",
            "[WARNING] c",
            "",
            "[ERROR] 2025-99-99 d",
            "sin nivel",
        )
        self.assertEqual(r.total_eventos, 5)
        self.assertEqual(r.lineas_vacias, 1)
        self.assertEqual(r.eventos_de("INFO"), 2)
        self.assertEqual(r.eventos_de("WARNING"), 1)
        self.assertEqual(r.eventos_de("ERROR"), 1)
        self.assertEqual(r.eventos_de("DESCONOCIDO"), 1)
        self.assertEqual(r.mal_formateadas_o_incompletas, 3)
        self.assertEqual([p.numero for p in r.problemas], [3, 5, 6])

    def test_desglose_de_fechas_suma_el_total(self):
        r = resumen_de(
            "[INFO] 2025-01-10 ok",   # válida
            "[ERROR] 2025-01-10",     # sin mensaje, pero con fecha válida
            "[ERROR]",                # sin mensaje y sin fecha
            "[WARNING] sin fecha",    # sin fecha
            "[INFO] 2025-02-30 x",    # inválida
            "[DEBUG] 2025-01-10 x",   # no evaluada
        )
        self.assertEqual(r.con_fecha_valida, 2)
        self.assertEqual(r.sin_fecha, 2)
        self.assertEqual(r.con_fecha_invalida, 1)
        self.assertEqual(r.fecha_no_evaluada, 1)
        self.assertEqual(
            r.con_fecha_valida + r.sin_fecha + r.con_fecha_invalida + r.fecha_no_evaluada,
            r.total_eventos,
        )

    def test_limite_de_detalle_no_cambia_los_conteos(self):
        lineas = ["[INFO] 2025-01-10 ok", "[ERROR]", "[WARNING] sin fecha",
                  "[INFO] 2025-02-30 x", "nada", "[DEBUG] 2025-01-10 x"] * 20
        completo, recortado, nada = (resumen_de(*lineas, limite=l) for l in (None, 3, 0))
        for r in (recortado, nada):
            self.assertEqual(r.mal_formateadas_o_incompletas, 100)
            self.assertEqual(r.por_fecha, completo.por_fecha)
        self.assertEqual(len(completo.problemas), 100)
        self.assertEqual((len(recortado.problemas), recortado.problemas_omitidos), (3, 97))
        self.assertEqual((len(nada.problemas), nada.problemas_omitidos), (0, 100))


if __name__ == "__main__":
    unittest.main()
