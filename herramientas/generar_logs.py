"""Genera archivos de logs sintéticos de cualquier tamaño (RD3).

Uso:
    python herramientas/generar_logs.py SALIDA.log --lineas 100000 --errores 0.15 --semilla 42

Además del log escribe SALIDA.esperado.json con los conteos que el analizador
DEBERÍA obtener. Esos conteos se calculan aquí a partir de lo que se generó,
sin usar el analizador: si se usara, la comparación no probaría nada.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path

# Mensajes con la forma habitual de una aplicación web (usuarios, rutas, IPs, excepciones).
MENSAJES = {
    "INFO": [
        "User {u} logged in from 10.0.{a}.{b}",
        "GET /api/v1/orders/{n} HTTP/1.1 status: 200 time: 0.{n}s",
        "Scheduled job 'cleanup-sessions' finished in {n} ms",
        "Cache warmed up with {n} entries",
        "Connection pool resized to {a} connections",
        "Payment {n} authorized for user {u}",
    ],
    "WARNING": [
        "Invalid password attempt for user {u}",
        "Response time above threshold: {n} ms on /api/v1/search",
        "Disk usage at {a}% on /var/log",
        "Retrying request to inventory-service (attempt {b}/5)",
        "Deprecated API version v1 called by client {u}",
    ],
    "ERROR": [
        "Failed to connect to database db-{b}.internal:5432 (timeout)",
        "NullPointerException in OrderService.process(OrderService.java:{n})",
        "Payment gateway returned HTTP 502 for transaction {n}",
        "Could not write to /var/data/uploads: No space left on device",
        "Unhandled exception in worker-{b}: KeyError 'customer_id'",
    ],
}
USUARIOS = ["alice", "bob", "carlos", "diana", "eve", "fatima", "gabriel", "sofia"]
PESOS_NIVEL = {"INFO": 70, "WARNING": 20, "ERROR": 10}

# Tipos de defecto -> (nivel esperado en el resumen, estado esperado).
# Los nombres de estado coinciden con analizador_logs.parser.Estado.
DEFECTOS = [
    "sin_fecha", "fecha_imposible", "fecha_formato", "hora_imposible",
    "sin_mensaje", "nivel_desconocido", "sin_nivel", "vacia",
]


def _mensaje(rng: random.Random, nivel: str) -> str:
    return rng.choice(MENSAJES[nivel]).format(
        u=rng.choice(USUARIOS), n=rng.randint(1, 99999),
        a=rng.randint(1, 99), b=rng.randint(1, 9),
    )


def generar(salida: Path, lineas: int, tasa_errores: float, semilla: int) -> dict:
    rng = random.Random(semilla)  # instancia propia: reproducible (CD7)
    niveles = list(PESOS_NIVEL)
    pesos = list(PESOS_NIVEL.values())
    momento = datetime(2025, 1, 1)

    por_nivel: Counter = Counter()
    por_estado: Counter = Counter()
    vacias = 0

    with salida.open("w", encoding="utf-8", newline="\n") as f:
        for _ in range(lineas):
            momento += timedelta(seconds=rng.randint(0, 30))
            fecha = momento.strftime("%Y-%m-%d %H:%M:%S")
            nivel = rng.choices(niveles, pesos)[0]
            mensaje = _mensaje(rng, nivel)

            if rng.random() >= tasa_errores:
                f.write(f"[{nivel}] {fecha} {mensaje}\n")
                por_nivel[nivel] += 1
                por_estado["VALIDA"] += 1
                continue

            defecto = rng.choice(DEFECTOS)
            if defecto == "vacia":
                f.write("\n")
                vacias += 1
                continue
            if defecto == "sin_fecha":
                linea, n, e = f"[{nivel}] {mensaje}", nivel, "SIN_FECHA"
            elif defecto == "fecha_imposible":
                linea, n, e = f"[{nivel}] 2025-{rng.randint(13, 99)}-{rng.randint(32, 99)} {mensaje}", nivel, "FECHA_INVALIDA"
            elif defecto == "fecha_formato":
                linea, n, e = f"[{nivel}] {momento:%d/%m/%Y} {mensaje}", nivel, "FECHA_INVALIDA"
            elif defecto == "hora_imposible":
                linea, n, e = f"[{nivel}] {momento:%Y-%m-%d} {rng.randint(24, 99)}:{rng.randint(60, 99)}:00 {mensaje}", nivel, "FECHA_INVALIDA"
            elif defecto == "sin_mensaje":
                linea, n, e = f"[{nivel}] {fecha}", nivel, "SIN_MENSAJE"
            elif defecto == "nivel_desconocido":
                otro = rng.choice(["DEBUG", "TRACE", "FATAL", "CRITICAL", "WARN"])
                linea, n, e = f"[{otro}] {fecha} {mensaje}", "DESCONOCIDO", "NIVEL_DESCONOCIDO"
            else:  # sin_nivel
                linea, n, e = f"{fecha} {nivel} {mensaje}", "DESCONOCIDO", "SIN_NIVEL"
            f.write(linea + "\n")
            por_nivel[n] += 1
            por_estado[e] += 1

    esperado = {
        "semilla": semilla,
        "tasa_errores": tasa_errores,
        "lineas_escritas": lineas,
        "total_eventos": sum(por_estado.values()),
        "lineas_vacias": vacias,
        "por_nivel": dict(sorted(por_nivel.items())),
        "por_estado": dict(sorted(por_estado.items())),
        "mal_formateadas_o_incompletas": sum(v for k, v in por_estado.items() if k != "VALIDA"),
    }
    salida.with_suffix(".esperado.json").write_text(
        json.dumps(esperado, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return esperado


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="Genera logs sintéticos con errores controlados.")
    p.add_argument("salida", type=Path)
    p.add_argument("--lineas", type=int, default=10_000)
    p.add_argument("--errores", type=float, default=0.15,
                   help="fracción de líneas defectuosas, entre 0 y 1 (defecto 0.15)")
    p.add_argument("--semilla", type=int, default=42)
    args = p.parse_args(argv)
    if not 0 <= args.errores <= 1 or args.lineas < 0:
        p.error("--errores debe estar entre 0 y 1 y --lineas no puede ser negativo")
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    esperado = generar(args.salida, args.lineas, args.errores, args.semilla)
    print(f"{args.salida}: {args.lineas} lineas, "
          f"{esperado['mal_formateadas_o_incompletas']} con problemas, "
          f"{esperado['lineas_vacias']} vacias")
    return 0


if __name__ == "__main__":
    sys.exit(main())
