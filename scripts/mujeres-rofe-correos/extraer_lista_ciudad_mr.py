#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extraer_lista_ciudad_mr.py — Lista de envío Mujeres ROFÉ por ciudad, universo COMPLETO.

Reemplaza el patrón de escribir un query ad-hoc contra Supabase por cada campaña
(extraer_lista_bogota.py, generar_lista_y_enviar.py, extraer_lista_cundinamarca.py...) —
cada uno con su propia normalización de ciudad hecha a mano, y por eso con bugs
distintos (ver incidente 2026-07-24 en claude_sessions.md: un filtro `'BOGOTA' in
ciudad.upper()` descartó 431/512 filas de Bogotá porque .upper() no quita tildes).

Fuente: `postulantes_mr` (universo completo de postulantes/candidatas MR — NO solo
matriculadas en curso, ver docs/procesos/postulantes-mr-supabase.md). Filtra por
`ciudad_norm` (columna generada, ver docs/migrations/013_normalizar_ciudad.sql) +
`ciudad_alias` (fusiona "Bogotá D.C." / "BGT" -> "Bogotá", etc. vía ciudad_utils.py) —
nunca por `ciudad` crudo.

Si necesitas SOLO matriculadas en un curso activo (no el universo completo), esa es
otra pregunta — usa `participants`+`enrollments` filtrado por `courses.programa='mr'`
(ver extraer_lista_mr_ultimos3anios.py), no este script.

Uso:
    python extraer_lista_ciudad_mr.py --ciudad "Bogotá" --id encuentro_bogota_2026
    python extraer_lista_ciudad_mr.py --todas --id campana_nacional   # sin filtro de ciudad

Salida: tools/mujeres-rofe-correos/data/lista_<ID>.csv (nombre,correo,cohorte — cohorte
vacío: postulantes_mr no tiene noción de cohorte de curso, eso es de `enrollments`).

Consola (parseable):
    RESUMEN: ciudad="X" universo=N validos=M suprimidos=S final=F matriculadas_cruce=C estado=exito
"""
import argparse
import io
import os
import re
import sys

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
TOOLS_DATA = os.path.join(PROYECTO_ROOT, "tools", "mujeres-rofe-correos", "data")

sys.path.insert(0, os.path.join(PROYECTO_ROOT, "scripts", "panel-datos"))
from ciudad_utils import Supa, cargar_alias, claves_para  # noqa: E402

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def log(msg):
    print(f"[extraer-ciudad-mr] {msg}", flush=True)


def cargar_env_local():
    if not os.path.isfile(RUTA_ENV):
        return
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            k, v = linea.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip())


def extraer_supresiones(supa):
    """Set de correos (lowercase) a excluir: opt-out + hard bounces."""
    optout, hard = set(), set()
    try:
        optout = {(f.get("email") or "").strip().lower()
                  for f in supa.get_todo("/email_optout?select=email") if f.get("email")}
    except RuntimeError as e:
        log(f"AVISO: no se pudo leer email_optout ({e}) — no se excluye opt-out")
    try:
        hard = {(f.get("email") or "").strip().lower()
                for f in supa.get_todo("/email_bounces?select=email&tipo=eq.hard") if f.get("email")}
    except RuntimeError as e:
        log(f"AVISO: no se pudo leer email_bounces ({e}) — no se excluyen rebotes")
    return optout | hard, len(optout), len(hard)


def main():
    ap = argparse.ArgumentParser(description="Lista de envío MR por ciudad (universo completo, postulantes_mr)")
    grupo = ap.add_mutually_exclusive_group(required=True)
    grupo.add_argument("--ciudad", help='Ciudad tal como la escribiría un humano, ej. "Bogotá"')
    grupo.add_argument("--todas", action="store_true", help="Sin filtro de ciudad (universo nacional)")
    ap.add_argument("--id", required=True, help="ID de campaña -> lista_<ID>.csv")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales Supabase (.env.local)")
        sys.exit(1)
    supa = Supa(url, key)

    alias = cargar_alias(supa)
    claves = None
    if args.ciudad:
        claves = claves_para(args.ciudad, alias=alias)
        if not claves:
            log(f"ERROR: '{args.ciudad}' no normalizó a nada usable")
            sys.exit(1)
        log(f"Ciudad '{args.ciudad}' -> ciudad_norm en {claves}")
        filtro = ",".join(claves)
        universo = supa.get_todo(f"/postulantes_mr?ciudad_norm=in.({filtro})&select=nombre,email,ciudad")
    else:
        log("Sin filtro de ciudad (--todas)")
        universo = supa.get_todo("/postulantes_mr?select=nombre,email,ciudad")
    log(f"  postulantes_mr: {len(universo)} filas")

    mapa = {}
    for p in universo:
        correo = (p.get("email") or "").strip().lower()
        if not correo or not EMAIL_RE.match(correo):
            continue
        if correo not in mapa:
            mapa[correo] = (p.get("nombre") or "").strip()
    log(f"  correos válidos únicos: {len(mapa)}")

    supresiones, n_optout, n_hard = extraer_supresiones(supa)
    excluidos = 0
    if supresiones:
        antes = len(mapa)
        mapa = {c: n for c, n in mapa.items() if c not in supresiones}
        excluidos = antes - len(mapa)
    log(f"Supresiones: {n_optout} opt-out, {n_hard} hard bounces → {excluidos} excluidos")

    # Cruce de sanidad (informativo, NO filtra la lista): cuántas de estas también
    # están matriculadas en un curso MR activo (participants/enrollments). Un número
    # sospechosamente bajo en `final` comparado con este cruce, o con un envío anterior
    # al mismo público, es señal de revisar antes de reportar — no de confiar ciego.
    matriculadas_cruce = None
    if claves:
        filtro = ",".join(claves)
        try:
            matriculadas_cruce = len(supa.get_todo(
                f"/participants?ciudad_norm=in.({filtro})&select=id"))
        except RuntimeError as e:
            log(f"AVISO: no se pudo hacer el cruce de sanidad con participants ({e})")

    log(f"Lista final: {len(mapa)} correos"
        + (f"  (cruce: {matriculadas_cruce} matriculadas en participants con la misma ciudad_norm)"
           if matriculadas_cruce is not None else ""))

    os.makedirs(TOOLS_DATA, exist_ok=True)
    ruta_salida = os.path.join(TOOLS_DATA, f"lista_{args.id}.csv")
    with open(ruta_salida, "w", encoding="utf-8-sig", newline="") as f:
        f.write("nombre,correo,cohorte\n")
        for correo in sorted(mapa.keys()):
            nombre = mapa[correo].replace('"', "'")
            f.write(f'"{nombre}",{correo},\n')

    log(f"✓ Escrito: {ruta_salida}")
    ciudad_txt = args.ciudad or "TODAS"
    print(f'RESUMEN: ciudad="{ciudad_txt}" universo={len(universo)} validos={len(mapa) + excluidos} '
          f"suprimidos={excluidos} final={len(mapa)} matriculadas_cruce={matriculadas_cruce} estado=exito")


if __name__ == "__main__":
    main()
