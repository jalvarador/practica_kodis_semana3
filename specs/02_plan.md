# 02 · Plan técnico

Derivado de [01_spec.md](01_spec.md).

## Arquitectura

Separar **análisis** (lógica pura, testeable) de **entrada/salida** (archivo y consola):

```
analizar_logs.py              ← punto de entrada: python analizar_logs.py [archivo]
analizador_logs/
├── __init__.py
├── __main__.py               ← permite: python -m analizador_logs
├── parser.py                 ← analizar_linea(texto) -> ResultadoLinea      (RF2)
├── resumen.py                ← Resumen: acumula resultados                  (RF3)
├── reporte.py                ← formatear_reporte(resumen) -> str            (RF4)
└── cli.py                    ← argumentos, selección y lectura del archivo  (RF1, RNF2)
tests/
├── datos/                    ← archivos de prueba
├── test_parser.py            ← CA1–CA11
├── test_resumen.py
└── test_cli.py               ← CA12, CA13 y extremo a extremo
```

## Decisiones de diseño

| # | Decisión | Motivo |
|---|----------|--------|
| D1 | `parser.analizar_linea` es una función pura (str → dataclass) | Se prueba sin archivos ni consola. |
| D2 | Regex solo para **localizar** las partes; la validez de la fecha la decide `datetime.strptime` | Una regex `\d{4}-\d{2}-\d{2}` acepta `2025-13-45` o `2025-02-30`. |
| D3 | Un token "parece fecha" si son tres grupos de dígitos separados por `-` `/` `.` y **no** sigue otro separador con dígito (`(?![-/.]\d)`) | Distingue "fecha mal escrita" (`FECHA_INVALIDA`) de "no hay fecha" (`SIN_FECHA`), sin confundir una IP como `10.0.0.1` con una fecha. |
| D4 | Estados en un `Enum` con propiedad `es_problema` | Una sola fuente de verdad para "mal formateada o incompleta". |
| D5 | `Resumen` usa `collections.Counter` (por nivel, por estado y `por_fecha`) y guarda como mucho `limite_detalle` líneas con problemas | RNF3: la memoria no crece con el archivo ni con el número de errores. Los conteos de fecha se calculan al agregar, no recorriendo `problemas`, porque esa lista puede estar recortada. |
| D6 | Codificación: BOM UTF-16 → `utf-16`; si no, `utf-8-sig`; si falla, `latin-1`. Bytes nulos en los primeros 8 KB (sin BOM UTF-16) → binario | `>` en PowerShell 5.1 escribe UTF-16; Bloc de notas/Excel escriben BOM o ANSI. El umbral de 8 KB es el criterio de `git`/`grep` y no rechaza logs con relleno de nulos al final. |
| D7 | `--gui` con `tkinter` importado **dentro** de la función; `TclError` al crear la ventana → se pide la ruta por teclado | Si tkinter no está instalado, o no hay entorno gráfico, el modo consola sigue funcionando. |
| D8 | `main()` devuelve un código de salida en lugar de llamar a `sys.exit` | Se puede probar sin cerrar el intérprete. |
| D9 | Pruebas con `unittest` | Biblioteca estándar (RNF1); también funcionan con `pytest` si está instalado. |
| D10 | `reporte._sanear` escapa los caracteres no imprimibles con `unicode_escape` antes de mostrar texto del log | Un log es entrada no confiable: una línea con `ESC[2J` no debe poder borrar la pantalla. |
| D11 | `cli._imprimir` captura `BrokenPipeError`/`OSError` y redirige stdout a `os.devnull`; `KeyboardInterrupt` → código 130 | Sin traceback con `\| head` ni con Ctrl+C. En Windows una tubería cerrada da `OSError(EINVAL)`, no `BrokenPipeError`. |

## Modelo de datos

```python
class Estado(Enum): VALIDA, SIN_FECHA, FECHA_INVALIDA, SIN_MENSAJE, NIVEL_DESCONOCIDO, SIN_NIVEL

@dataclass(frozen=True)
class ResultadoLinea:
    numero: int
    texto: str
    nivel: str          # "INFO" | "WARNING" | "ERROR" | "DESCONOCIDO"
    estado: Estado
    fecha: datetime | None
    mensaje: str
```
