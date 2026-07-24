# -*- coding: utf-8 -*-
"""
sync_supabase_to_sheets.py — Sincronización Supabase → Google Sheets (uso de Emoflow).

Objetivo: dejar en Google Sheets una hoja de lectura fácil para que el equipo consulte
el uso de Emoflow por estudiante sin entrar al panel ni a Supabase.

Escribe UNA pestaña: `AUTO_Emoflow_Uso` (la crea si no existe).

⚠️ La pestaña se BORRA ENTERA (`clear()`) en cada corrida — por eso el prefijo `AUTO_`:
   nada escrito a mano ahí sobrevive. No renombrar sin actualizar TAB_EMOFLOW abajo.

⚠️ NUNCA apuntar este script al Sheet `1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs`
   (pestaña `h2test`): ese es el export CRUDO de Q10 que lee `normalize_q10_data.py`,
   la ENTRADA de todo el pipeline. Un `clear()` ahí lo destruiría. La similitud de
   nombres `h2test` / `H2Test` es coincidencia — ver docs/procesos/supabase-estructura.md.

**2026-07-23 — reescrito.** Antes intentaba escribir 3 pestañas (H1Test/H2Test/H3Test) y
venía fallando a diario. Dos causas: (a) las pestañas fueron borradas del Sheet, y
(b) el script había quedado desactualizado frente al esquema —
`participants.cedula`/`participants.programa` no existen (son `q10_id` y viven en
`courses`), y la vista `v_aprobacion_cohorte_stats` tampoco. Decisión: dejar solo Emoflow,
que es la parte que sí funciona. Las funciones de Participantes y Resumen quedan abajo
DESACTIVADAS y sin llamar, como referencia por si el equipo las vuelve a pedir.

Usa SERVICE_ROLE (no anon): `emoflow_ingresos` es PII y anon quedó revocado (401) en el
hardening de seguridad del 2026-07-14/23.

Uso:
    python sync_supabase_to_sheets.py [--sheet-id <id>]
Consola (parseable por n8n):
    RESUMEN: filas=N estado=exito

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

# Sheet destino: hoja DEDICADA de espejos automáticos ("AUTO"), compartida con la SA
# como Editor. NO es la BD Seguimiento (1ggz…, fuente humana canónica, la SA es
# solo-lectura ahí a propósito) ni el export de h2test — ambos son destinos de
# ESCRITURA PROHIBIDOS (ver guardarraíl en main). Decisión 2026-07-24.
SHEET_ID_DEFAULT = "1eO73hL9Bq_X8T11g3aPAEkq6QkKfMRNykru7to8GDdo"
TAB_EMOFLOW      = "AUTO_Emoflow_Uso"

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


def sincronizar_emoflow(supa: Supa, ws) -> int:
    """`AUTO_Emoflow_Uso`: uso de Emoflow por persona + su estado canónico.

    La columna Estado traduce el cruce con `participants.en_seguimiento_jc` para que la
    hoja se explique sola: el CSV de Emoflow arrastra gente que ya no es estudiante
    (retiros y postulantes de años anteriores), y sin esa columna los totales de la hoja
    no cuadrarían con el panel. Ver docs/procesos/supabase-estructura.md.
    """
    log(f"Sincronizando {TAB_EMOFLOW}...")

    filas = supa.get_todo(
        "/emoflow_ingresos?select=email,nombre,grupo_ciudad,ingresos,ultimo_ingreso,"
        "participant_id&order=ingresos.desc"
    )
    # id → en_seguimiento_jc, para clasificar sin una segunda consulta por fila
    seguimiento = {
        p["id"]: p.get("en_seguimiento_jc")
        for p in supa.get_todo("/participants?select=id,en_seguimiento_jc")
    }

    def estado(pid) -> str:
        if not pid or pid not in seguimiento:
            return "Sin matrícula en Q10"
        return "Retiro probable" if seguimiento[pid] is False else "Estudiante actual"

    datos = [["Email", "Nombre", "Ciudad", "Ingresos al Sistema", "Último Ingreso", "Estado"]]
    for f in filas:
        datos.append([
            f.get("email") or "",
            f.get("nombre") or "",
            f.get("grupo_ciudad") or "",
            f.get("ingresos") or 0,
            f.get("ultimo_ingreso") or "",
            estado(f.get("participant_id")),
        ])

    log(f"  Escribiendo {len(datos) - 1} registros...")
    ws.clear()
    ws.append_rows(datos)
    return len(datos) - 1


# ---------------------------------------------------------------------------
# DESACTIVADAS (2026-07-23). No se llaman desde main(). Ambas quedaron rotas contra el
# esquema actual y se conservan solo como referencia si el equipo vuelve a pedir estas
# hojas — arreglarlas exige reescribir las consultas, no solo recrear las pestañas:
#   · sincronizar_h1_participantes: `participants.cedula` y `participants.programa` no
#     existen (son `q10_id`, y el programa vive en `courses` vía `enrollments`) → HTTP 400.
#   · sincronizar_h3_resumen: la vista `v_aprobacion_cohorte_stats` no existe (HTTP 404) y
#     los campos que lee de `cohorte_stats` (ingresados/activos/aprobados/…) tampoco —
#     hoy esa tabla trae total_participantes/con_emprendimiento/edad_promedio.
# ---------------------------------------------------------------------------
def sincronizar_h1_participantes(supa: Supa, ws_h1) -> None:
    """[DESACTIVADA] H1Test: Participantes + programa + ciudad."""
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
    """[DESACTIVADA] H3Test: Resumen ejecutivo — KPIs de la cohorte actual."""
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

    # SERVICE_ROLE, no anon: `emoflow_ingresos` es PII y anon está revocado (401).
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        log("ERROR: falta SUPABASE_URL o SUPABASE_SERVICE_ROLE_KEY (.env.local)")
        return 1

    supa = Supa(url, key)

    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES,
        scopes=["https://www.googleapis.com/auth/spreadsheets"],
    )
    sh = gspread.authorize(creds).open_by_key(args.sheet_id)

    # Guardarraíl: destinos de ESCRITURA prohibidos — abortar antes de tocar nada.
    #  - h2test (1q4VNn…): un clear()/add ahí destruiría la entrada del pipeline.
    #  - BD Seguimiento (1ggz…): fuente humana canónica; la SA es solo-lectura ahí a
    #    propósito. Este script SOLO debe escribir en la hoja dedicada de espejos AUTO.
    SHEETS_PROHIBIDOS = {
        "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs":
            "export crudo de Q10 / h2test (entrada del pipeline)",
        "1ggzoJeZR3fS6AwRCLoGeYA5HEp_B7zvOwFGlGwny0l8":
            "BD Seguimiento de Monitorias (fuente humana, solo-lectura)",
    }
    if args.sheet_id in SHEETS_PROHIBIDOS:
        log(f"ERROR: destino de escritura prohibido — {SHEETS_PROHIBIDOS[args.sheet_id]}. Abortando.")
        print("RESUMEN: filas=0 estado=error")
        return 1

    try:
        # Crear la pestaña si no existe: evita el fallo diario que traía este paso.
        try:
            ws = sh.worksheet(TAB_EMOFLOW)
        except gspread.WorksheetNotFound:
            log(f"La pestaña '{TAB_EMOFLOW}' no existe — creándola...")
            ws = sh.add_worksheet(title=TAB_EMOFLOW, rows="1000", cols="10")

        n = sincronizar_emoflow(supa, ws)

        log("OK")
        print(f"RESUMEN: filas={n} estado=exito")
        return 0

    except Exception as e:
        log(f"ERROR: {e}")
        print("RESUMEN: filas=0 estado=error")
        return 1


if __name__ == "__main__":
    sys.exit(main())
