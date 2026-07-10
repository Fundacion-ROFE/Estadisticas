# -*- coding: utf-8 -*-
"""
importar_historico_q10.py — Cohortes pasadas (2023-2025) de Q10 → Supabase.

Descarga el Consolidado de Educación Virtual de los periodos históricos (mapa
EXPLÍCITO abajo — sin inferencias en runtime), normaliza con las mismas reglas
del sync diario y carga participants/courses/enrollments por cohorte-año.

Decisiones "sin margen de error" (validadas con sondeo 2026-07-10, ver
tools/sondeo_periodos_20260710.json):
  - Mapa periodo→(cohorte, programa_override) EXPLÍCITO. "Único Horario nivel 1-3"
    (pids 10/12/14, sin año en la etiqueta) se asigna a 2024 — están entre los
    periodos 2023 y 2025 y "Único 2024" (pid 9) es su vecino. CONFIRMABLE con el equipo.
  - pid 16 "Unico 2025" = ruta Mujeres ROFÉ 2025 completa (cursos de emprendedoras)
    → programa mr forzado a nivel de periodo.
  - Q10 REUTILIZA nombres de curso entre años ("...- 2026" aparece en cohorte 2023):
    UNIQUE(nombre, cohorte) los separa correctamente.
  - Cohorte 2026 NO se importa aquí — es del sync diario (h2test). Evita doble fuente.
  - Participantes YA existentes en Supabase NO se tocan (el sync 2026 es más fresco);
    solo se insertan cédulas nuevas (histórico puro).
  - Retirados históricos (inhabilitados) NO salen del Consolidado — las cohortes
    pasadas representan a quienes permanecieron. Limitación de Q10, documentada.
  - Exclusiones: perfiles de prueba (tools/exclusiones_prueba.json) + desertores
    (pestaña Retirados, Tipo=Desertor) fuera de todo, igual que el sync diario.

Idempotente: upserts por claves naturales; re-correr no duplica.

Uso:
    python importar_historico_q10.py [--dry-run] [--solo-pid N]
Consola (parseable):
    RESUMEN: participantes_nuevos=N cursos=K matriculas=M cohortes=C errores=E estado=exito
"""

