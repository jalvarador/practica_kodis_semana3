# 01 · Especificación — Analizador de logs

> Metodología SDD (Spec-Driven Development). Este documento es la **fuente de verdad**:
> el plan, las tareas, el código y las pruebas se derivan de aquí. Si el código y la
> spec discrepan, se corrige uno de los dos de forma explícita, nunca en silencio.

## 1. Objetivo

Script de consola en Python que lee un archivo de texto con eventos de una aplicación
(un evento por línea), clasifica cada línea y muestra un resumen claro.

## 2. Formato de entrada esperado

```
[NIVEL] AAAA-MM-DD [HH:MM:SS] Mensaje
```

| Parte     | Obligatoria | Regla                                                              |
|-----------|-------------|--------------------------------------------------------------------|
| Nivel     | Sí          | `[INFO]`, `[WARNING]` o `[ERROR]`, entre corchetes. Sin distinguir mayúsculas. |
| Fecha     | Sí*         | `AAAA-MM-DD` y además debe existir en el calendario (no `2025-02-30`). |
| Hora      | No          | Si aparece tras la fecha: `HH:MM:SS` válida (00–23, 00–59, 00–59). |
| Mensaje   | Sí          | Texto no vacío después del nivel/fecha.                            |

\* Una línea sin fecha **sigue siendo un evento** (tiene nivel), pero cuenta como *incompleta*.

Se toleran viñetas iniciales (`·`, `-`, `*`) y espacios alrededor, porque el enunciado
muestra ejemplos con `·` delante.

## 3. Clasificación de cada línea (estados mutuamente excluyentes)

| Estado            | Condición                                                        | ¿Evento? | ¿Problemática? |
|-------------------|------------------------------------------------------------------|----------|----------------|
| `VALIDA`          | Nivel conocido + fecha válida + mensaje                          | Sí       | No             |
| `SIN_FECHA`       | Nivel conocido + mensaje, sin fecha                              | Sí       | Sí (incompleta)|
| `FECHA_INVALIDA`  | Nivel conocido + algo con forma de fecha/hora que no es válido   | Sí       | Sí (mal formateada) |
| `SIN_MENSAJE`     | Nivel conocido (con o sin fecha) pero sin mensaje                | Sí       | Sí (incompleta)|
| `NIVEL_DESCONOCIDO` | Etiqueta entre corchetes no reconocida (`[DEBUG]`, `[]`)       | Sí       | Sí (mal formateada) |
| `SIN_NIVEL`       | No empieza por una etiqueta `[...]`                              | Sí       | Sí (mal formateada) |
| *(línea vacía)*   | Solo espacios                                                    | **No**   | No — se ignora |

Prioridad al evaluar: nivel → fecha/hora → mensaje (se reporta el **primer** problema).

**¿Cuándo un token "intenta ser una fecha"?** Cuando son exactamente tres grupos de
dígitos separados por `-`, `/` o `.` (`2025-13-45`, `10/01/2025`). Si detrás viene otro
separador con dígitos (`10.0.0.1`, una IP) no es una fecha: la línea queda como `SIN_FECHA`.
*(Revisado en la evaluación de edge cases: `10.0.0.1` salía como `FECHA_INVALIDA` y
`192.168.1.10` como `SIN_FECHA`.)*

## 4. Requisitos funcionales

- **RF1** — El usuario elige el archivo: como argumento de línea de comandos, o, si no lo
  pasa, se le pide por teclado. Opción `--gui` para abrir un selector de archivos; si no
  hay entorno gráfico, se avisa y se pide la ruta por teclado. `~` se expande a la carpeta
  del usuario.
- **RF2** — Analizar cada línea y determinar nivel y validez de la fecha (sección 3).
- **RF3** — Resumen con:
  - Total de eventos (líneas no vacías).
  - Eventos por tipo: INFO, WARNING, ERROR y *DESCONOCIDO* (sin nivel reconocible).
  - Eventos con fecha válida / sin fecha / con fecha inválida.
  - Número de líneas mal formateadas o incompletas (todo lo que no es `VALIDA`).
- **RF4** — Mostrar el resumen en consola de forma clara, con el detalle de las líneas
  problemáticas (número de línea, motivo, contenido). Por defecto se muestran las
  **primeras 50** y un aviso con cuántas faltan; `--max-detalle N` cambia el límite
  (`0` = todas) y `--sin-detalle` oculta el detalle.

## 5. Requisitos no funcionales

- **RNF1** — Solo biblioteca estándar (sin dependencias externas).
- **RNF2** — No debe romperse con archivos inexistentes, directorios, archivos vacíos o
  codificaciones distintas de UTF-8: mensaje claro y código de salida ≠ 0.
  - Codificaciones: UTF-8 (con o sin BOM), UTF-16 con BOM (lo que produce `>` en
    PowerShell 5.1 y "Unicode" en el Bloc de notas) y, como respaldo, latin-1.
  - Un archivo binario se rechaza: `Error: ... no parece un archivo de texto`, código 1.
    Criterio (el mismo que usan `git` y `grep`): hay bytes nulos en los primeros 8 KB.
    Un byte nulo más adelante no invalida el archivo, porque los logs truncados por un
    crash a veces terminan con relleno de nulos; esa línea se analiza como cualquier otra.
  - Ctrl+C: `Analisis cancelado.`, código 130, sin traceback.
  - Tubería cerrada por el receptor (`| head`): se termina en silencio, sin traceback.
- **RNF3** — Procesa línea a línea (no carga el archivo entero en memoria). La memoria
  tampoco crece con el número de líneas con problemas: solo se guardan las que se van a
  mostrar en el detalle.
