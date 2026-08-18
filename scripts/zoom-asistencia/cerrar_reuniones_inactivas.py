# -*- coding: utf-8 -*-
"""
Cierra (Activo=FALSE) en REUNIONES-ACTIVAS cualquier reunión sin actividad reciente.

Por qué existe: `meeting.ended` no siempre llega -- si un participante queda conectado sin
salir o el host no cierra con "Finalizar reunión para todos", Zoom nunca manda el evento de
cierre (ver docs/procesos/zoom-asistencia.md). Sin este script, esa fila se queda
Activo=TRUE indefinidamente y, al ser la reunión "más reciente" de su cuenta (o la única),
tapa el bloque de PANEL-EN-VIVO de esa cuenta con datos de horas antes en vez de mostrarlo
vacío -- visto en vivo 2 veces el mismo día (2026-08-05).

Criterio: una fila se cierra si pasaron más de UMBRAL_HORAS desde su último evento real en
LIVE-LOG (columna HoraMs, epoch ms). Si la fila no tiene NINGÚN evento en LIVE-LOG (p.ej.
porque `Limpiar LIVE-LOG` ya vació su historial de un día anterior), se usa `Apertura` como
respaldo -- si es vieja, se cierra igual.

Pensado para correr cada hora vía n8n (Schedule Trigger + Execute Command en el workflow
`Zoom - Asistencia`), NO solo a las 21:00 -- el problema afecta el panel durante el día, no
solo la limpieza nocturna de LIVE-LOG.

Extendido 2026-08-18 (Fase 2 panel-vivo/Vercel): también cierra (activo=false) la fila
espejo en Supabase `zoom_reuniones_activas` -- el "cerrar" en tiempo real vía un nodo n8n
nuevo se intentó primero, pero resultó poco confiable (fan-out justo antes de "Esperar 90s"
no disparaba consistente, e insertado en línea llegó a corromper el cierre en Sheets al
fallar -- ver docs/procesos/panel-clase-vivo.md). Este script YA corre cada hora y ya tolera
que "cerrar" no sea instantáneo (mismo criterio que el zombie de Sheets); reusarlo para
Supabase evita agregar un punto de falla nuevo al workflow en vivo. Best-effort: si Supabase
falla, el cierre en Sheets (la fuente que ya funciona) no se ve afectado.

Requiere: Service Account en scripts/q10-consolidacion/credenciales_service_account.json.
Opcional: SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY en .env.local (si faltan, se salta el
espejo a Supabase sin fallar).
"""
import argparse
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
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

SHEET_ID = "1VyXOYsnpD9ksKcJFHiiRR6fr4UUCea4WmGG96NV0WP0"
TAB_REUNIONES = "REUNIONES-ACTIVAS"
TAB_LIVE_LOG = "LIVE-LOG"

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

UMBRAL_HORAS_DEFAULT = 3  # sin actividad en LIVE-LOG por mas de esto -> se considera zombie

# Epoch de Google Sheets (serial de fecha 0 = 1899-12-30) para convertir "Apertura" (que se
# escribe como fecha real via USER_ENTERED, no como texto) al respaldo cuando no hay
# eventos en LIVE-LOG.
EPOCH_SHEETS = datetime(1899, 12, 30)


def conectar():
    if not CRED.exists():
        raise FileNotFoundError(f"No encontrado: {CRED}")
    creds = Credentials.from_service_account_file(str(CRED), scopes=SCOPES)
    return gspread.authorize(creds)


def cargar_env_local():
    if ENV_LOCAL.exists():
        for line in ENV_LOCAL.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


