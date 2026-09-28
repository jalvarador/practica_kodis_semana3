"""Pruebas de extremo a extremo con los archivos de tests/datos (RF1, RF4, RNF2)."""

import io
import os
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

from analizador_logs import cli
from analizador_logs.cli import analizar_archivo, main

DATOS = Path(__file__).parent / "datos"


def ejecutar(*argv):
    salida, errores = io.StringIO(), io.StringIO()
    with redirect_stdout(salida), redirect_stderr(errores):
        codigo = main(list(argv))
    return codigo, salida.getvalue(), errores.getvalue()


class TestArchivoBienFormado(unittest.TestCase):
    def test_resumen(self):
        r = analizar_archivo(DATOS / "logs_bien_formado.log")
        self.assertEqual(r.total_eventos, 10)
        self.assertEqual((r.eventos_de("INFO"), r.eventos_de("WARNING"), r.eventos_de("ERROR")),
                         (5, 3, 2))
        self.assertEqual(r.con_fecha_valida, 10)
        self.assertEqual(r.mal_formateadas_o_incompletas, 0)

    def test_salida_consola(self):
        codigo, salida, _ = ejecutar(str(DATOS / "logs_bien_formado.log"))
        self.assertEqual(codigo, 0)
        self.assertIn("Todas las lineas estan bien formadas.", salida)


class TestArchivoConErrores(unittest.TestCase):
    def test_resumen(self):
        r = analizar_archivo(DATOS / "logs_con_errores.log")
        self.assertEqual(r.total_eventos, 15)
        self.assertEqual(r.lineas_vacias, 2)
        self.assertEqual(
            {n: r.eventos_de(n) for n in r.niveles_reporte},
            {"INFO": 4, "WARNING": 3, "ERROR": 4, "DESCONOCIDO": 4},
        )
        self.assertEqual(r.con_fecha_valida, 5)
        self.assertEqual(r.sin_fecha, 2)
        self.assertEqual(r.con_fecha_invalida, 4)
        self.assertEqual(r.fecha_no_evaluada, 4)
        self.assertEqual(r.mal_formateadas_o_incompletas, 11)
        self.assertEqual([p.numero for p in r.problemas],
                         [3, 5, 6, 7, 8, 9, 10, 11, 12, 13, 17])

    def test_sin_detalle(self):
        codigo, salida, _ = ejecutar(str(DATOS / "logs_con_errores.log"), "--sin-detalle")
        self.assertEqual(codigo, 0)
        self.assertNotIn("Detalle de lineas", salida)


class TestErroresDeEntrada(unittest.TestCase):
    def test_ca12_archivo_inexistente(self):
        codigo, _, errores = ejecutar(str(DATOS / "no_existe.log"))
        self.assertEqual(codigo, 1)
        self.assertIn("no existe", errores)

    def test_ruta_es_directorio(self):
        codigo, _, errores = ejecutar(str(DATOS))
        self.assertEqual(codigo, 1)
        self.assertIn("no es un archivo", errores)

    def test_ca13_archivo_vacio(self):
        codigo, salida, _ = ejecutar(str(DATOS / "logs_vacio.log"))
        self.assertEqual(codigo, 0)
        self.assertIn("Total de eventos", salida)
        self.assertIn("El archivo no contiene eventos.", salida)
        self.assertNotIn("Todas las lineas estan bien formadas.", salida)
        self.assertEqual(analizar_archivo(DATOS / "logs_vacio.log").total_eventos, 0)

    def test_codificacion_latin1(self):
        r = analizar_archivo(DATOS / "logs_latin1.log")
        self.assertEqual(r.total_eventos, 2)
        self.assertEqual(r.mal_formateadas_o_incompletas, 0)

    def test_ruta_pedida_por_teclado_con_comillas(self):
        ruta = f'"{DATOS / "logs_bien_formado.log"}"'
        with mock.patch("builtins.input", return_value=ruta):
            codigo, salida, _ = ejecutar()
        self.assertEqual(codigo, 0)
        self.assertIn("logs_bien_formado.log", salida)

    def test_ruta_vacia_por_teclado(self):
        with mock.patch("builtins.input", return_value="   "):
            codigo, _, errores = ejecutar()
        self.assertEqual(codigo, 1)
        self.assertIn("No se indico", errores)


