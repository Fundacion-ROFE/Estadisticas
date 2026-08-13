# -*- coding: utf-8 -*-
"""
sync_aprobacion_supabase.py — docs/aprobacion/data.json → Supabase (cohorte canónica).

Sube los agregados canónicos de aprobación (generados por export_aprobacion.py, que loguea
directo en Q10 y aplica la definición canónica del proyecto: cohorte = habilitados +
inhabilitados, SIN perfiles de prueba ni desertores institucionales) a dos tablas públicas:

  - cohorte_ingresos  (cohorte, programa): ingresados / activos / retirados
      ← por_programa: estudiantes_cohorte / habilitados_unicos / retirados_unicos
      (JC 2026 = 832 ingresados = el total sobre el que el panel muestra el avance)
  - aprobacion_cursos (cohorte, curso): cursaron, aprobados, aprobados_retirados,
      retirados, bandas de avance, promedio — el avance de la cohorte COMPLETA por curso.

Escalable por año sin tocar código: la cohorte sale del campo `anio` del JSON; al cambiar
de año el pipeline de aprobación escribe el anio nuevo y este sync crea las filas nuevas
(las de años previos quedan con su último estado). Sin PII — el JSON ya es público.

Uso:
    python sync_aprobacion_supabase.py [--dry-run]
Consola (parseable por n8n):
    RESUMEN: cursos=N programas=P cohorte=YYYY estado=exito

Fundación ROFÉ | Jóvenes creaTIvos · Mujeres ROFÉ
"""

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

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
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_JSON         = os.path.join(PROYECTO_ROOT, "docs", "aprobacion", "data.json")

USER_AGENT = "panel-datos-etl/1.0"  # Supabase rechaza secrets con UA de navegador

# Etiqueta de programa del JSON → enum programa_type (misma clasificación canónica)
MAPA_PROGRAMA = {"jóvenes creativos": "jc", "mujeres rofé": "mr"}


def log(msg: str) -> None:
    print(f"[sync-aprobacion] {msg}", flush=True)


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


def req(url_base: str, key: str, metodo: str, ruta: str, cuerpo=None, prefer: str = ""):
    headers = {"apikey": key, "Authorization": f"Bearer {key}",
               "Content-Type": "application/json", "User-Agent": USER_AGENT}
    if prefer:
        headers["Prefer"] = prefer
    r = urllib.request.Request(url_base.rstrip("/") + "/rest/v1" + ruta, method=metodo,
                               headers=headers,
                               data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
    try:
        with urllib.request.urlopen(r, timeout=120) as resp:
            datos = resp.read()
            return resp.status, json.loads(datos) if datos else None
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                           f"{e.read().decode(errors='replace')[:500]}") from None


def prog_enum(etiqueta: str) -> str | None:
    return MAPA_PROGRAMA.get((etiqueta or "").strip().lower())