- **RNF4** — Todo el texto que genera el programa (marcos, etiquetas, mensajes de error)
  es ASCII, para que se vea bien en cualquier consola de Windows, también al redirigir
  la salida. *(Revisado tras la primera ejecución: las etiquetas con tilde, como
  "inválida", salían corruptas al pasar por una tubería con codificación cp1252.)*
  El contenido del log que se muestra en el detalle se sanea: los caracteres de control
  (por ejemplo, secuencias ANSI `ESC[2J`) se escriben escapados (`\x1b[2J`) para que una
  línea del log no pueda borrar la pantalla ni cambiar colores en la terminal.

## 6. Criterios de aceptación

| ID   | Dado                                           | Se espera                                |
|------|------------------------------------------------|------------------------------------------|
| CA1  | `[INFO] 2025-01-10 User logged in`             | INFO, `VALIDA`                           |
| CA2  | `[WARNING] Invalid password attempt`           | WARNING, `SIN_FECHA`                     |
| CA3  | `[ERROR] 2025-13-45 Disk full`                 | ERROR, `FECHA_INVALIDA`                  |
| CA4  | `[ERROR] 2025-02-30 x`                         | ERROR, `FECHA_INVALIDA` (fecha inexistente) |
| CA5  | `[INFO] 10/01/2025 Boot`                       | INFO, `FECHA_INVALIDA` (formato no ISO)  |
| CA6  | `[INFO] 2025-01-10 25:61:00 Boot`              | INFO, `FECHA_INVALIDA` (hora imposible)  |
| CA7  | `[ERROR] 2025-01-10`                           | ERROR, `SIN_MENSAJE`                     |
| CA8  | `[DEBUG] 2025-01-10 Cache hit`                 | DESCONOCIDO, `NIVEL_DESCONOCIDO`         |
| CA9  | `User logged out`                              | DESCONOCIDO, `SIN_NIVEL`                 |
| CA10 | `· [info] 2025-01-10 ok`                       | INFO, `VALIDA` (viñeta y minúsculas)     |
| CA11 | línea vacía                                    | ignorada, no cuenta como evento          |
| CA12 | archivo inexistente                            | mensaje de error, código de salida 1     |
| CA13 | archivo vacío                                  | resumen con todo a 0 y `El archivo no contiene eventos.` |
| CA14 | `[WARNING] 10.0.0.1 blocked`                   | WARNING, `SIN_FECHA` (una IP no es una fecha) |
| CA15 | archivo UTF-16 con BOM                         | se lee igual que el mismo contenido en UTF-8 |
| CA16 | archivo binario                                | mensaje de error, código de salida 1     |
| CA17 | línea con `ESC[2J` en el detalle               | se muestra como `\x1b[2J`                |
| CA18 | archivo con más de 50 líneas con problemas     | detalle con 50 líneas + `... y N lineas mas` |
| CA19 | ruta `~/archivo.log`                           | se expande a la carpeta del usuario      |
| CA20 | `--gui` sin entorno gráfico                    | aviso y se pide la ruta por teclado      |
| CA21 | Ctrl+C durante el análisis                     | `Analisis cancelado.`, código 130        |

## 7. Edge cases pendientes (decisión abierta)

Casos detectados en la evaluación de edge cases cuyo resultado **cumple esta spec** pero es
discutible. Se dejan **sin cambiar a propósito**. Las pruebas de
`TestEdgeCasesPendientes` (`tests/test_parser.py`) fijan el comportamiento actual: si
alguien lo cambia sin actualizar esta sección, las pruebas fallan.

| ID  | Línea                              | Resultado actual | Por qué es discutible | Opción si se acepta |
|-----|------------------------------------|------------------|-----------------------|---------------------|
| EP1 | `[ERROR]: 2025-01-10 x`            | ERROR, `SIN_FECHA` | La fecha existe, pero el `:` pegado a la etiqueta queda como primer token y la desplaza. | Tolerar `:` justo después de `]`, como ya se toleran las viñetas. |
| EP2 | `[INFO] 2025-01-10T10:00:00 x`     | INFO, `FECHA_INVALIDA` | Es ISO 8601 válido; la sección 2 solo admite `AAAA-MM-DD [HH:MM:SS]` separados por espacio. | Aceptar `T` como separador entre fecha y hora. |
| EP3 | `[INFO] 2025-01-10 08:00:00.123 x` | INFO, `FECHA_INVALIDA` | Los milisegundos (`.123` o `,123`) son habituales en logs reales (Java, Python `logging`). | Aceptar `HH:MM:SS.fff` y `HH:MM:SS,fff`. |
| EP4 | `[DEBUG] 2025-01-11 Query executed in 12ms` | DESCONOCIDO, `NIVEL_DESCONOCIDO`; la etiqueta `DEBUG` no aparece en el resumen ni en el motivo del detalle (solo en el texto crudo de la línea) | **Mejora no contemplada**, no un resultado discutible: la clasificación es correcta (el enunciado solo define INFO, WARNING y ERROR), pero con muchos `[DEBUG]`, `[FATAL]`, `[WARN]`... mezclados el resumen no dice cuántos hay de cada uno. | Sin cambiar la clasificación: mostrar `Nivel desconocido (DEBUG)` en el detalle y listar en el resumen las etiquetas no reconocidas con su cantidad (RF3/RF4). **No** aceptar `DEBUG` como nivel válido: contradice el enunciado. |

Para resolver uno: se mueve a la sección 6 como criterio de aceptación, se ajusta la
sección 2 (o RF3/RF4 en el caso de EP4) y se actualiza su prueba.

## 8. Fuera de alcance

- Filtros por rango de fechas, exportar a CSV/JSON, lectura en tiempo real (`tail -f`).
