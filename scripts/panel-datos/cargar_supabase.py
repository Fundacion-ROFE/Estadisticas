# -*- coding: utf-8 -*-
"""
cargar_supabase.py — Carga el payload normalizado a Supabase (panel-datos-rofe).

Consume tools/supabase_payload.json (generado por normalize_q10_data.py) y hace:
  1. Snapshot de participants → participants_snapshots (rollback/auditoría, Decisión 2)
  2. Upsert participants   (on_conflict=q10_id)
  3. Upsert courses        (on_conflict=nombre,cohorte)
  4. Resolución de FKs (q10_id→UUID, nombre curso→UUID) y upsert enrollments
     (on_conflict=participant_id,course_id)
  5. RPC recompute_aggregates() → participant_metrics + cohorte_stats

Credenciales: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY de .env.local (raíz) o entorno.
El service_role bypasea RLS — este script es SOLO backend/n8n, jamás exponerlo.

⚠ Gotcha Supabase: las secret keys se rechazan si el User-Agent parece navegador
("Mozilla...") → siempre mandamos UA propio 'panel-datos-etl/1.0'.

Uso:
    python normalize_q10_data.py      # PRIMERO — genera el payload
    python cargar_supabase.py         # carga
    python cargar_supabase.py --dry-run   # solo reporta qué haría
Consola (parseable por n8n):
    RESUMEN: participants=N courses=K enrollments=M snapshot=S estado=exito

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
    truststore.inject_into_ssl()  # SSL corporativo (convención del proyecto)
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "supabase_payload.json")
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")

USER_AGENT  = "panel-datos-etl/1.0"  # NO Mozilla — Supabase bloquea secrets "de navegador"
LOTE        = 500                    # filas por request (mismo espíritu que TAMANIO_LOTE)


def log(msg: str) -> None:
    print(f"[cargar-supabase] {msg}", flush=True)


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
    """Cliente REST mínimo (stdlib) con service key."""

    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def _req(self, metodo: str, ruta: str, cuerpo=None, prefer: str = ""):
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        if prefer:
            headers["Prefer"] = prefer
        req = urllib.request.Request(
            self.base + ruta, method=metodo, headers=headers,
            data=json.dumps(cuerpo).encode() if cuerpo is not None else None)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:500]
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: {detalle}") from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        """GET paginado (PostgREST corta en ~1000 filas por defecto)."""
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page

    def upsert(self, tabla: str, filas: list, conflicto: str) -> int:
        """Upsert por lotes. Retorna filas enviadas."""
        for i in range(0, len(filas), LOTE):
            self._req("POST", f"/{tabla}?on_conflict={conflicto}", filas[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
        return len(filas)


def main() -> int:
    ap = argparse.ArgumentParser(description="Carga payload normalizado a Supabase")
    ap.add_argument("--dry-run", action="store_true", help="Solo reporta, no escribe")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (.env.local o entorno)")
        return 1
    if not os.path.isfile(RUTA_PAYLOAD):
        log("ERROR: falta tools/supabase_payload.json — corre normalize_q10_data.py primero")
        return 1

    with open(RUTA_PAYLOAD, encoding="utf-8") as f:
        payload = json.load(f)
    parts, courses, enrolls = payload["participants"], payload["courses"], payload["enrollments"]
    log(f"Payload {payload['generado']}: {len(parts)} participants, "
        f"{len(courses)} courses, {len(enrolls)} enrollments")

    if args.dry_run:
        print(f"RESUMEN: participants={len(parts)} courses={len(courses)} "
              f"enrollments={len(enrolls)} snapshot=0 estado=dry_run")
        return 0

    supa = Supa(url, key)
    ahora = datetime.now().isoformat(timespec="seconds")

    # 1. Snapshot del estado ANTERIOR (Decisión 2: rollback + auditoría)
    previos = supa.get_todo("/participants?select=*")
    snapshot_n = 0
    if previos:
        supa.upsert("participants_snapshots",
                    [{"snapshot_date": datetime.now().date().isoformat(),
                      "row_count": len(previos), "data": previos}],
                    conflicto="snapshot_date")
        snapshot_n = len(previos)
        log(f"Snapshot previo: {snapshot_n} filas → participants_snapshots")
    else:
        log("BD vacía — sin snapshot previo (primera carga)")

    # 2. Participants (upsert por q10_id)
    filas_p = [{**p, "updated_at": ahora} for p in parts]
    supa.upsert("participants", filas_p, conflicto="q10_id")
    log(f"Participants upsert: {len(filas_p)}")

    # 3. Courses (upsert por nombre+cohorte — constraint courses_nombre_cohorte_unique)
    supa.upsert("courses", courses, conflicto="nombre,cohorte")
    log(f"Courses upsert: {len(courses)}")

    # 4. Enrollments — resolver FKs y upsert
    mapa_p = {r["q10_id"]: r["id"] for r in supa.get_todo("/participants?select=id,q10_id")}
    mapa_c = {(r["nombre"], r["cohorte"]): r["id"]
              for r in supa.get_todo("/courses?select=id,nombre,cohorte")}
    cohorte = payload["cohorte"]
    filas_e, sin_fk = [], 0
    for e in enrolls:
        pid = mapa_p.get(e["q10_id"])
        cid = mapa_c.get((e["curso"], cohorte))
        if not pid or not cid:
            sin_fk += 1
            continue
        filas_e.append({
            "participant_id": pid, "course_id": cid,
            "porcentaje_avance": e["porcentaje_avance"], "estado": e["estado"],
            "updated_at": ahora,
        })
    if sin_fk:
        log(f"ADVERTENCIA: {sin_fk} enrollments sin FK resoluble (no cargados)")
    supa.upsert("enrollments", filas_e, conflicto="participant_id,course_id")
    log(f"Enrollments upsert: {len(filas_e)}")

    # 5. Recompute de agregados (participant_metrics + cohorte_stats)
    _, agg = supa._req("POST", "/rpc/recompute_aggregates", {})
    log(f"Agregados recomputados: {agg}")

    # 6. Snapshot del día en historial_cursos (serie de tiempo pública).
    #    UNIQUE(fecha, curso) → re-correr el mismo día actualiza, no duplica.
    hoy = datetime.now().date().isoformat()
    filas_h = [{
        "fecha": hoy, "curso": v["curso"], "programa": v["programa"],
        "matriculados": v["matriculados"], "completados": v["completados"],
        "promedio_avance": v["promedio_avance"], "fuente": "sync-diario",
    } for v in supa.get_todo("/v_curso_completion?select=*")]
    supa.upsert("historial_cursos", filas_h, conflicto="fecha,curso")
    log(f"Historial: snapshot {hoy} con {len(filas_h)} cursos")

    # 7. Mismo snapshot desglosado por ciudad (grupo_ciudad viene de la BD de monitorias,
    #    solo existe para JC). Serie independiente: arranca 2026-07-14, el pasado no es
    #    reconstruible porque historial_cursos nunca guardó la dimensión ciudad.
    filas_hc = [{
        "fecha": hoy, "curso": v["curso"], "grupo_ciudad": v["grupo_ciudad"],
        "programa": v["programa"], "cohorte": v["cohorte"],
        "matriculados": v["matriculados"], "completados": v["completados"],
        "promedio_avance": v["promedio_avance"], "fuente": "sync-diario",
    } for v in supa.get_todo("/v_curso_completion_por_ciudad?select=*")]
    supa.upsert("historial_cursos_ciudad", filas_hc, conflicto="fecha,curso,grupo_ciudad")
    log(f"Historial ciudad: snapshot {hoy} con {len(filas_hc)} filas curso×ciudad")

    estado = "exito" if sin_fk == 0 else "con_advertencias"
    print(f"RESUMEN: participants={len(filas_p)} courses={len(courses)} "
          f"enrollments={len(filas_e)} snapshot={snapshot_n} "
          f"metricas={agg.get('participant_metrics', 0)} cohortes={agg.get('cohorte_stats', 0)} "
          f"estado={estado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
