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
from datetime import datetime, timezone

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

    def get_todo_paginas(self, ruta: str, page: int = 1000):
        """Igual que get_todo() pero yield por página en vez de acumular todo en
        memoria — usar solo para tablas con filas muy pesadas (ej. blobs jsonb
        grandes en participants_snapshots), donde escribir a disco incrementalmente
        evita tener la tabla completa duplicada en RAM."""
        offset = 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            if not lote:
                return
            yield lote
            if len(lote) < page:
                return
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
    # UTC (no hora local): coherente con v_frescura, que compara updated_at contra now() en UTC.
    # Hora local (COT) inflaba la frescura +5h. `hoy_snapshot` (más abajo) SÍ usa la fecha local a
    # propósito (día calendario del operador). Ver runbooks/recuperacion-frescura.md.
    ahora = datetime.now(timezone.utc).replace(tzinfo=None).isoformat(timespec="seconds")

    # 0. Absorber renombres de curso ya confirmados (tabla cursos_alias, migración 026).
    #    Q10 permite renombrar un curso sin aviso previo (pasó el 2026-07-24 con
    #    "DESARROLLO WEB FRONT-END - HTML - 2026" → "... - HTML Y CSS - 2026"). Como el
    #    export h2test NO trae código de curso, `courses` se identifica por nombre+cohorte:
    #    sin este remapeo un renombre crea un curso NUEVO y duplica la cohorte entera en
    #    courses/enrollments/aprobacion_cursos/historial_cursos. Remapear ANTES de todo
    #    upsert. El detector de renombres nuevos es v_choques_cursos (migración 027); esta
    #    tabla solo contiene los que ya confirmó una persona.
    filas_alias = supa.get_todo("/cursos_alias?select=cohorte,nombre_viejo,nombre_nuevo")
    remap = {a["nombre_viejo"].strip().upper(): a["nombre_nuevo"]
             for a in filas_alias if a["cohorte"] == payload["cohorte"]}
    if remap:
        n_c = 0
        for c in courses:
            nuevo = remap.get(c["nombre"].strip().upper())
            if nuevo and nuevo != c["nombre"]:
                c["nombre"] = nuevo
                n_c += 1
        n_e = 0
        for e in enrolls:
            nuevo = remap.get(e["curso"].strip().upper())
            if nuevo and nuevo != e["curso"]:
                e["curso"] = nuevo
                n_e += 1
        # Un renombre puede colapsar dos entradas en una sola clave. Hay que deduplicar
        # ANTES del upsert: PostgREST falla con "ON CONFLICT DO UPDATE command cannot
        # affect row a second time" si el mismo lote trae la clave repetida.
        dedup_c = {(c["nombre"], c["cohorte"]): c for c in courses}
        courses = list(dedup_c.values())
        dedup_e = {}
        for e in enrolls:
            clave = (e["q10_id"], e["curso"])
            previo = dedup_e.get(clave)
            # keepMax: mismo criterio que normalize_q10_data.py para matrículas duplicadas.
            if previo is None or e["porcentaje_avance"] > previo["porcentaje_avance"]:
                dedup_e[clave] = e
        if len(dedup_e) != len(enrolls):
            log(f"Renombre colapsó {len(enrolls) - len(dedup_e)} matrículas duplicadas (keepMax)")
        enrolls = list(dedup_e.values())
        log(f"Renombres absorbidos desde cursos_alias: {n_c} cursos, {n_e} matrículas")

    # 1. Snapshot del estado ANTERIOR (Decisión 2: rollback + auditoría) — una vez al día.
    #    Este script corre varias veces al día (sync incremental); on_conflict=snapshot_date
    #    hace que las corridas 2ª+ del mismo día pisen la misma fila sin aportar nada, pero
    #    igual pagaban el costo de un SELECT * completo de participants en cada corrida
    #    (principal fuente de egress de Supabase, 2026-08-05). Se evita ese SELECT * redundante
    #    consultando antes si ya existe snapshot de hoy (query de 1 fila, no la tabla entera).
    hoy_snapshot = datetime.now().date().isoformat()
    ya_snapshot = supa.get_todo(
        f"/participants_snapshots?select=snapshot_date&snapshot_date=eq.{hoy_snapshot}")
    snapshot_n = 0
    if ya_snapshot:
        log(f"Snapshot de hoy ({hoy_snapshot}) ya existe — se omite el SELECT * de participants")
    else:
        previos = supa.get_todo("/participants?select=*")
        if previos:
            supa.upsert("participants_snapshots",
                        [{"snapshot_date": hoy_snapshot,
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
    #    visto_en_fuente_at sella "la fuente confirmó este curso en esta corrida"
    #    (migración 026). Es lo que permite distinguir un curso que dejó de dar clases de un
    #    pipeline roto, SIN inventar una fecha de cierre que Q10 no tiene.
    #    ⚠ Los cursos que NO vienen en el payload conservan su sello viejo a propósito: no se
    #    borran ni se marcan cerrados, porque Q10 permite retomar actividad en cursos pasados
    #    y en ese caso reviven solos en la siguiente corrida, sin intervención humana.
    #    ⚠ `estado` viene hardcodeado como "activo" desde normalize_q10_data.py y NO es un
    #    ciclo de vida real (el curso MR que cerró clases en julio 2026 sigue en "activo").
    #    Para saber si un curso está vigente usar visto_en_fuente_at, nunca estado.
    filas_c = [{**c, "visto_en_fuente_at": ahora} for c in courses]
    supa.upsert("courses", filas_c, conflicto="nombre,cohorte")
    log(f"Courses upsert: {len(filas_c)}")

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
    #    ⚠ Filtrar a la cohorte viva es OBLIGATORIO: Q10 reutiliza los nombres de curso
    #    entre años, así que v_curso_completion trae el mismo `curso` en varias cohortes
    #    (desde el import histórico del 2026-07-10). Sin el filtro, el lote lleva `curso`
    #    repetido y PostgREST aborta TODO el upsert con 21000 "ON CONFLICT DO UPDATE
    #    command cannot affect row a second time" — así se rompió el sync diario.
    hoy = datetime.now().date().isoformat()
    filas_h = [{
        "fecha": hoy, "curso": v["curso"], "programa": v["programa"],
        "matriculados": v["matriculados"], "completados": v["completados"],
        "promedio_avance": v["promedio_avance"], "fuente": "sync-diario",
    } for v in supa.get_todo(f"/v_curso_completion?select=*&cohorte=eq.{cohorte}")]
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
    } for v in supa.get_todo(f"/v_curso_completion_por_ciudad?select=*&cohorte=eq.{cohorte}")]
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
