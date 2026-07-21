# -*- coding: utf-8 -*-
"""
Backfill / red de seguridad de grabaciones Zoom -> YouTube (MR) / Drive (NOVA).

Lista TODAS las grabaciones en la nube de comunicaciones@tocaunavida.org de los ultimos
N dias (default 2) y le pasa cada una a la misma logica del webhook (procesar() de
subir_yt_grabacion.py, idempotente: YouTube por log de UUID, NOVA por archivo ya
presente en Drive). Cubre los casos en que el webhook se pierde: PC apagado, tunel
caido, o transcripcion que Zoom termino despues del evento recording.completed.

Uso:
  python backfill_grabaciones.py            # ultimos 2 dias
  python backfill_grabaciones.py --dias 5
  python backfill_grabaciones.py --dry-run
"""
import argparse
import io
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

sys.path.insert(0, str(Path(__file__).resolve().parent))
from subir_yt_grabacion import ZOOM_ENV, _parse_env_file, obtener_token_zoom, procesar

HOST = "comunicaciones@tocaunavida.org"


def listar_grabaciones(access_token: str, desde: str, hasta: str) -> list:
    meetings, token_pagina = [], ""
    while True:
        params = {"from": desde, "to": hasta, "page_size": 100}
        if token_pagina:
            params["next_page_token"] = token_pagina
        url = (f"https://api.zoom.us/v2/users/{urllib.parse.quote(HOST)}/recordings?"
               + urllib.parse.urlencode(params))
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {access_token}"})
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.load(r)
        meetings.extend(data.get("meetings", []))
        token_pagina = data.get("next_page_token", "")
        if not token_pagina:
            return meetings


def main():
    parser = argparse.ArgumentParser(description="Backfill grabaciones Zoom -> YouTube/Drive")
    parser.add_argument("--dias", type=int, default=2)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    hasta = datetime.utcnow().date()
    desde = hasta - timedelta(days=args.dias)

    access_token = obtener_token_zoom(_parse_env_file(ZOOM_ENV))
    meetings = listar_grabaciones(access_token, str(desde), str(hasta))
    print(f"Grabaciones encontradas ({desde} a {hasta}): {len(meetings)}")

    errores = 0
    for m in meetings:
        try:
            # Sin download_token (solo viene en el webhook): procesar() descarga con el
            # access_token de la app S2S, que ya tiene el scope de cloud recording.
            rc = procesar(m, None, args.dry_run)
            errores += 1 if rc != 0 else 0
        except Exception as e:
            errores += 1
            print(f"[ERROR] {m.get('topic')} ({m.get('uuid')}): {e}", file=sys.stderr)

    if errores:
        print(f"[ERROR] Backfill termino con {errores} fallo(s) de {len(meetings)} reuniones")
        return 1
    print(f"[OK] Backfill completo: {len(meetings)} reuniones revisadas, sin fallos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
