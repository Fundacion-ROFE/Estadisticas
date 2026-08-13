# -*- coding: utf-8 -*-
"""
backfill_ciudad_seguimiento_historico.py — rellena la UBICACIÓN (grupo_ciudad + ciudad) de los
participantes JC que hoy la tienen vacía, usando un SNAPSHOT VIEJO exportado de la BD de
Seguimiento (CSV). El Sheet vivo ya no trae a esta gente (el equipo los borra al retirarse),
así que `sync_sociodemograficos.py` no puede recuperar su ciudad y quedan "sin ubicación".
Samuel encontró un export anterior que sí los tiene → esta carga puntual los reubica.

Contexto (2026-08-13): 64 participantes sin `grupo_ciudad`. El CSV JC2026 (832 filas) los
cubre a los 64 por cédula. Ver docs/procesos/panel-control-jc-mr.md.

REGLAS DURAS:
  • Solo se ESCRIBE donde el campo está vacío — nunca se sobrescribe un valor existente.
  • Cruce por cédula (ID) primero, correo (E-mail) como respaldo.
  • NO se toca `en_seguimiento_jc`: este CSV es un snapshot VIEJO; estar en él no significa
    que la persona siga vigente en Seguimiento. Solo se escribe grupo_ciudad + ciudad.
  • `ciudad_norm` es columna generada en Postgres → se recalcula sola al escribir `ciudad`.
  • Al final se llama recompute_aggregates (igual que sync_sociodemograficos.py).

Uso:
    python backfill_ciudad_seguimiento_historico.py --dry-run   # preview, no escribe
    python backfill_ciudad_seguimiento_historico.py             # aplica

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import csv
import io
import os
import re
import sys
from collections import Counter, defaultdict

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIRECTORIO_SCRIPT)
from cargar_supabase import Supa, cargar_env_local  # noqa: E402

RUTA_CSV_DEFAULT = r"C:\Users\EstudiantesJC\Downloads\BD Seguimiento de Monitorias - JC2026 - Seguimiento (3).csv"


def log(m): print(f"[backfill-ciudad] {m}", flush=True)


def norm_ced(v): return re.sub(r"\D", "", str(v or "")).lstrip("0")
def norm_email(v):
    s = str(v or "").strip().lower()
    m = re.search(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", s)
    return m.group(0) if m else ""


def leer_csv(ruta):
    """Parsea por NOMBRE de encabezado (el orden de columnas del export difiere del Sheet vivo).
    Devuelve (by_ced, by_email) con {clave: {grupo_ciudad, ciudad}}."""
    with open(ruta, encoding="utf-8-sig", newline="") as fh:
        filas = list(csv.DictReader(fh))
    by_ced, by_email = {}, {}
    for r in filas:
        R = {(k or "").strip(): (v or "") for k, v in r.items()}
        rec = {
            "grupo_ciudad": (R.get("Grupo") or "").strip() or None,
            "ciudad": (R.get("Ciudad") or "").strip() or None,
        }
        if not (rec["grupo_ciudad"] or rec["ciudad"]):
            continue
        ced = norm_ced(R.get("ID"))
        em = norm_email(R.get("E-mail"))
        if ced:
            by_ced.setdefault(ced, rec)
        if em:
            by_email.setdefault(em, rec)
    log(f"CSV: {len(filas)} filas · índices cédula={len(by_ced)} correo={len(by_email)}")
    return by_ced, by_email


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--csv", default=RUTA_CSV_DEFAULT)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    supa = Supa(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])
    by_ced, by_email = leer_csv(args.csv)

    parts = supa.get_todo("/participants?select=q10_id,nombre,email,ciudad,grupo_ciudad")

    def vacio(v): return v is None or str(v).strip() == ""

    # Payloads agrupados por (grupo,ciudad,campos) → un PATCH por grupo con q10_id=in.(...)
    grupos = defaultdict(list)   # (grupo, ciudad, campos) -> [q10_id]
    por_grupo_ciudad = Counter()
    sin_match = 0
    for p in parts:
        falta_grupo = vacio(p.get("grupo_ciudad"))
        falta_ciudad = vacio(p.get("ciudad"))
        if not (falta_grupo or falta_ciudad):
            continue
        c = norm_ced(p.get("q10_id"))
        e = norm_email(p.get("email"))
        rec = by_ced.get(c) or by_email.get(e)
        if not rec:
            sin_match += 1
            continue
        payload = {}
        if falta_grupo and rec["grupo_ciudad"]:
            payload["grupo_ciudad"] = rec["grupo_ciudad"]
        if falta_ciudad and rec["ciudad"]:
            payload["ciudad"] = rec["ciudad"]
        if not payload:
            continue
        clave = (payload.get("grupo_ciudad"), payload.get("ciudad"), frozenset(payload))
        grupos[clave].append(p["q10_id"])
        por_grupo_ciudad[rec["grupo_ciudad"] or "—"] += 1

    total = sum(len(ids) for ids in grupos.values())
    log(f"Participantes a rellenar: {total} · sin match en el CSV (se dejan como están): {sin_match}")
    print("\nPor grupo de ciudad:")
    for g, n in por_grupo_ciudad.most_common():
        print(f"  {g:<6} {n}")

    if args.dry_run:
        log("DRY-RUN: no se escribió nada. Corré sin --dry-run para aplicar.")
        return 0

    escritos = 0
    for (grupo, ciudad, campos), ids in grupos.items():
        payload = {}
        if "grupo_ciudad" in campos:
            payload["grupo_ciudad"] = grupo
        if "ciudad" in campos:
            payload["ciudad"] = ciudad
        # PATCH: solo UPDATE (no inserta) → sin riesgo de NOT NULL; y reforzamos el "solo vacíos"
        # con filtros en el propio WHERE para que sea idempotente aunque se re-corra.
        for i in range(0, len(ids), 100):
            lote = ids[i:i + 100]
            filtro = "q10_id=in.(%s)" % ",".join(lote)
            if "grupo_ciudad" in campos:
                filtro += "&grupo_ciudad=is.null"
            if "ciudad" in campos:
                filtro += "&ciudad=is.null"
            supa._req("PATCH", f"/participants?{filtro}", payload,
                      prefer="return=minimal")
            escritos += len(lote)
    log(f"PATCH aplicado a {escritos} participantes (solo campos vacíos).")

    st, _ = supa._req("POST", "/rpc/recompute_aggregates", {})
    log(f"recompute_aggregates → HTTP {st}")
    log("Listo. ciudad_norm se recalculó solo (columna generada).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