def cerrar_en_supabase(uuids, dry_run=False):
    """Best-effort: activo=false en zoom_reuniones_activas para cada uuid, uno por uno (son
    pocos por corrida -- no hace falta batch). Nunca lanza -- un fallo acá no debe tumbar el
    cierre en Sheets, que es la fuente que ya funciona."""
    if not uuids:
        return
    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("(sin SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY -- se salta el espejo a Supabase)")
        return
    for uuid in uuids:
        if dry_run:
            print(f"[dry-run] Supabase: cerraria uuid={uuid}")
            continue
        try:
            qs = urllib.parse.urlencode({"uuid": f"eq.{uuid}"})
            req = urllib.request.Request(
                f"{url}/rest/v1/zoom_reuniones_activas?{qs}",
                method="PATCH",
                headers={
                    "apikey": key, "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json", "Prefer": "return=minimal",
                },
                data=json.dumps({"activo": False}).encode(),
            )
            with urllib.request.urlopen(req, timeout=15):
                pass
        except Exception as e:
            print(f"(Supabase: no se pudo cerrar {uuid}: {e} -- no bloquea el cierre en Sheets)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--umbral-horas", type=float, default=UMBRAL_HORAS_DEFAULT,
                         help=f"Horas sin actividad antes de cerrar (default {UMBRAL_HORAS_DEFAULT})")
    parser.add_argument("--dry-run", action="store_true",
                         help="Solo mostrar qué se cerraría, sin escribir en Sheets")
    args = parser.parse_args()

    gc = conectar()
    sh = gc.open_by_key(SHEET_ID)
    ra = sh.worksheet(TAB_REUNIONES)
    ll = sh.worksheet(TAB_LIVE_LOG)

    filas_ra = ra.get_all_values()
    activas = [(i, r) for i, r in enumerate(filas_ra, start=1)
               if r and len(r) > 4 and r[4] == "TRUE"]
    if not activas:
        print("No hay ninguna reunión Activo=TRUE. Nada que revisar.")
        return

    # Ultimo HoraMs (epoch ms) por UUID, leido directo de LIVE-LOG.
    ultimo_evento_ms = {}
    for r in ll.get_all_values()[1:]:
        if not r or len(r) < 5 or not r[4]:
            continue
        uuid = r[0]
        try:
            ms = int(r[4])
        except ValueError:
            continue
        if ms > ultimo_evento_ms.get(uuid, 0):
            ultimo_evento_ms[uuid] = ms

    ahora_ms = time.time() * 1000
    umbral_ms = args.umbral_horas * 3600 * 1000
    cerradas = 0
    uuids_cerrados = []

    for fila, row in activas:
        uuid, topic, host, apertura = row[0], row[1], row[2], row[3]
        if uuid in ultimo_evento_ms:
            inactivo_ms = ahora_ms - ultimo_evento_ms[uuid]
            fuente = "LIVE-LOG"
        else:
            # Respaldo: sin eventos en LIVE-LOG (posiblemente ya limpiado) -- usar Apertura.
            try:
                apertura_dt = datetime.strptime(apertura, "%Y-%m-%d %H:%M")
            except ValueError:
                continue  # formato inesperado -- no arriesgar un cierre a ciegas
            inactivo_ms = (datetime.now() - apertura_dt).total_seconds() * 1000
            fuente = "Apertura (sin datos en LIVE-LOG)"

        if inactivo_ms > umbral_ms:
            horas = inactivo_ms / 3600000
            print(f"{'[DRY-RUN] ' if args.dry_run else ''}Cerrando fila {fila}: "
                  f"{topic} ({host}) -- {horas:.1f}h sin actividad [{fuente}]")
            if not args.dry_run:
                ra.update(values=[["FALSE"]], range_name=f"E{fila}",
                          value_input_option="USER_ENTERED")
            cerradas += 1
            uuids_cerrados.append(uuid)

    if cerradas == 0:
        print(f"Ninguna reunión activa lleva más de {args.umbral_horas}h sin actividad. "
              f"Nada que cerrar.")
    else:
        print(f"{'Se cerrarían' if args.dry_run else 'Cerradas'} {cerradas} reunión(es) "
              f"inactiva(s).")
        cerrar_en_supabase(uuids_cerrados, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
