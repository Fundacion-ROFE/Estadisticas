# -*- coding: utf-8 -*-
"""
sync_supabase_to_sheets.py — Sincronización Supabase → Sheets (H1Test, H2Test, H3Test).

Objetivo: mantener hojas de lectura fácil en Google Sheets para que el equipo pueda
consultar/editar los datos sin abandonar Excel. Las vistas públicas de Supabase se
espejo en pestañas H1Test (Participantes), H2Test (Emoflow), H3Test (Resumen).

⚠️ NOTA: Este script es principalmente de LECTURA (Supabase → Sheets).
Escrituras manuales en Sheets se cargan en Supabase a través del flujo manual.

Uso:
    python sync_supabase_to_sheets.py [--sheet-id <id>]

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import date

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                 "credenciales_service_account.json")

# Sheet ID por defecto (el mismo de Q10/Avance/Emoflow manual)
SHEET_ID_DEFAULT = "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8"

USER_AGENT = "panel-datos-etl/1.0"


def log(msg: str) -> None:
    print(f"[sync-supabase-sheets] {msg}", flush=True)


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

    def _req(self, metodo: str, ruta: str):
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        req = urllib.request.Request(self.base + ruta, method=metodo, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(
                f"HTTP {e.code} en {metodo} {ruta}: {e.read().decode(errors='replace')[:500]}"
            ) from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        """GET paginado."""
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def sincronizar_h1_participantes(supa: Supa, ws_h1) -> None:
    """H1Test: Participantes + programa + ciudad (datos brutos para referencia)."""
    log("Sincronizando H1Test (Participantes)...")

    # Participantes con programa y ciudad
    filas = supa.get_todo("/participants?select=id,cedula,nombre,email,programa,grupo_ciudad&order=cedula.asc")

    # Headers
    headers = ["Cédula", "Nombre", "Email", "Programa", "Ciudad"]
    datos = [headers]

    for p in filas:
        datos.append([
            p.get("cedula") or "",
            p.get("nombre") or "",
            p.get("email") or "",
            p.get("programa") or "",
            p.get("grupo_ciudad") or "",
        ])

    log(f"  Escribiendo {len(datos)-1} participantes en h1...")
    ws_h1.clear()
    if datos:
        ws_h1.append_rows(datos)


def sincronizar_h2_emoflow(supa: Supa, ws_h2) -> None:
    """H2Test: Emoflow — ingresos al sistema por participante."""
    log("Sincronizando H2Test (Emoflow - Ingresos)...")

    # Emoflow con participant_id resuelto
    filas = supa.get_todo(
        "/emoflow_ingresos?select=email,nombre,grupo_ciudad,ingresos,ultimo_ingreso,participant_id&order=ingresos.desc"
    )

    # Headers
    headers = ["Email", "Nombre", "Ciudad", "Ingresos al Sistema", "Último Ingreso"]
    datos = [headers]

    for f in filas:
        datos.append([
            f.get("email") or "",
            f.get("nombre") or "",
            f.get("grupo_ciudad") or "",
            f.get("ingresos") or 0,
            f.get("ultimo_ingreso") or "",
        ])

    log(f"  Escribiendo {len(datos)-1} registros Emoflow en h2...")
    ws_h2.clear()
    if datos:
        ws_h2.append_rows(datos)


def sincronizar_h3_resumen(supa: Supa, ws_h3) -> None:
    """H3Test: Resumen ejecutivo — KPIs de la cohorte actual."""
    log("Sincronizando H3Test (Resumen Ejecutivo)...")

    # Estadísticas generales
    cohorte_stats = supa.get_todo("/cohorte_stats?limit=1")
    emoflow_resumen = supa.get_todo("/v_emoflow_resumen?limit=1")
    aprobacion = supa.get_todo("/v_aprobacion_cohorte_stats?limit=1")

    datos = [
        ["RESUMEN EJECUTIVO COHORTE ACTUAL"],
        [],
        ["MÉTRICA", "VALOR"],
    ]

    if cohorte_stats:
        c = cohorte_stats[0]
        datos.extend([
            ["Ingresados", c.get("ingresados", 0)],
            ["Activos", c.get("activos", 0)],
            ["Aprobados", c.get("aprobados", 0)],
            ["En Progreso", c.get("en_progreso", 0)],
            ["Retirados", c.get("retirados", 0)],
        ])

    if emoflow_resumen:
        e = emoflow_resumen[0]
        datos.extend([
            [],
            ["EMOFLOW (INGRESOS AL SISTEMA)"],
            ["Participantes Emoflow", e.get("participantes", 0)],
            ["Promedio Ingresos", round(float(e.get("ingresos_promedio") or 0), 2)],
            ["Mediana Ingresos", e.get("ingresos_mediana", 0)],
            ["Máximo Ingresos", e.get("ingresos_max", 0)],
            ["Activos 7d (%)", f"{round(100*e.get('activos_7d', 0)/max(e.get('participantes', 1), 1), 1)}%"],
            ["Inactivos 30d (%)", f"{round(100*e.get('inactivos_30d', 0)/max(e.get('participantes', 1), 1), 1)}%"],
        ])

    datos.extend([
        [],
        ["Actualizado", str(date.today())],
    ])

    log(f"  Escribiendo resumen en h3...")
    ws_h3.clear()
    if datos:
        ws_h3.append_rows(datos)


def main() -> int:
    ap = argparse.ArgumentParser(description="Sincroniza Supabase → Sheets (hojas intermedias)")
    ap.add_argument("--sheet-id", default=SHEET_ID_DEFAULT, help="ID del Google Sheet")
    args = ap.parse_args()

    cargar_env_local()

    # Credenciales Supabase
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_ANON_KEY")  # Anon key es suficiente (lectura de vistas públicas)
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_ANON_KEY (.env.local)")
        return 1

    # Conectar a Supabase
    supa = Supa(url, key)

    # Conectar a Google Sheets
    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    sh = gspread.authorize(creds).open_by_key(args.sheet_id)

    # Verificar que existan las hojas H1Test, H2Test, H3Test (deben existir en el Sheet)
    hojas_existentes = {w.title for w in sh.worksheets()}
    hojas_necesarias = ["H1Test", "H2Test", "H3Test"]

    log(f"Hojas disponibles en el Sheet: {hojas_existentes}")

    hojas_faltantes = [h for h in hojas_necesarias if h not in hojas_existentes]
    if hojas_faltantes:
        log(f"⚠️ ADVERTENCIA: faltan hojas {hojas_faltantes} en el Sheet.")
        log(f"   Por favor crea manualmente las hojas H1Test, H2Test, H3Test en: https://docs.google.com/spreadsheets/d/{args.sheet_id}")
        log(f"   Luego ejecuta este script de nuevo.")
        return 1

    # Sincronizar
    try:
        ws_h1 = sh.worksheet("H1Test")
        sincronizar_h1_participantes(supa, ws_h1)

        ws_h2 = sh.worksheet("H2Test")
        sincronizar_h2_emoflow(supa, ws_h2)

        ws_h3 = sh.worksheet("H3Test")
        sincronizar_h3_resumen(supa, ws_h3)

        log("OK")
        print("RESUMEN: estado=exito")
        return 0

    except Exception as e:
        log(f"ERROR: {e}")
        print("RESUMEN: estado=error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
