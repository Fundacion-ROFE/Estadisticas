# -*- coding: utf-8 -*-
"""
export_supabase_json.py — Exporta TODAS las vistas y tablas públicas de Supabase a JSON.

Objetivo: generar archivos JSON con toda la información de Supabase para que
el panel de Netlify (venerable-truffle-331f3c.netlify.app) los consuma directamente.

Salida: docs/datos/ con archivos JSON por tema (emoflow.json, participantes.json, cursos.json, etc)

Uso:
    python export_supabase_json.py [--output-dir <dir>]

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime

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
DIRECTORIO_DATOS_DEFAULT = os.path.join(PROYECTO_ROOT, "docs", "datos")

USER_AGENT = "panel-datos-etl/1.0"


def log(msg: str) -> None:
    print(f"[export-supabase-json] {msg}", flush=True)


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
                log(f"  ⚠️ Error leyendo {ruta}: {e}")
                return filas


# Tablas/vistas cuyo agregado NUNCA debería estar realmente vacío (hay datos históricos
# desde 2026 en todas). Si UNA de estas vuelve 0 filas, es señal de fallo real (RLS/anon
# roto, tabla vaciada por error, etc.) y sí debe abortar la corrida. El resto de la lista
# son agregados que legítimamente PUEDEN vaciarse algún día sin que sea un fallo del
# pipeline (ej. una serie diaria antes de la primera corrida del día) — 0 filas ahí es
# solo advertencia, no tumba la cadena nocturna de 8 corridas (refinamiento 2026-07-24,
# pedido explícito de Samuel tras revisar el diseño inicial).
NUNCA_VACIAS = {"cohorte_stats", "aprobacion_cursos", "historial_cursos"}


def exportar_tabla(supa: Supa, nombre_tabla: str, output_dir: str) -> dict:
    """Exporta una tabla/vista a JSON. Retorna dict {tabla, filas, ok, warn, error}.
    - Excepción HTTP/timeout → ok=False, error=detalle (aborta la corrida).
    - 0 filas en una tabla de NUNCA_VACIAS → ok=False, error="0 filas" (aborta: esas
      tablas siempre deberían tener datos, 0 es señal de fallo real).
    - 0 filas en cualquier otra tabla configurada → ok=True, warn=True (NO aborta; queda
      reportado en RESUMEN como filas_cero=[...] para revisión humana, sin tumbar la
      cadena nocturna por un agregado que se vació de forma legítima)."""
    try:
        log(f"Exportando {nombre_tabla}...")
        filas = supa.get_todo(f"/{nombre_tabla}")

        if not filas:
            if nombre_tabla in NUNCA_VACIAS:
                log(f"  ✗ 0 filas — tabla en NUNCA_VACIAS, se trata como fallo real")
                return {"tabla": nombre_tabla, "filas": 0, "ok": False, "warn": False, "error": "0 filas (NUNCA_VACIAS)"}
            log(f"  ⚠️ 0 filas (advertencia, no aborta — no está en NUNCA_VACIAS)")
            return {"tabla": nombre_tabla, "filas": 0, "ok": True, "warn": True, "error": None}

        archivo = os.path.join(output_dir, f"{nombre_tabla}.json")
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(filas, f, ensure_ascii=False, indent=2)

        log(f"  ✓ {len(filas)} registros → {os.path.relpath(archivo, PROYECTO_ROOT)}")
        return {"tabla": nombre_tabla, "filas": len(filas), "ok": True, "warn": False, "error": None}
    except Exception as e:
        log(f"  ✗ Error: {e}")
        return {"tabla": nombre_tabla, "filas": 0, "ok": False, "warn": False, "error": str(e)}


# ── Git commit y push ──────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str, output_dir: str) -> bool:
    """Mismo patrón que export_stats.py/export_aprobacion.py. `docs/datos/*.json` ya
    está trackeado en git — sin este paso el directorio queda permanentemente sucio
    (escrito en disco, nunca commiteado). ⚠️ Ver docs/procesos/panel-datos-etl.md:
    hoy no hay consumidor confirmado de estos JSON (el frontend real consulta
    Supabase client-side), así que este commit diario no alimenta nada visible aún.
    Retorna True si el push salió bien (o no había nada que publicar), False si falló."""
    rel_dir = os.path.relpath(output_dir, PROYECTO_ROOT)

    try:
        resultado_status = subprocess.run(
            ["git", "status", "--porcelain", "--", rel_dir],
            cwd=PROYECTO_ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        log("ERROR git (status --porcelain): timeout tras 180s")
        return False
    if resultado_status.returncode != 0:
        stderr = resultado_status.stderr.strip() or resultado_status.stdout.strip()
        log(f"ERROR git (status --porcelain): {stderr}")
        return False
    if not resultado_status.stdout.strip():
        log("  git: sin cambios, no hay nada que publicar.")
        return True

    pasos = [
        ["git", "add", rel_dir],
        ["git", "commit", "-m", f"chore: actualizar export supabase->json [{timestamp}]"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in pasos:
        try:
            resultado = subprocess.run(
                cmd,
                cwd=PROYECTO_ROOT,
                capture_output=True,
                text=True,
                encoding="utf-8",
                timeout=180,
            )
        except subprocess.TimeoutExpired:
            log(f"ERROR git ({' '.join(cmd)}): timeout tras 180s")
            return False
        if resultado.returncode != 0:
            stderr = resultado.stderr.strip() or resultado.stdout.strip()
            log(f"ERROR git ({' '.join(cmd)}): {stderr}")
            return False
        log(f"  git {cmd[1]}: OK")
    return True


def main() -> int:
    ap = argparse.ArgumentParser(description="Exporta Supabase → JSON (panel Netlify)")
    ap.add_argument("--output-dir", default=DIRECTORIO_DATOS_DEFAULT, help="Directorio de salida")
    ap.add_argument("--sin-push", action="store_true",
                    help="Genera el JSON sin git commit/push (pruebas)")
    args = ap.parse_args()

    cargar_env_local()

    # Credenciales Supabase (anon key es suficiente para vistas públicas)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_ANON_KEY (.env.local)")
        return 1

    # Crear directorio de salida
    os.makedirs(args.output_dir, exist_ok=True)
    log(f"Exportando a: {args.output_dir}")

    supa = Supa(url, key)

    # Tablas y vistas públicas a exportar (SUPABASE_ANON_KEY → solo lo realmente público).
    # Se sacaron de esta lista (verificado en vivo con la anon key, 2026-07-24):
    #   - "participants", "emoflow_ingresos", "asistencia_zoom", "asistencia_promedio":
    #     HTTP 401 — PII con RLS+REVOKE anon, siempre vacías/erróneas vía este script por diseño.
    #   - "enrollments": HTTP 200 pero 0 filas siempre (policy pública filtra por
    #     participants.is_public, que hoy es false en el 100% de los casos) — mismo ruido.
    #   - "v_aprobacion_cohorte_stats": HTTP 404 — la vista no existe en Supabase.
    #   - "emoflow_participacion_semanal": deprecada 🔴 (ver supabase-estructura.md), sin
    #     consumidor nuevo — candidata a DROP (migración 012, pendiente de aprobación).
    tablas = [
        # Cursos y matrículas
        "courses",
        "v_curso_completion",
        "v_curso_completion_por_ciudad",

        # Demografía
        "v_demografia_grupo",
        "v_mr_demografia",

        # Estadísticas generales
        "cohorte_stats",

        # Emoflow (ingresos al sistema)
        "v_emoflow_resumen",
        "v_emoflow_por_ciudad",
        "v_emoflow_bandas",
        "v_emoflow_bandas_ciudad",
        "historial_emoflow",
        "historial_emoflow_ciudad",

        # Aprobación
        "cohorte_ingresos",
        "aprobacion_cursos",

        # Historial
        "historial_cursos",
        "historial_cursos_ciudad",
    ]

    log(f"Exportando {len(tablas)} tablas/vistas...")
    resultados = [exportar_tabla(supa, tabla, args.output_dir) for tabla in tablas]

    total_filas = sum(r["filas"] for r in resultados)
    fallidas = [r for r in resultados if not r["ok"]]
    exitosas = [r for r in resultados if r["ok"]]
    con_advertencia = [r for r in exitosas if r["warn"]]

    # Manifest generado desde lo REALMENTE exportado (no hardcodeado).
    manifest = {
        "fecha_exportacion": datetime.now().isoformat(),
        "total_registros": total_filas,
        "tablas_configuradas": len(tablas),
        "tablas_exportadas_ok": len(exitosas),
        "tablas_fallidas": [{"tabla": r["tabla"], "error": r["error"]} for r in fallidas],
        "tablas_con_0_filas": [r["tabla"] for r in con_advertencia],
        "detalle": {r["tabla"]: r["filas"] for r in exitosas},
    }

    archivo_manifest = os.path.join(args.output_dir, "manifest.json")
    with open(archivo_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"✓ Manifest → {os.path.relpath(archivo_manifest, PROYECTO_ROOT)}")

    if con_advertencia:
        nombres_warn = ",".join(r["tabla"] for r in con_advertencia)
        log(f"⚠️ {len(con_advertencia)} tabla(s) con 0 filas (no abortan, no están en NUNCA_VACIAS): {nombres_warn}")

    if fallidas:
        nombres = ",".join(r["tabla"] for r in fallidas)
        log(f"ERROR: {len(fallidas)} tabla(s) fallaron: {nombres}")
        log("No se hace git push de un export incompleto.")
        print(
            f"RESUMEN: tablas={len(tablas)} ok={len(exitosas)} fallidas={len(fallidas)} "
            f"filas_cero={','.join(r['tabla'] for r in con_advertencia) or 'ninguna'} "
            f"registros={total_filas} estado=error detalle=tablas_fallidas:{nombres}"
        )
        return 1

    push_ok = True
    if args.sin_push:
        log("Modo --sin-push: no se toca git.")
    else:
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        log("Ejecutando git commit y push...")
        push_ok = git_commit_y_push(timestamp, args.output_dir)

    filas_cero_str = ",".join(r["tabla"] for r in con_advertencia) or "ninguna"

    if not push_ok:
        log("ERROR: git push falló.")
        print(
            f"RESUMEN: tablas={len(tablas)} ok={len(exitosas)} fallidas=0 "
            f"filas_cero={filas_cero_str} registros={total_filas} "
            f"estado=error detalle=git_push_fallido"
        )
        return 1

    log("OK")
    print(
        f"RESUMEN: tablas={len(tablas)} ok={len(exitosas)} fallidas=0 "
        f"filas_cero={filas_cero_str} registros={total_filas} estado=exito"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
