# Analizador de logs — Práctica semana 3

Script en Python (solo biblioteca estándar, Python 3.10+) que analiza un archivo de logs
y muestra un resumen por consola. Desarrollado con metodología **SDD**.

## Uso

```bash
python analizar_logs.py ruta/al/archivo.log     # archivo como argumento
python analizar_logs.py                         # pide la ruta por teclado
python analizar_logs.py --gui                   # selector de archivos
python analizar_logs.py archivo.log --sin-detalle      # solo el resumen
python analizar_logs.py archivo.log --max-detalle 0    # todas las lineas con problemas (defecto: 50)
```

## Pruebas

```bash
python -m unittest discover -s tests -t . -v
```

## Estructura

| Ruta | Contenido |
|------|-----------|
| [specs/01_spec.md](specs/01_spec.md) | Especificación y criterios de aceptación (fuente de verdad) |
| [specs/02_plan.md](specs/02_plan.md) | Diseño técnico y decisiones D1–D11 |
| [specs/03_tareas.md](specs/03_tareas.md) | Tareas y trazabilidad a requisitos |
| [analizar_logs.py](analizar_logs.py) | Punto de entrada |
| [analizador_logs/](analizador_logs/) | `parser` (línea), `resumen` (conteos), `reporte` (texto), `cli` (archivo/argumentos) |
| [specs/04_spec_datos_generados.md](specs/04_spec_datos_generados.md) | Ampliación: generador de logs y datos a gran escala |
| [herramientas/generar_logs.py](herramientas/generar_logs.py) | Genera logs sintéticos de cualquier tamaño con sus conteos esperados |
| [tests/](tests/) | 59 pruebas `unittest` y archivos de ejemplo en `tests/datos/` |
| [tests/datos/generados/](tests/datos/generados/) | Logs generados de 5.000 líneas (limpio y con 20 % de errores) con su `.esperado.json` |
| [docs/evidencia_pruebas.docx](docs/evidencia_pruebas.docx) | Resultados esperados vs. obtenidos |
| [docs/reflexion_tecnica.docx](docs/reflexion_tecnica.docx) | Reflexión sobre el uso de IA (2 páginas) |