import argparse
import io
import json
import os
import sys
from collections import Counter
from datetime import datetime

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
sys.path.insert(0, os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion"))

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import q10_to_sheets as q10                      # login + descarga Consolidado (truststore ya inyectado)
from normalize_q10_data import (                 # mismas reglas del sync diario
    Reporte, cargar_config_cursos, cargar_exclusiones, clasificar_curso,
    estado_matricula, norm_id, norm_texto, normalizar_avance, RE_EMAIL,
)
from cargar_supabase import Supa, cargar_env_local

# ── Mapa EXPLÍCITO periodo Q10 → (cohorte, programa forzado | None) ───────────
# None en programa → clasificar por curso (course_config + keywords, default jc)
MAPA_PERIODOS = {
    2:  ("2023", None),  # Único Egresados nivel 1 2023
    3:  ("2023", None),  # Único Colegios nivel 1 2023
    4:  ("2023", None),  # Único Colegios nivel 2 2023
    5:  ("2023", None),  # Único egresados nivel 2 2023
    6:  ("2023", None),  # Único Colegios nivel 3 2023
    7:  ("2023", None),  # Único Egresados nivel 3 2023
    9:  ("2024", None),  # Único 2024
    10: ("2024", None),  # Único Horario nivel 1  (sin año — asignado 2024, confirmar)
    12: ("2024", None),  # Único Horario nivel 2  (idem)
    14: ("2024", None),  # Único Horario nivel 3  (idem)
    16: ("2025", "mr"),  # Unico 2025 = ruta Mujeres ROFÉ 2025 completa
    17: ("2025", None),  # Desarrollo-Nivel 3-2025
    18: ("2025", None),  # Logica-Nivel 2-2025
    19: ("2025", None),  # Habilidades-Nivel 1-2025
}

RUTA_REPORTE = os.path.join(PROYECTO_ROOT, "tools",
                            f"importar_historico_report_{datetime.now():%Y%m%d}.json")


def log(m):
    print(f"[import-historico] {m}", flush=True)


def leer_desertores_q10(session) -> set:
    """Cédulas Tipo=Desertor del reporte histórico de cancelados (excluidos de todo)."""
    df = q10.descargar_retirados(session)
    if df is None or df.empty:
        return set()
    df = q10.mapear_columnas_retirados(df)
    if "Tipo" not in df.columns or "Identificacion" not in df.columns:
        return set()
    mask = df["Tipo"].astype(str).str.strip().str.lower() == "desertor"
    return {norm_id(v) for v in df.loc[mask, "Identificacion"]} - {""}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--solo-pid", type=int, default=None, help="Importar un solo periodo (prueba)")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales Supabase")
        return 1

    config = cargar_config_cursos()
    excl_ceds, excl_emails = cargar_exclusiones()
    rep = Reporte()

    session = q10.login_q10()
    desertores = leer_desertores_q10(session)
    log(f"Desertores históricos excluidos: {len(desertores)}")

    pids = [args.solo_pid] if args.solo_pid else sorted(MAPA_PERIODOS)
    participants: dict[str, dict] = {}
    courses: dict[tuple, dict] = {}      # (nombre, cohorte) → fila
    enrollments: dict[tuple, dict] = {}  # (cedula, nombre, cohorte) → fila

    for pid in pids:
        cohorte, prog_forzado = MAPA_PERIODOS[pid]
        df = q10.descargar_consolidado_periodo(session, pid)
        if df is None or df.empty:
            log(f"ADVERTENCIA: pid {pid} sin datos — ¿cambió Q10?")
            rep.warn("periodo_vacio", {"pid": pid})
            continue
        etiqueta = q10._etiqueta_periodo(df)
        n_filas = 0
        for _, fila in df.iterrows():
            cedula = norm_id(fila.get(q10.COL_ID, ""))
            if not cedula:
                rep.error("cedula_invalida", {"pid": pid, "valor": str(fila.get(q10.COL_ID))[:30]})
                continue
            email = norm_texto(fila.get(q10.COL_EMAIL, "")).lower()
            if cedula in excl_ceds or email in excl_emails:
                rep.contadores["excluido_prueba"] += 1
                continue
            if cedula in desertores:
                rep.contadores["excluido_desertor"] += 1
                continue
            curso = norm_texto(fila.get(q10.COL_CURSO, ""))
            if not curso:
                rep.error("curso_vacio", {"pid": pid, "cedula": cedula})
                continue
            avance = normalizar_avance(str(fila.get(q10.COL_AVANCE, "")), curso, cedula, rep)
            if avance is None:
                continue
            nombre = norm_texto(f"{fila.get(q10.COL_NOMBRES, '')} {fila.get(q10.COL_APELLIDOS, '')}")
            if email and not RE_EMAIL.match(email):
                rep.warn("email_invalido", {"cedula": cedula, "email": email})
                email = ""

            participants.setdefault(cedula, {
                "q10_id": cedula, "nombre": nombre or "(sin nombre)", "email": email or None,
            })
            programa = prog_forzado or clasificar_curso(curso, config)
            courses.setdefault((curso, cohorte), {
                "nombre": curso, "cohorte": cohorte, "estado": "completado",
                "programa": programa,
            })
            clave = (cedula, curso, cohorte)
            if clave in enrollments:
                if avance > enrollments[clave]["porcentaje_avance"]:
                    enrollments[clave]["porcentaje_avance"] = int(round(avance))
                    enrollments[clave]["estado"] = estado_matricula(avance)
                rep.warn("matricula_duplicada", {"cedula": cedula, "curso": curso, "cohorte": cohorte})
            else:
                enrollments[clave] = {
                    "cedula": cedula, "curso": curso, "cohorte": cohorte,
                    "porcentaje_avance": int(round(avance)),
                    "estado": estado_matricula(avance),
                }
            n_filas += 1
        log(f"pid {pid} ({etiqueta} → cohorte {cohorte}): {n_filas} matrículas válidas")

    cohortes = sorted({c for _, c in courses})
    log(f"Total: {len(participants)} cédulas · {len(courses)} cursos·cohorte · "
        f"{len(enrollments)} matrículas · cohortes {cohortes}")

    if args.dry_run:
        print(f"RESUMEN: participantes_nuevos=? cursos={len(courses)} "
              f"matriculas={len(enrollments)} cohortes={len(cohortes)} "
              f"errores={len(rep.errores)} estado=dry_run")
        return 0

    supa = Supa(url, key)

    # Participantes: SOLO cédulas nuevas (no tocar a los del sync 2026)
    existentes = {r["q10_id"] for r in supa.get_todo("/participants?select=q10_id")}
    nuevos = [participants[c] for c in sorted(set(participants) - existentes)]
    if nuevos:
        supa.upsert("participants", nuevos, conflicto="q10_id")
    log(f"Participantes nuevos insertados: {len(nuevos)} "
        f"(ya existían: {len(set(participants) & existentes)})")

    # Cursos por cohorte
    supa.upsert("courses", [courses[k] for k in sorted(courses)], conflicto="nombre,cohorte")
    log(f"Courses upsert: {len(courses)}")

    # Enrollments con FKs
    mapa_p = {r["q10_id"]: r["id"] for r in supa.get_todo("/participants?select=id,q10_id")}
    mapa_c = {(r["nombre"], r["cohorte"]): r["id"]
              for r in supa.get_todo("/courses?select=id,nombre,cohorte")}
    filas_e, sin_fk = [], 0
    for (ced, curso, coh), e in sorted(enrollments.items()):
        pid_, cid = mapa_p.get(ced), mapa_c.get((curso, coh))
        if not pid_ or not cid:
            sin_fk += 1
            continue
        filas_e.append({"participant_id": pid_, "course_id": cid,
                        "porcentaje_avance": e["porcentaje_avance"], "estado": e["estado"],
                        "updated_at": datetime.now().isoformat(timespec="seconds")})
    supa.upsert("enrollments", filas_e, conflicto="participant_id,course_id")
    log(f"Enrollments upsert: {len(filas_e)} (sin_fk: {sin_fk})")

    _, agg = supa._req("POST", "/rpc/recompute_aggregates", {})
    log(f"Agregados recomputados: {agg}")

    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump({"generado": datetime.now().isoformat(timespec="seconds"),
                   "participantes_nuevos": len(nuevos), "cursos": len(courses),
                   "matriculas": len(filas_e), "cohortes": cohortes,
                   "contadores": dict(rep.contadores),
                   "errores": rep.errores, "advertencias": rep.advertencias[:200]},
                  f, ensure_ascii=False, indent=1)
    log(f"Reporte → {RUTA_REPORTE}")

    estado = "exito" if not rep.errores and sin_fk == 0 else "con_errores"
    print(f"RESUMEN: participantes_nuevos={len(nuevos)} cursos={len(courses)} "
          f"matriculas={len(filas_e)} cohortes={len(cohortes)} "
          f"errores={len(rep.errores)} estado={estado}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
