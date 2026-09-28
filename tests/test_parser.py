"""Pruebas de analizar_linea: una por criterio de aceptación (specs/01_spec.md, sección 6)."""

import unittest
from datetime import datetime

from analizador_logs.parser import Estado, analizar_linea, es_linea_vacia


class TestCriteriosAceptacion(unittest.TestCase):
    def comprobar(self, linea, nivel, estado):
        r = analizar_linea(linea)
        self.assertEqual((r.nivel, r.estado), (nivel, estado), msg=linea)
        return r

    def test_ca1_linea_valida(self):
        r = self.comprobar("[INFO] 2025-01-10 User logged in", "INFO", Estado.VALIDA)
        self.assertEqual(r.fecha, datetime(2025, 1, 10))
        self.assertEqual(r.mensaje, "User logged in")

    def test_ca2_sin_fecha(self):
        r = self.comprobar("[WARNING] Invalid password attempt", "WARNING", Estado.SIN_FECHA)
        self.assertEqual(r.mensaje, "Invalid password attempt")

    def test_ca3_mes_y_dia_fuera_de_rango(self):
        self.comprobar("[ERROR] 2025-13-45 Disk full", "ERROR", Estado.FECHA_INVALIDA)

    def test_ca4_fecha_inexistente(self):
        # La forma es correcta, pero el 30 de febrero no existe: lo detecta strptime (D2).
        self.comprobar("[ERROR] 2025-02-30 x", "ERROR", Estado.FECHA_INVALIDA)

    def test_ca5_formato_no_iso(self):
        self.comprobar("[INFO] 10/01/2025 Boot", "INFO", Estado.FECHA_INVALIDA)

    def test_ca6_hora_imposible(self):
        self.comprobar("[INFO] 2025-01-10 25:61:00 Boot", "INFO", Estado.FECHA_INVALIDA)

    def test_ca7_sin_mensaje(self):
        r = self.comprobar("[ERROR] 2025-01-10", "ERROR", Estado.SIN_MENSAJE)
        self.assertIsNotNone(r.fecha)

    def test_ca8_nivel_desconocido(self):
        self.comprobar("[DEBUG] 2025-01-10 Cache hit", "DESCONOCIDO", Estado.NIVEL_DESCONOCIDO)

    def test_ca9_sin_nivel(self):
        self.comprobar("User logged out", "DESCONOCIDO", Estado.SIN_NIVEL)

    def test_ca10_vineta_y_minusculas(self):
        self.comprobar("· [info] 2025-01-10 ok", "INFO", Estado.VALIDA)

    def test_ca14_ip_no_es_fecha(self):
        # Antes "10.0.0.1" salía FECHA_INVALIDA y "192.168.1.10" SIN_FECHA (D3 inconsistente).
        self.comprobar("[WARNING] 10.0.0.1 blocked", "WARNING", Estado.SIN_FECHA)
        self.comprobar("[INFO] 192.168.1.10 connected", "INFO", Estado.SIN_FECHA)

    def test_ca11_linea_vacia(self):
        self.assertTrue(es_linea_vacia(""))
        self.assertTrue(es_linea_vacia("   \t\n"))
        self.assertFalse(es_linea_vacia("[INFO]"))


