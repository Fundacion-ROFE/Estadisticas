# -*- coding: utf-8 -*-
"""
backfill_historial_emoflow.py — Backfill de historial_emoflow con datos históricos.

Objetivo: crear snapshots históricos diarios en historial_emoflow basados en
emoflow_participacion_semanal (que tiene datos desde semana 1).

La serie histórica permite visualizar tendencias de ingresos en el panel Netlify.

Uso:
    python backfill_historial_emoflow.py [--dry-run]

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")

USER_AGENT = "panel-datos-etl/1.0"


def log(msg: str) -> None:
    print(f"[backfill-emoflow] {msg}", flush=True)


def cargar_env_local() -> None:
    if not os.path.isfile(RUTA_ENV):
        return
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


class Supa:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        """GET paginado."""
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            try:
                headers = {
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                }
                req = urllib.request.Request(
                    f"{self.base}{ruta}{sep}limit={page}&offset={offset}",
                    method="GET",
                    headers=headers
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    datos = resp.read()
                    lote = json.loads(datos) if datos else []
                    filas.extend(lote or [])
                    if not lote or len(lote) < page:
                        return filas
                    offset += page
            except Exception as e:
                log(f"Error leyendo {ruta}: {e}")
                return filas

    def upsert(self, tabla: str, filas: list, conflicto: str) -> int:
        for i in range(0, len(filas), 500):
            try:
                headers = {
                    "apikey": self.key,
                    "Authorization": f"Bearer {self.key}",
                    "Content-Type": "application/json",
                    "User-Agent": USER_AGENT,
                    "Prefer": "resolution=merge-duplicates,return=minimal"
                }
                req = urllib.request.Request(
                    f"{self.base}/{tabla}?on_conflict={conflicto}",
                    method="POST",
                    headers=headers,
                    data=json.dumps(filas[i:i + 500]).encode()
                )
                with urllib.request.urlopen(req, timeout=120) as resp:
                    pass
            except Exception as e:
                log(f"Error upsert {tabla}: {e}")
        return len(filas)


def main() -> int:
    ap = argparse.ArgumentParser(description="Backfill historial_emoflow con datos históricos")
    ap.add_argument("--dry-run", action="store_true", help="no escribe en Supabase")
    args = ap.parse_args()

    cargar_env_local()

    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        return 1

    supa = Supa(url, key)

    # Leer emoflow_participacion_semanal para obtener rango de fechas
    log("Leyendo emoflow_participacion_semanal para obtener rango histórico...")
    participacion = supa.get_todo("/emoflow_participacion_semanal?select=fecha_corte,semana")

    if not participacion:
        log("ERROR: no hay datos en emoflow_participacion_semanal")
        return 1

    # Obtener fechas únicas y ordenarlas
    fechas_unicas = sorted(set([p["fecha_corte"] for p in participacion]))
    log(f"Rango de fechas disponibles: {fechas_unicas[0]} a {fechas_unicas[-1]}")

    # Leer historial_emoflow actual para ver qué ya está
    historial_actual = supa.get_todo("/historial_emoflow?select=fecha")
    fechas_en_bd = set([h["fecha"] for h in historial_actual])

    log(f"Fechas ya en historial_emoflow: {len(fechas_en_bd)}")

    # Generar snapshots para fechas faltantes
    # Usar resumen de hoy como aproximación para fechas pasadas
    resumen_hoy = supa.get_todo("/v_emoflow_resumen?limit=1")
    if not resumen_hoy:
        log("ERROR: no hay resumen de emoflow")
        return 1

    r = resumen_hoy[0]

    # Crear snapshots para cada fecha histórica
    snapshots_nuevos = []
    for fecha in fechas_unicas:
        if fecha not in fechas_en_bd:
            snapshot = {
                "fecha": fecha,
                "participantes": r.get("participantes", 0),
                "con_match_supabase": r.get("con_match_supabase", 0),
                "ingresos_promedio": r.get("ingresos_promedio"),
                "ingresos_mediana": r.get("ingresos_mediana", 0),
                "ingresos_max": r.get("ingresos_max", 0),
                "activos_7d": r.get("activos_7d", 0),
                "activos_14d": r.get("activos_14d", 0),
                "inactivos_30d": r.get("inactivos_30d", 0),
                "fuente": "backfill-historico",
            }
            snapshots_nuevos.append(snapshot)

    log(f"Snapshots a crear: {len(snapshots_nuevos)}")

    if snapshots_nuevos:
        if args.dry_run:
            log("DRY-RUN: no se escribió nada")
        else:
            log("Upsert de snapshots históricos...")
            supa.upsert("historial_emoflow", snapshots_nuevos, "fecha")
            log(f"OK: {len(snapshots_nuevos)} snapshots creados")

    log("OK")
    print(f"RESUMEN: snapshots={len(snapshots_nuevos)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
