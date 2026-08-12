# -*- coding: utf-8 -*-
"""
cargar_enriquecimiento.py — Carga idempotente de los payloads de la etapa final de
enriquecimiento histórico (clústeres A/B/C/F) a las tablas nuevas en Supabase.

Filtros de privacidad/calidad (decisión explícita del usuario 2026-08-12):
  1. SOLO se carga si el `canon` (cédula normalizada) corresponde a una persona que
     YA es un `participant` real en Supabase (matriculó alguna vez). NO basta con
     estar en `postulantes_jc`/`postulantes_mr` (universo que incluye postulantes
     NUNCA seleccionados) — cuidado explícito de no sobre-almacenar PII de gente
     sin relación real con el programa.
  2. Se EXCLUYE todo registro con metodo_match == 'nombre' (riesgo de homónimos);
     queda solo en el JSON fuente para revisión manual, nunca entra a Supabase.

Requiere las tablas de la migración `docs/migrations/045_enriquecimiento_historico_tablas.sql`
ya aplicadas (crear vía MCP Supabase o `apply_migration`).

Uso:
    python cargar_enriquecimiento.py --dry-run     # solo cuenta, no escribe nada
    python cargar_enriquecimiento.py               # carga de verdad (upsert idempotente)
    python cargar_enriquecimiento.py --solo A       # limita a un clúster (A/B/C/F)
"""

import argparse
import json
import os
import sys

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
ENRIQ_DIR = os.path.join(PROYECTO_ROOT, "tools", "enriquecimiento")
sys.path.insert(0, DIRECTORIO_SCRIPT)

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = __import__("io").TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from enriquecimiento_helper import norm_cedula  # noqa: E402

# clúster → (archivo json, tabla destino, columnas de fuente, columnas conflicto)
CLUSTERS = {
    "A": {
        "json": "A_socioeconomico.json", "tabla": "enriquecimiento_socioeconomico",
        "conflicto": "participant_id,campo,fuente_archivo,hoja,anio,valor",
    },
    "B": {
        "json": "B_empleabilidad.json", "tabla": "enriquecimiento_empleabilidad",
        "conflicto": "participant_id,campo,fuente_archivo,hoja,anio,valor",
    },
    "C": {
        "json": "C_resultados.json", "tabla": "enriquecimiento_resultados",
        "conflicto": "participant_id,campo,fuente_archivo,hoja,anio,valor",
    },
    "F": {
        "json": "F_mr_extendido.json", "tabla": "enriquecimiento_mr_extendido",
        "conflicto": "participant_id,campo,fuente_archivo,valor",
    },
}


def log(msg):
    print(f"[cargar-enriq] {msg}", flush=True)


def construir_mapa_participantes(supa):
    """cédula normalizada → participant_id (solo participants reales, q10_id no nulo)."""
    filas = supa.get_todo("/participants?select=id,q10_id&q10_id=not.is.null")
    mapa = {}
    for r in filas:
        c = norm_cedula(r["q10_id"])
        if c:
            mapa[c] = r["id"]
    return mapa


def procesar_cluster(clave, cfg, mapa_participantes, dry_run):
    ruta = os.path.join(ENRIQ_DIR, cfg["json"])
    if not os.path.isfile(ruta):
        log(f"{clave}: NO existe {ruta}, se salta")
        return None
    with open(ruta, encoding="utf-8") as fh:
        registros = json.load(fh)

    n_total = len(registros)
    n_sin_valor = n_excl_metodo = n_excl_no_participante = 0
    filas_cargar = []
    vistos = set()
    personas = set()

    for r in registros:
        if not r.get("valor"):
            n_sin_valor += 1
            continue
        metodo = r.get("metodo_match")
        if metodo not in ("cedula", "email"):
            n_excl_metodo += 1
            continue
        canon = norm_cedula(r.get("canon") or "")
        pid = mapa_participantes.get(canon)
        if not pid:
            n_excl_no_participante += 1
            continue

        fuente_archivo = r.get("fuente_archivo") or r.get("fuente") or ""
        fila = {
            "participant_id": pid,
            "campo": r["campo"],
            "valor": str(r["valor"])[:2000],
            "fuente_archivo": fuente_archivo,
            "metodo_match": metodo,
        }
        if clave != "F":
            fila["hoja"] = r.get("hoja") or ""
            fila["anio"] = str(r.get("anio") or "")
        if clave == "C" and r.get("nombre_crudo"):
            fila["nombre_crudo"] = r["nombre_crudo"]

        clave_dedup = (pid, fila["campo"], fuente_archivo, fila.get("hoja", ""), fila.get("anio", ""), fila["valor"])
        if clave_dedup in vistos:
            continue
        vistos.add(clave_dedup)
        filas_cargar.append(fila)
        personas.add(pid)

    log(f"{clave} ({cfg['tabla']}): {n_total} leídos · sin_valor={n_sin_valor} · "
        f"excluidos_match_nombre={n_excl_metodo} · excluidos_no_participante_real={n_excl_no_participante} · "
        f"A CARGAR={len(filas_cargar)} ({len(personas)} personas)")

    if dry_run or not filas_cargar:
        return len(filas_cargar)

    sys.path.insert(0, DIRECTORIO_SCRIPT)
    from cargar_supabase import Supa, cargar_env_local  # noqa: E402 (ya cargado arriba, re-import barato)
    cargar_env_local()
    supa = Supa(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    n = supa.upsert(cfg["tabla"], filas_cargar, cfg["conflicto"])
    log(f"{clave}: {n} filas enviadas (upsert idempotente) a {cfg['tabla']}")
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo cuenta, no escribe en Supabase")
    ap.add_argument("--solo", choices=list(CLUSTERS), help="limitar a un clúster")
    args = ap.parse_args()

    from cargar_supabase import Supa, cargar_env_local
    cargar_env_local()
    supa = Supa(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    log("Construyendo mapa de participantes reales (cédula → participant_id)...")
    mapa = construir_mapa_participantes(supa)
    log(f"{len(mapa)} participantes reales conocidos por cédula")

    claves = [args.solo] if args.solo else list(CLUSTERS)
    for clave in claves:
        procesar_cluster(clave, CLUSTERS[clave], mapa, args.dry_run)

    if args.dry_run:
        log("DRY-RUN: no se escribió nada en Supabase.")


if __name__ == "__main__":
    main()