class TestCasosLimite(unittest.TestCase):
    def test_hora_valida_se_incorpora_a_la_fecha(self):
        r = analizar_linea("[INFO] 2025-01-10 08:15:30 Start")
        self.assertEqual(r.estado, Estado.VALIDA)
        self.assertEqual(r.fecha, datetime(2025, 1, 10, 8, 15, 30))
        self.assertEqual(r.mensaje, "Start")

    def test_anio_bisiesto(self):
        self.assertEqual(analizar_linea("[INFO] 2024-02-29 ok").estado, Estado.VALIDA)
        self.assertEqual(analizar_linea("[INFO] 2025-02-29 ok").estado, Estado.FECHA_INVALIDA)

    def test_forma_iso_pero_fecha_inexistente(self):
        # Todas cumplen la regex \d{4}-\d{2}-\d{2}; solo strptime sabe que no existen (D2).
        import re
        solo_regex = re.compile(r"\d{4}-\d{2}-\d{2}")
        for fecha in ("2025-13-45", "2025-02-30", "2025-02-29", "2025-04-31",
                      "2025-00-10", "0000-01-01", "9999-99-99"):
            with self.subTest(fecha):
                self.assertTrue(solo_regex.fullmatch(fecha))
                self.assertEqual(analizar_linea(f"[ERROR] {fecha} x").estado,
                                 Estado.FECHA_INVALIDA)

    def test_fecha_sin_ceros_no_es_iso(self):
        # strptime aceptaría "2025-1-5"; la regex previa lo impide (D2).
        self.assertEqual(analizar_linea("[INFO] 2025-1-5 ok").estado, Estado.FECHA_INVALIDA)

    def test_numero_decimal_en_mensaje_no_es_fecha(self):
        # D3: "3.5" no tiene dos separadores, así que es mensaje, no fecha rota.
        r = analizar_linea("[INFO] 3.5 seconds elapsed")
        self.assertEqual(r.estado, Estado.SIN_FECHA)

    def test_solo_etiqueta(self):
        self.assertEqual(analizar_linea("[ERROR]").estado, Estado.SIN_MENSAJE)

    def test_etiqueta_vacia(self):
        self.assertEqual(analizar_linea("[] algo").estado, Estado.NIVEL_DESCONOCIDO)

    def test_nivel_sin_corchetes(self):
        self.assertEqual(analizar_linea("INFO 2025-01-10 x").estado, Estado.SIN_NIVEL)

    def test_espacios_y_salto_de_linea_windows(self):
        r = analizar_linea("   [WARNING]   2025-01-10   Low disk  \r\n", numero=7)
        self.assertEqual((r.estado, r.numero, r.mensaje), (Estado.VALIDA, 7, "Low disk"))

    def test_fecha_rota_seguida_de_texto_sigue_siendo_fecha_invalida(self):
        # El lookahead de D3 solo excluye un cuarto grupo numérico, no otros sufijos.
        self.assertEqual(analizar_linea("[INFO] 2025-13-01, x").estado, Estado.FECHA_INVALIDA)

    def test_etiquetas_de_estado_son_ascii(self):
        # Regresión RNF4: "inválida" salía como "inv?lida" al redirigir la salida en Windows.
        for estado in Estado:
            self.assertTrue(estado.value.isascii(), estado.value)

    def test_solo_valida_no_es_problema(self):
        problemas = [e for e in Estado if e.es_problema]
        self.assertNotIn(Estado.VALIDA, problemas)
        self.assertEqual(len(problemas), len(Estado) - 1)


class TestEdgeCasesPendientes(unittest.TestCase):
    """Fijan el comportamiento ACTUAL de los edge cases pendientes (spec 01, sección 7).

    No afirman que este resultado sea el deseable: la decisión está abierta. Si se
    resuelve un caso, primero se actualiza la spec y después esta prueba.
    """

    def test_ep1_dos_puntos_tras_etiqueta(self):
        r = analizar_linea("[ERROR]: 2025-01-10 x")
        self.assertEqual((r.nivel, r.estado), ("ERROR", Estado.SIN_FECHA))

    def test_ep2_iso_8601_con_t(self):
        r = analizar_linea("[INFO] 2025-01-10T10:00:00 x")
        self.assertEqual((r.nivel, r.estado), ("INFO", Estado.FECHA_INVALIDA))

    def test_ep4_etiqueta_desconocida_no_se_conserva(self):
        # Mejora no contemplada: la clasificación es correcta, pero "DEBUG" solo queda en
        # el texto crudo; ni `nivel` ni `mensaje` la conservan.
        r = analizar_linea("[DEBUG] 2025-01-11 Query executed in 12ms")
        self.assertEqual((r.nivel, r.estado), ("DESCONOCIDO", Estado.NIVEL_DESCONOCIDO))
        self.assertNotIn("DEBUG", r.nivel + r.mensaje)
        self.assertIn("DEBUG", r.texto)

    def test_ep3_milisegundos(self):
        for linea in ("[INFO] 2025-01-10 08:00:00.123 x", "[INFO] 2025-01-10 08:00:00,123 x"):
            with self.subTest(linea):
                self.assertEqual(analizar_linea(linea).estado, Estado.FECHA_INVALIDA)


if __name__ == "__main__":
    unittest.main()
