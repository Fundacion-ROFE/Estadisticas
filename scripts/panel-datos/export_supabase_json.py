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


def exportar_tabla(supa: Supa, nombre_tabla: str, output_dir: str) -> int:
    """Exporta una tabla/vista a JSON."""
    try:
        log(f"Exportando {nombre_tabla}...")
        filas = supa.get_todo(f"/{nombre_tabla}")

        if not filas:
            log(f"  (vacío)")
            return 0

        archivo = os.path.join(output_dir, f"{nombre_tabla}.json")
        with open(archivo, "w", encoding="utf-8") as f:
            json.dump(filas, f, ensure_ascii=False, indent=2)

        log(f"  ✓ {len(filas)} registros → {os.path.relpath(archivo, PROYECTO_ROOT)}")
        return len(filas)
    except Exception as e:
        log(f"  ✗ Error: {e}")
        return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Exporta Supabase → JSON (panel Netlify)")
    ap.add_argument("--output-dir", default=DIRECTORIO_DATOS_DEFAULT, help="Directorio de salida")
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

    # Tablas y vistas públicas a exportar
    # (todas las que consume el panel de Netlify + datos útiles para el equipo)
    tablas = [
        # Participantes
        "participants",

        # Cursos y matrículas
        "courses",
        "enrollments",
        "v_curso_completion",
        "v_curso_completion_por_ciudad",

        # Demografía
        "v_demografia_grupo",
        "v_mr_demografia",

        # Estadísticas generales
        "cohorte_stats",

        # Emoflow (ingresos al sistema)
        "emoflow_ingresos",
        "v_emoflow_resumen",
        "v_emoflow_por_ciudad",
        "v_emoflow_bandas",
        "v_emoflow_bandas_ciudad",
        "historial_emoflow",
        "historial_emoflow_ciudad",
        "emoflow_participacion_semanal",

        # Aprobación
        "cohorte_ingresos",
        "aprobacion_cursos",
        "v_aprobacion_cohorte_stats",

        # Asistencia
        "asistencia_zoom",
        "asistencia_promedio",

        # Historial
        "historial_cursos",
        "historial_cursos_ciudad",
    ]

    log(f"Exportando {len(tablas)} tablas/vistas...")
    total_filas = 0

    for tabla in tablas:
        total_filas += exportar_tabla(supa, tabla, args.output_dir)

    # Crear archivo de manifest/metadata
    manifest = {
        "fecha_exportacion": datetime.now().isoformat(),
        "total_registros": total_filas,
        "tablas_exportadas": len(tablas),
        "bases": {
            "participantes": ["participants"],
            "cursos": ["courses", "enrollments", "v_curso_completion"],
            "emoflow": ["emoflow_ingresos", "v_emoflow_resumen", "emoflow_participacion_semanal"],
            "aprobacion": ["cohorte_ingresos", "aprobacion_cursos"],
            "asistencia": ["asistencia_zoom", "asistencia_promedio"],
            "historial": ["historial_cursos", "historial_emoflow"],
        }
    }

    archivo_manifest = os.path.join(args.output_dir, "manifest.json")
    with open(archivo_manifest, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    log(f"✓ Manifest → {os.path.relpath(archivo_manifest, PROYECTO_ROOT)}")

    log("OK")
    print(f"RESUMEN: tablas={len(tablas)} registros={total_filas} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
