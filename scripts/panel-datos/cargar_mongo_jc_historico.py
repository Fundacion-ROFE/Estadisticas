# -*- coding: utf-8 -*-
"""
cargar_mongo_jc_historico.py — payload de extraer_mongo_jc_historico.py → Supabase
`postulantes_jc`.

NO toca Mongo (lee solo el JSON local ya extraído) — separado a propósito de la extracción,
mismo patrón que cargar_mongo_mr_historico.py (pymongo + urllib(Supabase) en el mismo
proceso puede colgar conexiones HTTPS).

Va a `postulantes_jc` (universo completo del Mongo de la app JC, NO participants): esta
colección es registro de usuarias/os de la app, no de matrícula/avance en cursos Q10 —
mismo criterio que postulantes_mr. Se carga TODO el payload (no solo los "exclusivos"):
`participant_id` queda NULL para quien no matriculó, poblado para quien sí — igual que
postulantes_mr. `fuente` deja explícito que el origen es Mongo (mongo_user/mongo_applicant).

Precedencia: upsert idempotente por cédula (on_conflict) — reejecutar no duplica.

Uso:
    python cargar_mongo_jc_historico.py [--dry-run]
Consola (parseable):
    RESUMEN: total=N cargados=X con_match_participant=Y estado=exito
"""

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

import argparse

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "mongo_jc_historico_payload.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
RUTA_REPORTE      = os.path.join(PROYECTO_ROOT, "tools",
                                 f"cargar_mongo_jc_historico_report_{datetime.now():%Y%m%d}.json")

USER_AGENT = "panel-datos-etl/1.0"
LOTE       = 500


def log(msg: str) -> None:
    print(f"[cargar-mongo-jc] {msg}", flush=True)


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


def _fuente(coleccion: str) -> str:
    return "mongo_user" if coleccion == "User" else "mongo_applicant"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if not os.path.isfile(RUTA_PAYLOAD):
        log(f"ERROR: no existe {RUTA_PAYLOAD} — correr primero extraer_mongo_jc_historico.py")
        return 1
    with open(RUTA_PAYLOAD, encoding="utf-8") as f:
        payload = json.load(f)
    documentos = payload["documentos"]
    log(f"Payload cargado (generado {payload['generado']}) — {len(documentos)} cédulas")

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        return 1

    exclusiones = cargar_exclusiones()
    antes = len(documentos)
    documentos = {ced: d for ced, d in documentos.items()
                  if ced not in exclusiones["cedulas"] and (d.get("email") or "") not in exclusiones["emails"]}
    if antes != len(documentos):
        log(f"Excluidos {antes - len(documentos)} perfiles de prueba")

    supa = Supa(url, key)
    log("Consultando participants (programa=jc) en Supabase...")
    participantes = supa.get_todo(
        "/participants?select=id,q10_id,nombre,enrollments!inner(courses!inner(programa))"
        "&enrollments.courses.programa=eq.jc")
    q10_a_participant = {p["q10_id"]: p["id"] for p in participantes if p.get("q10_id")}
    log(f"Participantes JC en Supabase: {len(q10_a_participant)}")

    con_match = sum(1 for ced in documentos if ced in q10_a_participant)
    log(f"Universo Mongo JC: {len(documentos)} · con match en participants: {con_match} "
        f"· exclusivos (sin match): {len(documentos) - con_match}")

    filas = []
    for ced, d in sorted(documentos.items()):
        fila = {
            "cedula": ced,
            "nombre": d.get("nombre") or None,
            "email": d.get("email") or None,
            "celular": d.get("celular") or None,
            "ciudad": d.get("ciudad") or None,
            "promo_year": str(d["promo_year"]) if d.get("promo_year") is not None else None,
            "rol": d.get("rol") or None,
            "fecha_creacion": d.get("fecha_creacion") or None,
            "fuente": _fuente(d.get("coleccion", "User")),
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        }
        fila = {k: v for k, v in fila.items() if v is not None}
        pid = q10_a_participant.get(ced)
        if pid:
            fila["participant_id"] = pid
        filas.append(fila)

    if args.dry_run:
        print(f"RESUMEN: total={len(documentos)} cargados=0 con_match_participant={con_match} estado=dry_run")
        return 0

    grupos: dict[frozenset, list] = {}
    for fila in filas:
        grupos.setdefault(frozenset(fila), []).append(fila)
    for _, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            supa._req("POST", "/postulantes_jc?on_conflict=cedula", grupo[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
    log(f"Cargados: {len(filas)} (en {len(grupos)} grupos de columnas)")

    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump({"_nota": "PII — no subir a git", "generado": datetime.now().isoformat(timespec="seconds"),
                   "total": len(documentos), "cargados": len(filas), "con_match_participant": con_match},
                  f, ensure_ascii=False, indent=1)
    log(f"Reporte → {RUTA_REPORTE}")

    print(f"RESUMEN: total={len(documentos)} cargados={len(filas)} "
          f"con_match_participant={con_match} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
