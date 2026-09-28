# 04 · Especificación incremental — Datos de prueba generados y a gran escala

> Amplía [01_spec.md](01_spec.md) **sin cambiar el analizador**. Solo se añaden un
> generador de logs y los archivos que produce.

## 1. Motivación

Los archivos de `tests/datos/` escritos a mano tienen menos de 20 líneas: sabemos qué
esperar, pero no prueban volumen ni variedad (mensajes largos, IPs, rutas, excepciones).
Escribir a mano miles de líneas **y** sus resultados esperados no es viable, así que se
generan.

## 2. Requisitos

- **RD1 — Generador** (`herramientas/generar_logs.py`). Crea archivos de *N* líneas en el
  formato de la spec 01, con mensajes realistas y una fracción configurable de líneas
  defectuosas. Cada defecto corresponde a un estado de la spec 01 (sin fecha, fecha u hora
  inválida, sin mensaje, nivel desconocido, sin nivel, línea vacía).
- **RD2 — Resultado esperado independiente.** Junto a cada log se escribe
  `<nombre>.esperado.json` con los conteos que se deberían obtener. Se calculan a partir
  de lo que el generador escribió, **sin usar el analizador**; si no, la comparación no
  probaría nada.
- **RD3 — Reproducible.** La misma semilla produce exactamente el mismo archivo, así los
  archivos del repositorio se pueden regenerar y verificar.
- **RD4 — Archivos incluidos** en `tests/datos/generados/`:

  | Archivo                          | Líneas | Errores | Semilla |
  |----------------------------------|-------:|--------:|--------:|
  | `logs_generado_limpio.log`       | 5.000  | 0 %     | 1       |
  | `logs_generado_con_errores.log`  | 5.000  | 20 %    | 2       |

- **RD5 — Rendimiento.** Se mide el tiempo y la memoria al analizar 1.000.000 de líneas
  generadas (documentado, sin umbral fijo). Ese archivo (unos 70 MB) no se incluye en el
  proyecto: se genera cuando hace falta.

## 3. Criterios de aceptación

| ID  | Dado                                         | Se espera |
|-----|----------------------------------------------|-----------|
| CD1 | `logs_generado_limpio.log`                   | 5.000 eventos, 0 mal formateados; conteos == `.esperado.json` |
| CD2 | `logs_generado_con_errores.log`              | Conteos por nivel y por estado == `.esperado.json` |
| CD3 | Regenerar cualquiera de los dos con su semilla | Archivo idéntico byte a byte al incluido |
| CD4 | Archivo nuevo con otra semilla y otra tasa   | Conteos == `.esperado.json` |
| CD5 | `--errores` fuera de 0–1 o `--lineas` negativo | Mensaje de error, código de salida ≠ 0 |
