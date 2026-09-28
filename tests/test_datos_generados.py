"""Pruebas con los logs generados (specs/04_spec_datos_generados.md)."""

import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from analizador_logs.cli import analizar_archivo

RAIZ = Path(__file__).resolve().parent.parent
GENERADOS = RAIZ / "tests" / "datos" / "generados"
sys.path.insert(0, str(RAIZ / "herramientas"))
import generar_logs  # noqa: E402


def leer_esperado(log: Path) -> dict:
    return json.loads(log.with_suffix(".esperado.json").read_text(encoding="utf-8"))


class CompararConEsperado(unittest.TestCase):
    def comprobar(self, log: Path) -> None:
        esperado = leer_esperado(log)
        r = analizar_archivo(log)
        self.assertEqual(r.total_eventos, esperado["total_eventos"])
        self.assertEqual(r.lineas_vacias, esperado["lineas_vacias"])
        self.assertEqual(dict(r.por_nivel), esperado["por_nivel"])
        self.assertEqual({e.name: n for e, n in r.por_estado.items()}, esperado["por_estado"])
        self.assertEqual(r.mal_formateadas_o_incompletas,
                         esperado["mal_formateadas_o_incompletas"])


class TestArchivosIncluidos(CompararConEsperado):
    def test_cd1_limpio(self):
        log = GENERADOS / "logs_generado_limpio.log"
        self.comprobar(log)
        r = analizar_archivo(log)
        self.assertEqual((r.total_eventos, r.mal_formateadas_o_incompletas), (5000, 0))

    def test_cd2_con_errores(self):
        self.comprobar(GENERADOS / "logs_generado_con_errores.log")

    def test_cd3_se_regeneran_identicos(self):
        with tempfile.TemporaryDirectory() as tmp:
            for log in sorted(GENERADOS.glob("*.log")):
                with self.subTest(log.name):
                    esperado = leer_esperado(log)
                    copia = Path(tmp) / log.name
                    generar_logs.generar(copia, esperado["lineas_escritas"],
                                         esperado["tasa_errores"], esperado["semilla"])
                    self.assertEqual(copia.read_bytes(), log.read_bytes())


class TestGenerador(CompararConEsperado):
    def test_cd4_otra_semilla_y_tasa(self):
        with tempfile.TemporaryDirectory() as tmp:
            log = Path(tmp) / "gen.log"
            generar_logs.generar(log, lineas=20_000, tasa_errores=0.5, semilla=123)
            self.comprobar(log)

    def test_cd5_argumentos_invalidos(self):
        for args in (["x.log", "--errores", "1.5"], ["x.log", "--lineas", "-1"]):
            with self.subTest(args), redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    generar_logs.main(args)
                self.assertNotEqual(ctx.exception.code, 0)


if __name__ == "__main__":
    unittest.main()
