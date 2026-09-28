# 03 · Tareas

Derivadas de [02_plan.md](02_plan.md). Cada tarea referencia los requisitos / criterios que cubre.

| # | Tarea | Cubre | Estado |
|---|-------|-------|--------|
| T1 | `parser.py`: `Estado`, `ResultadoLinea`, `analizar_linea` | RF2, CA1–CA11 | ✅ |
| T2 | `test_parser.py`: un test por criterio de aceptación CA1–CA11 | CA1–CA11 | ✅ |
| T3 | `resumen.py`: acumulador con conteos por nivel, por fecha y problemas | RF3 | ✅ |
| T4 | `test_resumen.py` | RF3 | ✅ |
| T5 | `reporte.py`: texto del informe con detalle opcional | RF4, RNF4 | ✅ |
| T6 | `cli.py`: argumentos, pedir ruta, `--gui`, lectura robusta | RF1, RNF2, RNF3 | ✅ |
| T7 | `test_cli.py`: archivo inexistente, vacío, directorio, latin-1, extremo a extremo | CA12, CA13, RNF2 | ✅ |
| T8 | Archivos de prueba en `tests/datos/` (bien formado y con errores) | Evidencia | ✅ |
| T9 | `docs/evidencia_pruebas.md`: esperado vs. obtenido | Entregable | ✅ |
| T10 | `docs/reflexion_tecnica.md` | Entregable | ✅ (borrador a validar por el estudiante) |
| T11 | Spec 04: generador y datos a gran escala | RD1–RD5 | ✅ |
| T12 | `herramientas/generar_logs.py` con `.esperado.json` y semilla | RD1–RD3 | ✅ |
| T13 | Generar `tests/datos/generados/` (limpio y con errores) | RD4 | ✅ |
| T14 | `test_datos_generados.py` | CD1–CD5 | ✅ |
| T15 | Medir 1.000.000 de líneas y documentarlo | RD5 | ✅ |
| T16 | Evaluación de edge cases: spec 01 con RF1/RF4/RNF2/RNF3/RNF4 revisados y CA13–CA21 | Spec | ✅ |
| T17 | `parser.py`: lookahead en `_RE_PARECE_FECHA` (IP ≠ fecha) | CA14 | ✅ |
| T18 | `resumen.py`: `por_fecha` y `limite_detalle` | RF4, RNF3, CA18 | ✅ |
| T19 | `reporte.py`: `_sanear`, mensaje de archivo vacío, conteo real para "Todas las lineas..." | RNF4, CA13, CA17 | ✅ |
| T20 | `cli.py`: UTF-16, binarios, `~`, `--gui` sin display, Ctrl+C, tubería cerrada, `--max-detalle` | RNF2, CA15, CA16, CA19–CA21 | ✅ |
| T21 | Pruebas de edge cases en `test_parser.py`, `test_resumen.py`, `test_cli.py` (54 en total) | CA13–CA21 | ✅ |
| T22 | Registrar EP1–EP3 como edge cases pendientes (spec 01, sección 7) y fijarlos con `TestEdgeCasesPendientes` | EP1–EP3 | ✅ |
| T23 | Documentar los pendientes en `evidencia_pruebas` y `reflexion_tecnica` (.md y .docx) | Entregable | ✅ |
| T24 | `test_forma_iso_pero_fecha_inexistente` (regex sola vs. `strptime`) y prueba de mutación documentada | D2, CA3, CA4 | ✅ |
| T25 | Corregir `test_tuberia_cerrada_no_lanza_excepcion`: silenciaba el stdout real del proceso de pruebas | Calidad de pruebas | ✅ |
| T26 | Reflexión técnica completa (ejemplo 4.2, otros errores de la IA) dentro de 1–3 páginas; evidencia con sección de validación de fechas (.docx) | Entregable | ✅ |
| T27 | Registrar EP4 (etiqueta de nivel desconocido no conservada) como mejora pendiente y fijarla con `test_ep4_etiqueta_desconocida_no_se_conserva` | EP4 | ✅ |
