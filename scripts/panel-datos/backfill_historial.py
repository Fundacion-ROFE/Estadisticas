# -*- coding: utf-8 -*-
"""
backfill_historial.py — Carga histórica única: docs/dashboard/history.json → historial_cursos.

history.json (snapshots del dashboard GitHub Pages desde 2026-06-26) trae por fecha y
programa (jc/mr): curso, estudiantes (matriculados) y promedio. NO trae completados →
queda NULL en el backfill (el sync diario sí lo llena de 2026-07-10 en adelante).

Idempotente: UNIQUE(fecha, curso) + upsert. Uso único (re-ejecutable sin daño).

Uso: python backfill_historial.py [--dry-run]
"""

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_HISTORY      = os.path.join(PROYECTO_ROOT, "docs", "dashboard", "history.json")
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
USER_AGENT        = "panel-datos-etl/1.0"


def log(m):
    print(f"[backfill-historial] {m}", flush=True)


def cargar_env():
    if os.path.isfile(RUTA_ENV):
        with open(RUTA_ENV, encoding="utf-8") as f:
            for linea in f:
                if "=" in linea and not linea.startswith("#"):
                    k, v = linea.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env()
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales")
        return 1

    with open(RUTA_HISTORY, encoding="utf-8") as f:
        history = json.load(f)

    filas = []
    for snap in history:
        fecha = snap["fecha"]
        for prog in ("jc", "mr"):
            for c in snap.get(prog, {}).get("por_curso", []):
                filas.append({
                    "fecha": fecha,
                    "curso": c["curso"],
                    "programa": prog,
                    "matriculados": c["estudiantes"],
                    "promedio_avance": c["promedio"],
                    "completados": None,        # history.json no lo registra
                    "fuente": "backfill-history.json",
                })
    log(f"{len(history)} snapshots → {len(filas)} filas (desde {history[0]['fecha']})")

    if args.dry_run:
        print(f"RESUMEN: filas={len(filas)} estado=dry_run")
        return 0

    req = urllib.request.Request(
        f"{url}/rest/v1/historial_cursos?on_conflict=fecha,curso",
        method="POST",
        headers={"apikey": key, "Authorization": f"Bearer {key}",
                 "Content-Type": "application/json", "User-Agent": USER_AGENT,
                 "Prefer": "resolution=merge-duplicates,return=minimal"},
        data=json.dumps(filas).encode())
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            log(f"Upsert OK (HTTP {resp.status})")
    except urllib.error.HTTPError as e:
        log(f"ERROR HTTP {e.code}: {e.read().decode(errors='replace')[:400]}")
        return 1

    print(f"RESUMEN: filas={len(filas)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
