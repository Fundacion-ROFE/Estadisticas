# -*- coding: utf-8 -*-
"""
respaldo_supabase.py — Respaldo local completo de las tablas base de Supabase
(proyecto panel-datos-rofe, kbxptoowtnteflhrfwid).

Recorre TODAS las tablas base del esquema public (NO vistas) con el paginador ya
probado de cargar_supabase.py (Supa.get_todo) usando SUPABASE_SERVICE_ROLE_KEY, y
escribe un volcado JSON por tabla + un _resumen.json con conteos.

  tools/backups/supabase_YYYYMMDD_HHMM/<tabla>.json
  tools/backups/supabase_YYYYMMDD_HHMM/_resumen.json

Motivación: Supabase free tier no tiene PITR; las series historial_* y los snapshots
NO son reconstruibles desde las fuentes. Este respaldo local cubre ese hueco. tools/
está gitignoreado → la PII nunca sale del PC.

Retención: borra carpetas supabase_* de más de RETENCION_DIAS días.

Uso:
    python respaldo_supabase.py            # respaldo real
    python respaldo_supabase.py --dry-run  # solo lista tablas/destino, no conecta ni escribe
Consola (parseable por n8n):
    RESUMEN: tablas=N filas=M estado=exito|error

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime, timedelta

try:
    import truststore
    truststore.inject_into_ssl()  # SSL corporativo (convención del proyecto)
except ImportError:
    pass

# Reutilizamos el cliente REST y el loader ya probados (no reescribir el paginador).
from cargar_supabase import Supa, cargar_env_local, PROYECTO_ROOT

# Tablas base del esquema public — lista autoritativa (list_tables 2026-07-24, 25 tablas).
# NO incluye vistas (v_*) ni materializaciones derivadas: solo lo que hay que respaldar.
TABLAS_BASE = [
    "participants",
    "courses",
    "enrollments",
    "participant_metrics",
    "cohorte_stats",
    "cohorte_ingresos",
    "aprobacion_cursos",
    "participants_snapshots",
    "historial_cursos",
    "historial_cursos_ciudad",
    "asistencia_zoom",
    "asistencia_promedio",
    "emoflow_ingresos",
    "emoflow_ingresos_diario",
    "emoflow_actividad_semanal",
    "historial_emoflow",
    "historial_emoflow_ciudad",
    "emoflow_participacion_semanal",
    "postulantes_mr",
    "postulantes_jc",
    "retiros",
    "email_optout",
    "email_bounces",
    "campanas_enviadas",
    "alertas_datos",
]

RETENCION_DIAS = 14
DIR_BACKUPS = os.path.join(PROYECTO_ROOT, "tools", "backups")


def log(msg: str) -> None:
    print(f"[respaldo-supabase] {msg}", flush=True)


def purgar_antiguos() -> int:
    """Borra carpetas supabase_YYYYMMDD_HHMM de más de RETENCION_DIAS días."""
    if not os.path.isdir(DIR_BACKUPS):
        return 0
    limite = datetime.now() - timedelta(days=RETENCION_DIAS)
    borradas = 0
    for nombre in os.listdir(DIR_BACKUPS):
        if not nombre.startswith("supabase_"):
            continue
        ruta = os.path.join(DIR_BACKUPS, nombre)
        if not os.path.isdir(ruta):
            continue
        # fecha del nombre: supabase_YYYYMMDD_HHMM
        try:
            fecha = datetime.strptime(nombre[len("supabase_"):], "%Y%m%d_%H%M")
        except ValueError:
            continue  # nombre no estándar → no tocar
        if fecha < limite:
            shutil.rmtree(ruta, ignore_errors=True)
            borradas += 1
            log(f"retención: borrada {nombre}")
    return borradas


def main() -> int:
    ap = argparse.ArgumentParser(description="Respaldo local de tablas base de Supabase")
    ap.add_argument("--dry-run", action="store_true",
                    help="Solo lista tablas y destino; no conecta ni escribe")
    args = ap.parse_args()

    sello = datetime.now().strftime("%Y%m%d_%H%M")
    dir_destino = os.path.join(DIR_BACKUPS, f"supabase_{sello}")

    if args.dry_run:
        log(f"[DRY-RUN] {len(TABLAS_BASE)} tablas → {dir_destino}")
        for t in TABLAS_BASE:
            log(f"[DRY-RUN]   - {t}.json")
        log(f"[DRY-RUN] retención: carpetas > {RETENCION_DIAS} días serían purgadas")
        print(f"RESUMEN: tablas={len(TABLAS_BASE)} filas=0 estado=exito")
        return 0

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (.env.local o entorno)")
        print("RESUMEN: tablas=0 filas=0 estado=error detalle=faltan_credenciales")
        return 1

    supa = Supa(url, key)
    os.makedirs(dir_destino, exist_ok=True)

    conteos = {}
    total_filas = 0
    fallidas = []
    for tabla in TABLAS_BASE:
        try:
            filas = supa.get_todo(f"/{tabla}?select=*")
        except Exception as e:  # cualquier fallo de red/HTTP → la tabla NO se respaldó
            log(f"ERROR respaldando {tabla}: {e}")
            fallidas.append(tabla)
            continue
        ruta = os.path.join(dir_destino, f"{tabla}.json")
        with open(ruta, "w", encoding="utf-8") as f:
            json.dump(filas, f, ensure_ascii=False)
        conteos[tabla] = len(filas)
        total_filas += len(filas)
        log(f"{tabla}: {len(filas)} filas")

    resumen = {
        "sello": sello,
        "generado": datetime.now().isoformat(timespec="seconds"),
        "proyecto": "kbxptoowtnteflhrfwid",
        "tablas_ok": conteos,
        "tablas_fallidas": fallidas,
        "total_filas": total_filas,
    }
    with open(os.path.join(dir_destino, "_resumen.json"), "w", encoding="utf-8") as f:
        json.dump(resumen, f, ensure_ascii=False, indent=2)

    purgar_antiguos()

    if fallidas:
        print(f"RESUMEN: tablas={len(conteos)} filas={total_filas} "
              f"estado=error detalle=fallaron:{','.join(fallidas)}")
        return 1
    print(f"RESUMEN: tablas={len(conteos)} filas={total_filas} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