class TestEdgeCases(unittest.TestCase):
    """Criterios CA15–CA21, añadidos en la evaluación de edge cases."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def escribir(self, nombre, contenido: bytes) -> Path:
        ruta = self.dir / nombre
        ruta.write_bytes(contenido)
        return ruta

    def test_ca15_utf16_da_lo_mismo_que_utf8(self):
        texto = (DATOS / "logs_con_errores.log").read_text(encoding="utf-8")
        base = analizar_archivo(DATOS / "logs_con_errores.log")
        # "utf-16" escribe BOM + little-endian, como `>` en PowerShell 5.1.
        variantes = {
            "utf-16-le": texto.encode("utf-16"),
            "utf-16-be": b"\xfe\xff" + texto.encode("utf-16-be"),
        }
        for nombre, datos in variantes.items():
            with self.subTest(nombre):
                r = analizar_archivo(self.escribir(f"{nombre}.log", datos))
                self.assertEqual(r.total_eventos, base.total_eventos)
                self.assertEqual(r.por_estado, base.por_estado)

    def test_utf16_truncado_da_error_claro(self):
        datos = "[INFO] 2025-01-10 ok\n".encode("utf-16") + b"\x41"  # byte suelto al final
        codigo, _, errores = ejecutar(str(self.escribir("trunc.log", datos)))
        self.assertEqual(codigo, 1)
        self.assertIn("No se pudo decodificar", errores)

    def test_ca16_binario_se_rechaza(self):
        ruta = self.escribir("binario.bin", b"MZ\x90\x00\x03\x00\x00\x00" * 100)
        codigo, salida, errores = ejecutar(str(ruta))
        self.assertEqual(codigo, 1)
        self.assertIn("no parece un archivo de texto", errores)
        self.assertEqual(salida, "")

    def test_nulos_despues_de_8kb_no_invalidan_el_archivo(self):
        # Log truncado por un crash: relleno de nulos al final.
        linea = b"[INFO] 2025-01-10 ok\n"
        ruta = self.escribir("crash.log", linea * 1000 + b"\x00" * 64 + b"\n")
        r = analizar_archivo(ruta)
        self.assertEqual(r.total_eventos, 1001)
        self.assertEqual(r.mal_formateadas_o_incompletas, 1)

    def test_ca17_caracteres_de_control_se_escapan(self):
        ruta = self.escribir("ansi.log", b"[ERROR] 2025-99-99 \x1b[2J\x1b[31mX\x1b[0m\n")
        _, salida, _ = ejecutar(str(ruta))
        self.assertNotIn("\x1b", salida)      # ningún ESC real llega a la terminal
        self.assertIn(r"\x1b[2J", salida)     # se muestra escapado

    def test_ca18_detalle_limitado_por_defecto(self):
        ruta = self.escribir("muchos.log", b"sin nivel\n" * 60)
        _, salida, _ = ejecutar(str(ruta))
        self.assertEqual(salida.count("Sin nivel "), 50)
        self.assertIn("... y 10 lineas mas", salida)

        _, salida, _ = ejecutar(str(ruta), "--max-detalle", "0")
        self.assertEqual(salida.count("Sin nivel "), 60)
        self.assertNotIn("lineas mas", salida)

        _, salida, _ = ejecutar(str(ruta), "--max-detalle", "5")
        self.assertIn("... y 55 lineas mas", salida)

    def test_sin_detalle_no_dice_que_todo_esta_bien(self):
        # Con --sin-detalle no se guarda ninguna línea con problemas; el reporte debe
        # decidir por el conteo, no por la lista vacía.
        _, salida, _ = ejecutar(str(DATOS / "logs_con_errores.log"), "--sin-detalle")
        self.assertNotIn("Todas las lineas estan bien formadas.", salida)
        self.assertNotIn("lineas mas", salida)

    def test_max_detalle_negativo_es_error_de_uso(self):
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as ctx:
            main([str(DATOS / "logs_bien_formado.log"), "--max-detalle", "-1"])
        self.assertEqual(ctx.exception.code, 2)

    def test_ca19_tilde_se_expande(self):
        (self.dir / "mio.log").write_bytes((DATOS / "logs_bien_formado.log").read_bytes())
        # expanduser usa USERPROFILE en Windows y HOME en el resto.
        with mock.patch.dict(os.environ, {"USERPROFILE": str(self.dir), "HOME": str(self.dir)}):
            codigo, _, _ = ejecutar("~/mio.log")
        self.assertEqual(codigo, 0)

    def test_ca20_gui_sin_entorno_grafico_pide_por_teclado(self):
        import tkinter
        ruta = str(DATOS / "logs_bien_formado.log")
        with mock.patch("tkinter.Tk", side_effect=tkinter.TclError("no display name")), \
             mock.patch("builtins.input", return_value=ruta):
            codigo, _, errores = ejecutar("--gui")
        self.assertEqual(codigo, 0)
        self.assertIn("No hay entorno grafico", errores)

    def test_ca21_ctrl_c(self):
        with mock.patch.object(cli, "analizar_archivo", side_effect=KeyboardInterrupt):
            codigo, _, errores = ejecutar(str(DATOS / "logs_bien_formado.log"))
        self.assertEqual(codigo, 130)
        self.assertIn("Analisis cancelado.", errores)

    def test_tuberia_cerrada_no_lanza_excepcion(self):
        # stdout redirigido a propósito: _imprimir hace os.dup2(devnull, stdout.fileno())
        # y, sin redirigir, dejaba mudo el stdout real de todo el proceso de pruebas.
        with redirect_stdout(io.StringIO()), \
             mock.patch("builtins.print", side_effect=BrokenPipeError):
            self.assertEqual(main([str(DATOS / "logs_bien_formado.log")]), 1)


if __name__ == "__main__":
    unittest.main()
