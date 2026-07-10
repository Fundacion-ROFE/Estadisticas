# -*- coding: utf-8 -*-
"""
test_cuadre_dashboard.py — Fase 4: cuadre Supabase ↔ dashboard GitHub Pages.

Compara, por curso, la vista pública v_curso_completion (Supabase, anon key)
contra docs/aprobacion/data.json (fuente canónica del dashboard actual):
  - matriculados (Supabase)  ==  activos (aprobación)     [misma población: h2test]
  - completados  (Supabase)  ==  aprobados (aprobación)   [mismo criterio: avance > 80]

Diferencias esperadas y aceptadas:
  - aprobación trae además la cohorte completa (cursaron/retirados) — Supabase
    hoy solo tiene activos; NO se compara cursaron.
  - Si los snapshots son de corridas distintas (horas de diferencia), tolerancia ±2.

Uso:  python test_cuadre_dashboard.py
Exit 0 = todo cuadra (± tolerancia) · 1 = hay descuadres.
"""

import io
import json
import os
import re
import sys
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
RUTA_APROBACION   = os.path.join(PROYECTO_ROOT, "docs", "aprobacion", "data.json")
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
TOLERANCIA        = 2   # corridas a horas distintas mueven 1-2 matrículas


def norm(nombre: str) -> str:
    return re.sub(r"\s+", " ", str(nombre).replace("\xa0", " ")).strip().upper()


def cargar_env():
    if os.path.isfile(RUTA_ENV):
        with open(RUTA_ENV, encoding="utf-8") as f:
            for linea in f:
                if "=" in linea and not linea.startswith("#"):
                    k, v = linea.strip().split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip())


def main() -> int:
    cargar_env()
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    req = urllib.request.Request(
        f"{url}/rest/v1/v_curso_completion?select=*",
        headers={"apikey": key, "Authorization": f"Bearer {key}"})
    with urllib.request.urlopen(req, timeout=30) as r:
        supabase = {norm(f["curso"]): f for f in json.load(r)}

    with open(RUTA_APROBACION, encoding="utf-8") as f:
        aprobacion = {norm(c["curso"]): c for c in json.load(f)["por_curso"]}

    fallos, comparados = [], 0
    print(f"{'Curso':<42} {'activos A/S':>12} {'aprobados A/S':>14}  estado")
    print("-" * 78)
    for curso, sb in sorted(supabase.items()):
        ap = aprobacion.get(curso)
        if ap is None:
            print(f"{curso[:40]:<42} {'—':>12} {'—':>14}  SOLO EN SUPABASE (¿curso MR sin cohorte?)")
            continue
        comparados += 1
        d_act = abs(ap["activos"] - sb["matriculados"])
        d_apr = abs(ap["aprobados"] - sb["completados"])
        ok = d_act <= TOLERANCIA and d_apr <= TOLERANCIA
        if not ok:
            fallos.append(curso)
        print(f"{curso[:40]:<42} {ap['activos']:>5}/{sb['matriculados']:<6} "
              f"{ap['aprobados']:>6}/{sb['completados']:<7}  {'OK' if ok else 'DESCUADRE'}")

    solo_ap = set(aprobacion) - set(supabase)
    for c in sorted(solo_ap):
        print(f"{c[:40]:<42} {'—':>12} {'—':>14}  SOLO EN APROBACIÓN")

    print("-" * 78)
    estado = "exito" if not fallos else "descuadre"
    print(f"RESUMEN: comparados={comparados} descuadres={len(fallos)} "
          f"solo_supabase={len(set(supabase) - set(aprobacion))} "
          f"solo_aprobacion={len(solo_ap)} tolerancia={TOLERANCIA} estado={estado}")
    return 0 if not fallos else 1


if __name__ == "__main__":
    sys.exit(main())
