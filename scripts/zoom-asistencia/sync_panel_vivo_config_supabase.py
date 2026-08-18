# -*- coding: utf-8 -*-
"""
Sync de la config del panel de clase en vivo hacia Supabase (Fase 2, 2026-08-18).

Empuja 2 piezas de baja frecuencia (solo cambian cuando alguien corre analizar_cupos_bd.py o
edita CUPOS a mano) a las tablas nuevas de la migración 051_panel_vivo_supabase:

- `tools/cupos_clases.json` (roster_por_horario, ya generado por analizar_cupos_bd.py) ->
  `matriculados_vivo` (reemplaza la pestaña MATRICULADOS-VIVO para el panel en Vercel).
- La pestaña `CUPOS` del Sheet -> `zoom_cupos_config` (reemplaza CUPOS para el panel en
  Vercel).

Reemplazo TOTAL (delete + insert), no upsert incremental -- mismo criterio que ya usa
`recrear()` en setup_zoom_asistance.py para estas mismas pestañas: son snapshots, no logs que
crecen. Corrida manual, mismo ritmo que analizar_cupos_bd.py hoy (no hay cron nuevo).

Requiere: Service Account en scripts/q10-consolidacion/credenciales_service_account.json,
SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env.local (mismas variables que ya usa
api_panel_vivo.py).
"""
import argparse
import json
import os
import sys
import urllib.request
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import gspread
from google.oauth2.service_account import Credentials

BASE = Path(__file__).resolve().parents[2]
CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"
ENV_LOCAL = BASE / ".env.local"
CUPOS_JSON = BASE / "tools" / "cupos_clases.json"

SHEET_ID = "1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
USER_AGENT = "rofe-sync-panel-vivo-config/1.0"


def log(msg: str) -> None:
    print(msg, flush=True)


def cargar_env_local() -> None:
    if ENV_LOCAL.exists():
        for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def conectar_sheet():
    creds = Credentials.from_service_account_file(str(CRED), scopes=SCOPES)
    gc = gspread.authorize(creds)
    return gc.open_by_key(SHEET_ID)


def _req(url, key, path, method="GET", data=None, extra_headers=None, timeout=60):
    headers = {"apikey": key, "Authorization": f"Bearer {key}", "User-Agent": USER_AGENT}
    if extra_headers:
        headers.update(extra_headers)
    body = json.dumps(data).encode() if data is not None else None
    if body is not None:
        headers["Content-Type"] = "application/json"
    r = urllib.request.Request(url + path, method=method, headers=headers, data=body)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        raw = resp.read()
        return json.loads(raw) if raw else None


def reemplazar_tabla(url, key, tabla, filas, filtro_delete, dry_run=False):
    """DELETE ALL (con `filtro_delete`, ej. 'id=gte.0') + INSERT en lotes de 500. Snapshot
    completo, no upsert -- coherente con el patron recrear() del resto del proyecto para
    estas mismas piezas (MATRICULADOS-VIVO/CUPOS)."""
    if dry_run:
        log(f"[dry-run] {tabla}: reemplazaria {len(filas)} filas (delete + insert)")
        return
    _req(url, key, f"/rest/v1/{tabla}?{filtro_delete}", method="DELETE",
         extra_headers={"Prefer": "return=minimal"})
    headers = {"Prefer": "return=minimal"}
    for i in range(0, len(filas), 500):
        lote = filas[i:i + 500]
        _req(url, key, f"/rest/v1/{tabla}", method="POST", data=lote, extra_headers=headers)
    log(f"{tabla}: {len(filas)} filas escritas")


def filas_matriculados_vivo():
    if not CUPOS_JSON.exists():
        log(f"AVISO: no existe {CUPOS_JSON} -- corre analizar_cupos_bd.py primero")
        return []
    datos = json.loads(CUPOS_JSON.read_text(encoding="utf-8"))
    roster = datos.get("roster_por_horario", {})
    filas = []
    vistos = set()
    for horario, personas in roster.items():
        for p in personas:
            correo = (p.get("correo") or "").strip().lower()
            nombre = (p.get("nombre") or "").strip()
            if not correo or not nombre:
                continue
            clave = (horario, correo)
            if clave in vistos:  # PK compuesta (horario, correo) -- evita 409 por duplicado
                continue
            vistos.add(clave)
            filas.append({"horario": horario, "nombre": nombre, "correo": correo})
    return filas


def filas_cupos_config(sh):
    ws = sh.worksheet("CUPOS")
    filas_raw = ws.get_all_values()
    out = []
    for r in filas_raw[1:]:
        if len(r) < 2 or not (r[1] or "").strip():  # sin Clase -> fila vacia/de config aparte
            continue
        out.append({
            "area": (r[0] or "").strip() or None,
            "clase": r[1].strip(),
            "inscritos": int(r[2]) if len(r) > 2 and (r[2] or "").strip().isdigit() else None,
            "alias_zoom": (r[3] or "").strip() if len(r) > 3 else None,
            "dia": (r[4] or "").strip() if len(r) > 4 else None,
            "hora": float(r[5]) if len(r) > 5 and (r[5] or "").strip()
                    and r[5].replace(".", "", 1).isdigit() else None,
        })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--solo-roster", action="store_true", help="Solo matriculados_vivo, no CUPOS")
    ap.add_argument("--solo-cupos", action="store_true", help="Solo zoom_cupos_config, no roster")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY en .env.local")
        return 1

    if not args.solo_cupos:
        filas = filas_matriculados_vivo()
        log(f"matriculados_vivo: {len(filas)} filas desde {CUPOS_JSON.name}")
        # correo es NOT NULL (parte de la PK) -- "not.is.null" matchea siempre todas las filas
        # existentes, sirve como "DELETE FROM" sin condicion real.
        reemplazar_tabla(url, key, "matriculados_vivo", filas, "correo=not.is.null",
                          dry_run=args.dry_run)

    if not args.solo_roster:
        sh = conectar_sheet()
        filas = filas_cupos_config(sh)
        log(f"zoom_cupos_config: {len(filas)} filas desde CUPOS")
        reemplazar_tabla(url, key, "zoom_cupos_config", filas, "id=gte.0", dry_run=args.dry_run)

    return 0


if __name__ == "__main__":
    sys.exit(main())