def main() -> int:
    ap = argparse.ArgumentParser(description="aprobacion/data.json → Supabase")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        return 1
    if not os.path.isfile(RUTA_JSON):
        log(f"ERROR: no existe {RUTA_JSON} — correr export_aprobacion.py primero")
        return 1

    with open(RUTA_JSON, encoding="utf-8") as f:
        d = json.load(f)
    cohorte = str(d.get("anio", "")).strip()
    if not cohorte:
        log("ERROR: el JSON no trae campo 'anio'")
        return 1
    # UTC (no hora local): v_frescura compara updated_at contra now() en UTC. Escribir hora local
    # (COT) inflaba la frescura en +5h y disparaba la alerta ~5h antes de tiempo. UTC explícito es
    # correcto aquí y tras la migración de n8n a un host cloud. Ver runbooks/recuperacion-frescura.md.
    ahora = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

    filas_prog = []
    for p in d.get("por_programa", []):
        enum = prog_enum(p.get("programa"))
        if not enum:
            log(f"ADVERTENCIA: programa sin mapeo, se omite: {p.get('programa')!r}")
            continue
        ingresados = p["estudiantes_cohorte"]
        activos = p["habilitados_unicos"]
        retirados = p["retirados_unicos"]

        # ⚠ MR: "habilitado" en Q10 NO significa "sigue en el programa" (2026-07-29).
        # Q10 marca inhabilitada a toda mujer cuyo curso cerró, y el scraper de aprobación
        # lo lee como retiro. Caso real: al cerrar 2 de los 3 cursos MR de 2026, la cifra
        # pasó de 322 activas / 24 retiradas a 179 / 167 sin que UNA SOLA mujer se retirara.
        # Definición confirmada por Lina (2026-07-29): en MR se consideran habilitadas TODAS
        # las mujeres de la cohorte; la única baja real es la que aparece en la pestaña
        # Inactivas (fuente `inactivas_mr` de la tabla `retiros`, cuyos motivos son de
        # microcrédito — "No pago Icredit/Microcredito", "Pidió retiro" — no de abandono de
        # curso). Por eso para MR se ignora `habilitados_unicos` y se deriva de la tabla
        # individual. Ver v_choques_cohorte (migración 028), que vigila exactamente esto.
        # JC NO se toca: ahí el habilitados de Q10 sí coincide con la pestaña Seguimiento
        # que mantiene el equipo (760, verificado por 3 fuentes independientes).
        if enum == "mr":
            _, filas_r = req(url, key, "GET",
                             f"/retiros?select=cedula&programa=eq.mr&cohorte=eq.{cohorte}")
            bajas = len({r["cedula"] for r in (filas_r or [])})
            activos_mr = ingresados - bajas
            log(f"  MR: activos {activos} (Q10 habilitados) → {activos_mr} "
                f"(cohorte {ingresados} − {bajas} bajas confirmadas en Inactivas); "
                f"retirados {retirados} → {bajas}")
            activos, retirados = activos_mr, bajas

        filas_prog.append({
            "cohorte": cohorte, "programa": enum,
            "ingresados": ingresados,
            "activos": activos,
            "retirados": retirados,
            "updated_at": ahora,
        })

    filas_curso = []
    for c in d.get("por_curso", []):
        filas_curso.append({
            "cohorte": cohorte, "curso": c["curso"], "programa": prog_enum(c.get("programa")),
            "cursaron": c["cursaron"], "activos": c["activos"], "aprobados": c["aprobados"],
            "aprobados_retirados": c["aprobados_retirados"], "retirados": c["retirados"],
            "banda_0_25": c.get("banda_0_25"), "banda_26_80": c.get("banda_26_80"),
            "banda_81_100": c.get("banda_81_100"), "aprobados_total": c.get("aprobados_total"),
            "no_aprobados": c.get("no_aprobados"), "sin_finalizar": c.get("sin_finalizar"),
            "promedio": c.get("promedio"), "pct_aprobados": c.get("pct_aprobados"),
            "finalizado": c.get("finalizado"), "updated_at": ahora,
        })

    # Absorber renombres de curso ya confirmados (tabla cursos_alias, migración 026).
    # Q10 permite renombrar un curso sin aviso previo; el panel de aprobación entonces
    # reporta el mismo curso dos veces (nombre viejo congelado + nombre nuevo vivo), y como
    # la clave de aprobacion_cursos es (cohorte, curso) EN TEXTO, el upsert crea dos filas y
    # contamina el rango de % de aprobación. Pasó el 2026-07-24 con el curso HTML: la fila
    # vieja quedó en 66.8% y ese número llegó a documentarse en diccionario-metricas.md como
    # el piso real del rango JC (el piso verdadero era 81.1%).
    # ⚠ Casing: acá los nombres vienen en Title Case y en cursos_alias vienen como los da
    # h2test (MAYÚSCULAS) — comparar siempre normalizado, nunca crudo.
    _, alias_rows = req(url, key, "GET",
                        "/cursos_alias?select=cohorte,nombre_viejo,nombre_nuevo")
    remap = {a["nombre_viejo"].strip().upper(): a["nombre_nuevo"].strip().upper()
             for a in (alias_rows or []) if a["cohorte"] == cohorte}
    if remap:
        presentes = {f["curso"].strip().upper() for f in filas_curso}
        conservadas, descartadas, renombradas = [], 0, 0
        for f in filas_curso:
            nuevo = remap.get(f["curso"].strip().upper())
            if not nuevo:
                conservadas.append(f)
            elif nuevo in presentes:
                # El nombre nuevo ya viene en este mismo payload con su casing correcto:
                # descartar la fila vieja es lo correcto; renombrarla duplicaría la clave.
                descartadas += 1
            else:
                # Solo llegó el nombre viejo (el curso volvió a aparecer con el nombre
                # anterior): renombrar para no perder la fila.
                f["curso"] = nuevo
                conservadas.append(f)
                renombradas += 1
        if descartadas or renombradas:
            log(f"Renombres absorbidos desde cursos_alias: {descartadas} filas viejas "
                f"descartadas, {renombradas} renombradas")
        filas_curso = conservadas

    log(f"Cohorte {cohorte}: {len(filas_prog)} programas · {len(filas_curso)} cursos "
        f"(JSON del {d.get('ultima_actualizacion', '?')[:16]})")
    for f_ in filas_prog:
        log(f"  {f_['programa']}: ingresados={f_['ingresados']} "
            f"activos={f_['activos']} retirados={f_['retirados']}")

    if args.dry_run:
        print(f"RESUMEN: cursos={len(filas_curso)} programas={len(filas_prog)} "
              f"cohorte={cohorte} estado=dry_run")
        return 0

    req(url, key, "POST", "/cohorte_ingresos?on_conflict=cohorte,programa", filas_prog,
        prefer="resolution=merge-duplicates,return=minimal")
    req(url, key, "POST", "/aprobacion_cursos?on_conflict=cohorte,curso", filas_curso,
        prefer="resolution=merge-duplicates,return=minimal")
    log("Upserts OK (idempotente por clave cohorte+programa / cohorte+curso)")

    print(f"RESUMEN: cursos={len(filas_curso)} programas={len(filas_prog)} "
          f"cohorte={cohorte} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
