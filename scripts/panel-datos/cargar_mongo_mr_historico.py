# -*- coding: utf-8 -*-
"""
cargar_mongo_mr_historico.py — payload de extraer_mongo_mr_historico.py → Supabase
`postulantes_mr`, cohortes 2023 y 2024.

NO toca Mongo (lee solo el JSON local ya extraído) — separado a propósito de la extracción,
ver nota en extraer_mongo_mr_historico.py.

Va a `postulantes_mr` (universo completo, NO participants): este Mongo es un registro de
usuarias de la app, no de matrícula/avance en cursos — mismo criterio que
sync_postulantes_mr.py (Sheet BD-Mujeres ROFÉ). Cruce por cédula contra `participants`
mostró 97% (2023) y 88% (2024) de cédulas que Supabase no conocía en absoluto.

Precedencia: NUNCA pisa una cédula que ya exista en `postulantes_mr` (las fuentes Sheet
—General/Inactivas/Plataforma MR— ya tienen precedencia establecida). Solo inserta cédulas
nuevas.

⚠️ Cohorte 2023: el equipo (Samuel + su superior) va a revisar la procedencia de esta
cohorte antes de darla por buena — hay sospecha de registros no genuinos. Por eso
--cohortes es EXPLÍCITO y no tiene default: sin él, el script solo reporta, no carga nada.

Uso:
    python cargar_mongo_mr_historico.py --dry-run                  # solo reporte, no carga nada
    python cargar_mongo_mr_historico.py --cohortes 2024            # carga solo 2024
    python cargar_mongo_mr_historico.py --cohortes 2023,2024       # carga ambas (tras revisión)
Consola (parseable):
    RESUMEN: extraidos_2023=N extraidos_2024=M cargados=X nuevos=Y ya_existian=Z estado=exito
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

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "mongo_mr_historico_payload.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
RUTA_REPORTE      = os.path.join(PROYECTO_ROOT, "tools",
                                 f"cargar_mongo_mr_historico_report_{datetime.now():%Y%m%d}.json")

USER_AGENT = "panel-datos-etl/1.0"
LOTE       = 500
COHORTES_DISPONIBLES = (2023, 2024)


def log(msg: str) -> None:
    print(f"[cargar-mongo-mr] {msg}", flush=True)


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


def cargar_exclusiones() -> dict:
    if not os.path.isfile(RUTA_EXCLUSIONES):
        log(f"AVISO: no se encontró {RUTA_EXCLUSIONES} — no se excluirá ningún perfil de prueba")
        return {"cedulas": set(), "emails": set()}
    with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
        data = json.load(f)
    perfiles = data.get("perfiles", [])
    return {
        "cedulas": {str(p.get("cedula")) for p in perfiles if p.get("cedula")},
        "emails": {str(p.get("email", "")).strip().lower() for p in perfiles if p.get("email")},
    }


class Supa:
    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def _req(self, metodo: str, ruta: str, cuerpo=None, prefer: str = ""):
        headers = {"apikey": self.key, "Authorization": f"Bearer {self.key}",
                   "Content-Type": "application/json", "User-Agent": USER_AGENT}
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(self.base + ruta, method=metodo, headers=headers,
                                     data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                               f"{e.read().decode(errors='replace')[:500]}") from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--cohortes", default="",
                     help="Ej: 2024 o 2023,2024 — cuáles cohortes CARGAR a Supabase "
                          "(las demás se reportan pero no se cargan). Vacío = ninguna.")
    args = ap.parse_args()

    cohortes_a_cargar = {int(c) for c in args.cohortes.split(",") if c.strip()}
    invalidas = cohortes_a_cargar - set(COHORTES_DISPONIBLES)
    if invalidas:
        log(f"ERROR: cohortes no soportadas: {invalidas} (disponibles: {COHORTES_DISPONIBLES})")
        return 1

    if not os.path.isfile(RUTA_PAYLOAD):
        log(f"ERROR: no existe {RUTA_PAYLOAD} — correr primero extraer_mongo_mr_historico.py")
        return 1
    with open(RUTA_PAYLOAD, encoding="utf-8") as f:
        payload = json.load(f)
    por_anio = {int(a): d for a, d in payload["por_anio"].items()}
    log(f"Payload cargado (generado {payload['generado']})")
    for anio in COHORTES_DISPONIBLES:
        log(f"  cohorte {anio}: {len(por_anio.get(anio, {}))} cédulas en el payload")

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        return 1

    exclusiones = cargar_exclusiones()
    for anio in COHORTES_DISPONIBLES:
        antes = len(por_anio.get(anio, {}))
        por_anio[anio] = {
            ced: d for ced, d in por_anio.get(anio, {}).items()
            if ced not in exclusiones["cedulas"] and (d.get("email") or "") not in exclusiones["emails"]
        }
        if antes != len(por_anio[anio]):
            log(f"  cohorte {anio}: excluidos {antes - len(por_anio[anio])} perfiles de prueba")

    supa = Supa(url, key)
    log("Consultando postulantes_mr existente en Supabase (para no pisar nada)...")
    existentes_postulantes = {r["cedula"] for r in supa.get_todo("/postulantes_mr?select=cedula")}
    log(f"  postulantes_mr ya tiene {len(existentes_postulantes)} cédulas")

    participantes = supa.get_todo("/participants?select=id,q10_id")
    q10_a_participant = {p["q10_id"]: p["id"] for p in participantes if p.get("q10_id")}

    resumen = {}
    filas_a_cargar = []
    for anio in COHORTES_DISPONIBLES:
        nuevas = {ced: d for ced, d in por_anio[anio].items() if ced not in existentes_postulantes}
        ya_en_postulantes = len(por_anio[anio]) - len(nuevas)
        con_match_participant = sum(1 for ced in nuevas if ced in q10_a_participant)
        resumen[anio] = {
            "extraidas": len(por_anio[anio]),
            "ya_en_postulantes_mr": ya_en_postulantes,
            "nuevas_candidatas": len(nuevas),
            "con_match_participant": con_match_participant,
            "se_carga_esta_corrida": anio in cohortes_a_cargar,
        }
        log(f"Cohorte {anio}: {len(nuevas)} nuevas candidatas "
            f"({ya_en_postulantes} ya estaban en postulantes_mr) — "
            f"{'SE CARGA' if anio in cohortes_a_cargar else 'solo reporte, no se carga'}")

        if anio not in cohortes_a_cargar:
            continue
        for ced, d in sorted(nuevas.items()):
            fila = {"cedula": ced, **{k: v for k, v in d.items() if v is not None},
                    "updated_at": datetime.now().isoformat(timespec="seconds")}
            pid = q10_a_participant.get(ced)
            if pid:
                fila["participant_id"] = pid
            filas_a_cargar.append(fila)

    extraidos = {a: resumen[a]["extraidas"] for a in COHORTES_DISPONIBLES}

    if args.dry_run or not filas_a_cargar:
        with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
            json.dump({"_nota": "PII — no subir a git", "generado": datetime.now().isoformat(timespec="seconds"),
                       "por_cohorte": resumen, "modo": "dry_run" if args.dry_run else "sin_cohortes_a_cargar"},
                      f, ensure_ascii=False, indent=1)
        log(f"Reporte → {RUTA_REPORTE}")
        print(f"RESUMEN: extraidos_2023={extraidos[2023]} extraidos_2024={extraidos[2024]} "
              f"cargados=0 nuevos=0 ya_existian=0 estado={'dry_run' if args.dry_run else 'solo_reporte'}")
        return 0

    grupos: dict[frozenset, list] = {}
    for fila in filas_a_cargar:
        grupos.setdefault(frozenset(fila), []).append(fila)
    for _, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            supa._req("POST", "/postulantes_mr?on_conflict=cedula", grupo[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
    log(f"Cargados: {len(filas_a_cargar)} (en {len(grupos)} grupos de columnas)")

    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump({"_nota": "PII — no subir a git", "generado": datetime.now().isoformat(timespec="seconds"),
                   "por_cohorte": resumen, "cargados_total": len(filas_a_cargar)},
                  f, ensure_ascii=False, indent=1)
    log(f"Reporte → {RUTA_REPORTE}")

    print(f"RESUMEN: extraidos_2023={extraidos[2023]} extraidos_2024={extraidos[2024]} "
          f"cargados={len(filas_a_cargar)} nuevos={len(filas_a_cargar)} ya_existian=0 estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
