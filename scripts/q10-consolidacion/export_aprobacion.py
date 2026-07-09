# -*- coding: utf-8 -*-
"""
export_aprobacion.py — Aprobación por curso (cohorte 2026 completa) → docs/aprobacion/data.json

Cruza tres fuentes de Q10 por cédula para reconstruir la cohorte COMPLETA de cada
curso (habilitados + inhabilitados) y calcular % de aprobación real:

  1. Consolidado Educación Virtual (por periodo)   → activos con avance por asignatura
  2. Detallado Estudiantes Matriculados (por periodo) → cohorte completa (incluye inhabilitados)
  3. Reporte Estudiantes cancelados (histórico)     → confirma que inhabilitado = retirado

Aprobado = avance >= 100 (hay casos de 101). Verificado 2026-07-07: en el periodo 22
los 80 inhabilitados (860 matriculados - 780 activos) aparecen TODOS en el reporte de
retirados.

Q10 inhabilita TODAS las matrículas del estudiante (no solo la del curso perdido) y el
Consolidado deja de traer su avance. Para no perder a los que YA habían aprobado un
curso antes de inhabilitarse, se mantiene un ledger local (tools/aprobacion_ledger.json,
PII, gitignoreado) con el máximo avance visto por estudiante×curso en cada corrida.
Con él, cada inhabilitado se clasifica por curso en:
  - aprobados_retirados: alcanzó avance >= 100 antes de inhabilitarse
  - retirados:           se retiró sin aprobar el curso
Sembrar el ledger con la hoja manual: python tools/seed_ledger_avance.py

El JSON público solo lleva agregados (NUNCA PII). Marca de agua en
docs/aprobacion/maximos.json: `aprobados` (total incl. aprobados_retirados) nunca decae;
si el conteo vivo baja, el déficit se reclasifica como "aprobó y se retiró".

Fundación ROFÉ | Jóvenes creaTIvos

Uso:
    python export_aprobacion.py                # año en curso, commit + push
    python export_aprobacion.py --sin-push     # genera JSON sin tocar git (pruebas)
    python export_aprobacion.py --anio 2026
"""

import argparse
import io
import json
import os
import re
import subprocess
import sys
from datetime import datetime

# truststore: en Windows con interceptación SSL corporativa, usa el cert store del SO
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# UTF-8 en consola Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

from q10_to_sheets import (
    login_q10,
    descargar_consolidado_periodo,
    descargar_retirados,
    descargar_excel,
    _headers_reporte,
    _etiqueta_periodo,
    _periodo_es_del_anio,
    Q10_BASE_URL,
    RANGO_PERIODOS,
    AÑO_OBJETIVO,
    COL_PERIODO,
    COL_ID,
    COL_CURSO,
    COL_AVANCE,
)

COL_PROGRAMA = "Nombre programa"

UMBRAL_APROBADO     = 100.0  # avance >= 100 aprueba (hay 101 por actividades extra)
UMBRAL_PROMEDIO_FIN = 90.0   # promedio de activos >= 90% → curso se considera finalizado

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_DATA_JSON    = os.path.join(PROYECTO_ROOT, "docs", "aprobacion", "data.json")
RUTA_MAXIMOS      = os.path.join(PROYECTO_ROOT, "docs", "aprobacion", "maximos.json")
RUTA_LEDGER       = os.path.join(PROYECTO_ROOT, "tools", "aprobacion_ledger.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
RUTA_COHORTE      = os.path.join(PROYECTO_ROOT, "tools", "cohorte_2026.json")


def log(msg: str) -> None:
    print(f"[export-aprobacion] {msg}", flush=True)


# ── Utilidades de normalización ───────────────────────────────────────────────
def norm_id(valor) -> str:
    """Cédula comparable entre reportes: solo dígitos ('C.C. 1016715076' → '1016715076')."""
    return re.sub(r"\D", "", str(valor))


def norm_curso(nombre) -> str:
    """Nombre de asignatura sin \\xa0 ni espacios repetidos (clave de agrupación)."""
    return re.sub(r"\s+", " ", str(nombre).replace("\xa0", " ")).strip()


def parse_avance(serie: pd.Series) -> pd.Series:
    """'100%' / '85,5%' → float. El Consolidado trae el progreso como texto con %."""
    limpio = serie.astype(str).str.replace("%", "", regex=False).str.replace(",", ".")
    return pd.to_numeric(limpio, errors="coerce")


# ── Exclusión de usuarios de prueba ───────────────────────────────────────────
def cargar_exclusiones() -> set:
    """Cédulas de perfiles de prueba (tools/exclusiones_prueba.json, gitignoreado).
    No deben contar en ningún KPI, tabla ni como retirados."""
    ceds = set()
    if os.path.isfile(RUTA_EXCLUSIONES):
        try:
            with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
                for p in json.load(f).get("perfiles", []):
                    ced = norm_id(p.get("cedula", ""))
                    if ced:
                        ceds.add(ced)
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: exclusiones ilegibles ({e}) — no se excluye nada")
    return ceds


def aplicar_exclusiones(virtual: dict, cohortes: dict, retirados: dict,
                        ledger: dict, excl: set) -> None:
    """Elimina las cédulas de prueba de todas las fuentes antes de agregar."""
    if not excl:
        return
    quitadas = 0
    for pid, df in virtual.items():
        mask = df[COL_ID].map(norm_id).isin(excl)
        quitadas += int(mask.sum())
        virtual[pid] = df[~mask]
    for info in cohortes.values():
        info["ids"] -= excl
        info["n"] = len(info["ids"])
    for ced in excl:
        retirados.pop(ced, None)
        ledger.pop(ced, None)
    log(f"Exclusión de pruebas: {len(excl)} cédulas — {quitadas} filas quitadas del Consolidado")


# ── Ledger local de avances (PII — tools/ está gitignoreado) ─────────────────
def cargar_ledger() -> dict:
    """{cedula: {curso_norm: max_avance}} — memoria del máximo avance visto por
    estudiante×curso. Q10 borra el avance al inhabilitar (el Consolidado solo
    trae activos), así que sin esta memoria no se puede saber si un inhabilitado
    ya había aprobado. Se siembra desde la hoja manual con
    tools/seed_ledger_avance.py y se actualiza sola en cada corrida."""
    if os.path.isfile(RUTA_LEDGER):
        try:
            with open(RUTA_LEDGER, encoding="utf-8") as f:
                ledger = json.load(f).get("estudiantes", {})
            log(f"Ledger de avances: {len(ledger)} estudiantes")
            return ledger
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: ledger ilegible ({e}) — se regenera desde cero")
    else:
        log("Ledger de avances: no existe aún — se crea en esta corrida "
            "(sembrar histórico con tools/seed_ledger_avance.py)")
    return {}


def actualizar_ledger(ledger: dict, virtual: dict) -> None:
    """Registra el máximo avance de cada activo. keepMax: nunca decae."""
    nuevos = 0
    for df in virtual.values():
        ceds    = df[COL_ID].map(norm_id)
        cursos  = df[COL_CURSO].map(norm_curso)
        avances = parse_avance(df[COL_AVANCE])
        for ced, curso, av in zip(ceds, cursos, avances):
            if not ced or not curso or pd.isna(av):
                continue
            d = ledger.setdefault(ced, {})
            if float(av) > d.get(curso, -1.0):
                if curso not in d:
                    nuevos += 1
                d[curso] = float(av)
    log(f"  ledger: {len(ledger)} estudiantes ({nuevos} registros estudiante×curso nuevos)")


def guardar_cohorte(prog_stats_raw: dict, anio: str) -> None:
    """Persiste la cohorte 2026 y los retirados únicos (cédulas) por programa,
    para que export_retirados.py filtre el histórico a 2026 sin re-descargar de Q10.
    Contiene PII → vive en tools/ (gitignoreado), NUNCA subir a git.

    'retirados' = inhabilitados de la cohorte del periodo (misma definición que el
    KPI 'retirados_unicos' del panel de aprobación). Es la fuente autoritativa de
    quién se retiró en 2026 — NO se usa FechaCancelacion (poco fiable)."""
    payload = {
        "_nota": ("Cohorte 2026 y retirados únicos por programa (cédulas, PII). "
                  "Generado por export_aprobacion.py; consumido por export_retirados.py. "
                  "tools/ está gitignoreado — NUNCA subir a git."),
        "actualizado": datetime.now().astimezone().isoformat(),
        "anio": anio,
        "por_programa": {
            prog: {
                "cohorte":   sorted(v["cohorte"]),
                "retirados": sorted(v["retirados"]),
            }
            for prog, v in prog_stats_raw.items()
        },
    }
    os.makedirs(os.path.dirname(RUTA_COHORTE), exist_ok=True)
    with open(RUTA_COHORTE, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False)
    tot_ret = sum(len(v["retirados"]) for v in prog_stats_raw.values())
    log(f"  cohorte_2026.json actualizado ({len(prog_stats_raw)} programas, "
        f"{tot_ret} retirados únicos)")


def guardar_ledger(ledger: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_LEDGER), exist_ok=True)
    with open(RUTA_LEDGER, "w", encoding="utf-8") as f:
        json.dump({
            "_nota": ("Máximo avance visto por estudiante×curso. Contiene cédulas "
                      "(PII) — vive en tools/ (gitignoreado), NUNCA subir a git."),
            "actualizado": datetime.now().astimezone().isoformat(),
            "estudiantes": ledger,
        }, f, ensure_ascii=False)


# ── Q10: Detallado Estudiantes Matriculados (incluye inhabilitados) ──────────
def descargar_matriculados_periodo(session, periodo_id: int) -> pd.DataFrame | None:
    """Reporte 'Consolidado de estudiantes matriculados' en modo Detallado.

    A diferencia del Consolidado de Educación Virtual (que solo trae activos y cuyo
    switch 'archivado' NO cambia el resultado — verificado 2026-07-07), este reporte
    incluye a TODOS los matriculados del periodo, habilitados e inhabilitados.
    Columnas: Programa | Jornada | Nivel | Estudiante | Identificación.
    El POST exige replicar los hidden Filtros[i].Name/PartialName del formulario.
    """
    url = f"{Q10_BASE_URL}/Reportes/Excel/GestionAcademica/ConsolidadoEstudiantesMatriculados"
    payload = [
        ("Titulo", "Consolidado de matriculados por semestre"),
        ("Filtros[0].Name", "Periodo"), ("Filtros[0].PartialName", "_SelectFilter"),
        ("Periodo", str(periodo_id)),
        ("Filtros[1].Name", "CondicionMatricula"), ("Filtros[1].PartialName", "_SelectFilter"),
        ("CondicionMatricula", ""),
        ("Filtros[2].Name", "filtro"), ("Filtros[2].PartialName", "_RadioFilter"),
        ("filtro", "D"),
        ("Filtros[3].Name", "programa"), ("Filtros[3].PartialName", "_SelectFilter"),
        ("programa", ""),
    ]
    resp = session.post(url, data=payload, headers=_headers_reporte(), timeout=120)
    if resp.status_code != 200:
        log(f"    matriculados p{periodo_id}: HTTP {resp.status_code} — {resp.text[:120]}")
        return None
    datos = resp.json()
    if datos.get("not_results") or not datos.get("url"):
        log(f"    matriculados p{periodo_id}: sin datos ({datos})")
        return None

    df = pd.read_excel(io.BytesIO(descargar_excel(session, datos["url"])),
                       header=None, dtype=str)
    # El Excel trae título/filtros arriba; los headers reales están en la fila
    # que contiene 'Identificación'
    fila_hdr = None
    for i in range(min(15, len(df))):
        if "Identificación" in df.iloc[i].astype(str).values:
            fila_hdr = i
            break
    if fila_hdr is None:
        log(f"    matriculados p{periodo_id}: no se encontró la fila de headers")
        return None
    df.columns = df.iloc[fila_hdr]
    df = df.iloc[fila_hdr + 1:].reset_index(drop=True)
    df = df.dropna(subset=["Identificación"])
    return df


# ── Descarga de todas las fuentes del año ─────────────────────────────────────
def descargar_fuentes(session, anio: str) -> tuple[dict, dict, dict]:
    """Retorna (virtual_por_periodo, cohorte_por_periodo, retirados_por_id).

    virtual_por_periodo: {pid: DataFrame consolidado virtual (solo activos)}
    cohorte_por_periodo: {pid: {"etiqueta": str, "ids": set, "n": int}}
    retirados_por_id:    {cedula_norm: tipo_retiro}
    """
    log(f"Autodescubriendo periodos del año {anio} "
        f"(sondeando IDs {RANGO_PERIODOS.start}–{RANGO_PERIODOS.stop - 1})...")
    virtual, cohortes = {}, {}
    for pid in RANGO_PERIODOS:
        df = descargar_consolidado_periodo(session, pid)
        if df is None or df.empty:
            continue
        etiqueta = _etiqueta_periodo(df)
        if not _periodo_es_del_anio(etiqueta, anio):
            log(f"    ✗ descartado (otro año) — {etiqueta or '¿sin etiqueta?'}")
            continue
        virtual[pid] = df
        log(f"    ✓ incluido — {etiqueta}")

        dm = descargar_matriculados_periodo(session, pid)
        if dm is None:
            log(f"    ADVERTENCIA: sin reporte de matriculados para p{pid} — "
                f"se usarán solo los activos (cohorte subestimada)")
            ids = set(df[COL_ID].map(norm_id)) - {""}
        else:
            ids = set(dm["Identificación"].map(norm_id)) - {""}
        cohortes[pid] = {"etiqueta": etiqueta, "ids": ids, "n": len(ids)}
        log(f"    cohorte p{pid}: {len(ids)} matriculados")

    if not virtual:
        return {}, {}, {}

    dr = descargar_retirados(session)
    retirados: dict[str, str] = {}
    if not dr.empty:
        col_id = next((c for c in dr.columns if "dentificaci" in c), None)
        col_tipo = "Tipo" if "Tipo" in dr.columns else None
        for _, fila in dr.iterrows():
            ced = norm_id(fila[col_id]) if col_id else ""
            if ced:
                retirados[ced] = str(fila[col_tipo]).strip() if col_tipo else ""
    log(f"Retirados histórico: {len(retirados)} cédulas")
    return virtual, cohortes, retirados


# ── Agregación por curso (solo agregados — NUNCA PII) ─────────────────────────
def agregar_por_curso(virtual: dict, cohortes: dict, retirados: dict,
                      ledger: dict) -> tuple[list, dict]:
    """Agrega por asignatura, fusionando periodos que comparten nombre
    (ej. Desarrollo Web en periodos 20 y 24 — cohortes disjuntas).

    Los inhabilitados del periodo se clasifican por curso contra el ledger:
    si su máximo avance registrado alcanzó el umbral → aprobados_retirados
    (aprobó y luego se inhabilitó); si no → retirados (se fue sin aprobar)."""
    cursos: dict[str, dict] = {}
    inhab_sin_retiro_total = 0
    inhabilitados_todos: set[str] = set()
    prog_stats: dict[str, dict] = {}   # programa → cohorte/inhabilitados únicos

    for pid, df in virtual.items():
        info = cohortes[pid]
        ids_activos_periodo = set(df[COL_ID].map(norm_id)) - {""}
        inhabilitados = info["ids"] - ids_activos_periodo
        inhabilitados_todos |= inhabilitados

        # Cohorte única por programa (cada periodo pertenece a un programa)
        programa_pid = (str(df[COL_PROGRAMA].iloc[0]).strip()
                        if COL_PROGRAMA in df.columns and len(df) else "")
        ps = prog_stats.setdefault(programa_pid,
                                   {"ids": set(), "inhab": set(), "activos": set()})
        ps["ids"]     |= info["ids"]
        ps["inhab"]   |= inhabilitados
        ps["activos"] |= ids_activos_periodo
        confirmados = {c for c in inhabilitados if c in retirados}
        sin_retiro = inhabilitados - confirmados
        inhab_sin_retiro_total += len(sin_retiro)
        if sin_retiro:
            log(f"  p{pid}: {len(sin_retiro)} inhabilitados sin retiro identificado "
                f"(posibles archivados al cerrar el curso)")

        df = df.copy()
        df["_av"] = parse_avance(df[COL_AVANCE])
        df["_ced"] = df[COL_ID].map(norm_id)

        for asig, g in df.groupby(COL_CURSO):
            clave = norm_curso(asig)
            g_dedup = g.sort_values("_av", ascending=False).drop_duplicates("_ced")
            activos   = len(g_dedup)
            aprobados = int((g_dedup["_av"] >= UMBRAL_APROBADO).sum())
            promedio  = float(g_dedup["_av"].mean()) if activos else 0.0
            programa  = (str(g[COL_PROGRAMA].iloc[0]).strip()
                         if COL_PROGRAMA in g.columns else "")

            # Clasificar inhabilitados de este periodo contra ESTE curso:
            # ¿su máximo avance registrado en el ledger ya era aprobatorio?
            aprob_ret = sum(
                1 for ced in inhabilitados
                if ledger.get(ced, {}).get(clave, 0.0) >= UMBRAL_APROBADO
            )

            c = cursos.setdefault(clave, {
                "curso": clave, "programa": programa, "periodos": [],
                "activos": 0, "aprobados": 0, "aprobados_retirados": 0,
                "retirados": 0, "cursaron": 0, "_suma_avance": 0.0,
            })
            c["periodos"].append(info["etiqueta"])
            c["activos"]             += activos
            c["aprobados"]           += aprobados
            c["aprobados_retirados"] += aprob_ret
            c["retirados"]           += len(inhabilitados) - aprob_ret
            c["cursaron"]            += activos + len(inhabilitados)
            c["_suma_avance"]        += promedio * activos

    lista = []
    for c in cursos.values():
        promedio = round(c.pop("_suma_avance") / c["activos"], 2) if c["activos"] else 0.0
        aprobados_total = c["aprobados"] + c["aprobados_retirados"]
        no_aprobados = c["cursaron"] - aprobados_total
        lista.append({
            **c,
            "aprobados_total": aprobados_total,
            "no_aprobados":   no_aprobados,
            "sin_finalizar":  c["activos"] - c["aprobados"],
            "promedio":       promedio,
            "pct_aprobados":  round(100 * aprobados_total / c["cursaron"], 1)
                              if c["cursaron"] else 0.0,
            "pct_no_aprobados": round(100 * no_aprobados / c["cursaron"], 1)
                                if c["cursaron"] else 0.0,
            "finalizado":     promedio >= UMBRAL_PROMEDIO_FIN,
        })
    lista.sort(key=lambda c: (c["programa"], -c["cursaron"]))
    anomalias = {
        "inhabilitados_sin_retiro": inhab_sin_retiro_total,
        "retirados_unicos_2026": len(inhabilitados_todos),
    }
    # Conserva los sets crudos por programa (cédulas) para persistir la cohorte
    # 2026 que consume export_retirados.py. Contiene PII → tools/ (gitignoreado).
    prog_stats_raw = {
        prog: {"cohorte": set(v["ids"]), "retirados": set(v["inhab"])}
        for prog, v in prog_stats.items() if prog
    }
    prog_stats = {
        prog: {
            "estudiantes_cohorte": len(v["ids"]),
            "retirados_unicos":    len(v["inhab"]),
            "habilitados_unicos":  len(v["activos"]),
        }
        for prog, v in prog_stats.items()
    }
    return lista, anomalias, prog_stats, prog_stats_raw


# ── Marca de agua (aprobados_total nunca decae) ───────────────────────────────
def aplicar_maximos(lista: list) -> None:
    """Red de seguridad para aprobados que el ledger no alcanzó a ver antes de
    que Q10 los inhabilitara (o que desaparecen de la cohorte): el total de
    aprobados por curso nunca decae. Si el conteo vivo baja respecto al máximo
    histórico, el déficit se reclasifica de 'retirados' a 'aprobados_retirados'
    (por definición son inhabilitados que alguna vez contaron como aprobados)."""
    maximos = {}
    if os.path.isfile(RUTA_MAXIMOS):
        try:
            with open(RUTA_MAXIMOS, encoding="utf-8") as f:
                maximos = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: maximos.json ilegible ({e}) — se regenera")

    for c in lista:
        # Clave "aprobados" del maximos.json histórico = piso del total aprobado
        m = maximos.setdefault(c["curso"], {"aprobados": 0, "cursaron": 0})
        m["aprobados"] = max(m["aprobados"], c["aprobados_total"])
        m["cursaron"]  = max(m["cursaron"], c["cursaron"])

        deficit = m["aprobados"] - c["aprobados_total"]
        if deficit > 0:
            traslado = min(deficit, c["retirados"])
            log(f"  marca de agua: {c['curso'][:40]!r} total aprobado "
                f"{c['aprobados_total']} < máximo {m['aprobados']} — "
                f"{traslado} reclasificados como aprobados_retirados")
            c["aprobados_retirados"] += traslado
            c["retirados"]           -= traslado
            c["aprobados_total"]     += traslado

        # Si el máximo de cursaron supera el vivo (Q10 anuló matrículas del reporte
        # de matriculados), el delta se cuenta como retirado para conservar la
        # identidad cursaron == aprobados + aprobados_retirados + sin_finalizar + retirados
        deficit_cursaron = m["cursaron"] - c["cursaron"]
        if deficit_cursaron > 0:
            log(f"  marca de agua: {c['curso'][:40]!r} cursaron {c['cursaron']} "
                f"< máximo {m['cursaron']} — {deficit_cursaron} anulados → retirados")
            c["retirados"] += deficit_cursaron
            c["cursaron"]   = m["cursaron"]
        c["no_aprobados"]     = c["cursaron"] - c["aprobados_total"]
        c["pct_aprobados"]    = round(100 * c["aprobados_total"] / c["cursaron"], 1) \
            if c["cursaron"] else 0.0
        c["pct_no_aprobados"] = round(100 * c["no_aprobados"] / c["cursaron"], 1) \
            if c["cursaron"] else 0.0

    os.makedirs(os.path.dirname(RUTA_MAXIMOS), exist_ok=True)
    with open(RUTA_MAXIMOS, "w", encoding="utf-8") as f:
        json.dump(maximos, f, ensure_ascii=False, indent=2)
    log(f"  maximos.json actualizado ({len(maximos)} cursos)")


# ── JSON final ────────────────────────────────────────────────────────────────
def generar_json(anio: str, lista: list, cohortes: dict, anomalias: dict,
                 prog_stats: dict) -> dict:
    programas: dict[str, dict] = {}
    for c in lista:
        p = programas.setdefault(c["programa"] or "Sin programa", {
            "cursos": 0, "cursaron": 0, "aprobados": 0,
            "aprobados_retirados": 0, "retirados": 0,
        })
        p["cursos"]              += 1
        p["cursaron"]            += c["cursaron"]
        p["aprobados"]           += c["aprobados_total"]
        p["aprobados_retirados"] += c["aprobados_retirados"]
        p["retirados"]           += c["retirados"]
        p["sin_finalizar"]        = p.get("sin_finalizar", 0) + c["sin_finalizar"]
        p["matriculas_activas"]   = p.get("matriculas_activas", 0) + c["activos"]
    for nombre, p in programas.items():
        p["pct_aprobados"] = round(100 * p["aprobados"] / p["cursaron"], 1) \
            if p["cursaron"] else 0.0
        # Estudiantes/retirados únicos del programa (para KPIs por programa)
        p.update(prog_stats.get(nombre, {}))

    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "anio": anio,
        "nota_metodo": (
            "Cohorte = matriculados del periodo (habilitados + inhabilitados). "
            "Aprobado = avance >= 100. Un inhabilitado que ya había alcanzado el "
            "100 cuenta como 'aprobó y se retiró' (no pierde su logro); solo los "
            "retirados sin aprobar cuentan como no aprobados."
        ),
        "por_curso": lista,
        "por_programa": [
            {"programa": nombre, **valores}
            for nombre, valores in sorted(programas.items())
        ],
        "totales": {
            "total_cursos":       len(lista),
            "total_matriculas":   sum(c["cursaron"] for c in lista),
            "total_aprobados":    sum(c["aprobados_total"] for c in lista),
            "total_aprobados_retirados": sum(c["aprobados_retirados"] for c in lista),
            "total_retirados_2026": anomalias.get("retirados_unicos_2026", 0),
            "estudiantes_cohorte_2026": len(
                set().union(*(info["ids"] for info in cohortes.values()))
            ) if cohortes else 0,
        },
        "anomalias": anomalias,
        "periodos": [
            {"periodo": info["etiqueta"], "matriculados": info["n"]}
            for info in cohortes.values()
        ],
    }


def guardar_json(datos: dict) -> None:
    os.makedirs(os.path.dirname(RUTA_DATA_JSON), exist_ok=True)
    with open(RUTA_DATA_JSON, "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2)
    log(f"  data.json generado en: {RUTA_DATA_JSON}")


# ── Git commit y push ─────────────────────────────────────────────────────────
def git_commit_y_push(timestamp: str) -> None:
    pasos = [
        ["git", "add",
         os.path.join("docs", "aprobacion", "data.json"),
         os.path.join("docs", "aprobacion", "maximos.json")],
        ["git", "commit", "-m", f"chore: actualizar aprobacion por curso [{timestamp}]"],
        ["git", "push", "origin", "main"],
    ]
    for cmd in pasos:
        resultado = subprocess.run(cmd, cwd=PROYECTO_ROOT, capture_output=True,
                                   text=True, encoding="utf-8")
        if resultado.returncode != 0:
            stderr = resultado.stderr.strip() or resultado.stdout.strip()
            log(f"ADVERTENCIA git ({' '.join(cmd[:2])}): {stderr}")
            return
        log(f"  git {cmd[1]}: OK")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    parser = argparse.ArgumentParser(
        description="Genera docs/aprobacion/data.json con %% de aprobación por curso"
    )
    parser.add_argument("--anio", default=AÑO_OBJETIVO,
                        help=f"Año de los periodos (default: {AÑO_OBJETIVO})")
    parser.add_argument("--sin-push", action="store_true",
                        help="Genera el JSON sin git commit/push (pruebas)")
    args = parser.parse_args()

    try:
        session = login_q10()
        ledger = cargar_ledger()
        virtual, cohortes, retirados = descargar_fuentes(session, args.anio)
        if not virtual:
            log(f"ERROR: ningún periodo del año {args.anio} devolvió datos.")
            sys.exit(1)

        aplicar_exclusiones(virtual, cohortes, retirados, ledger,
                            cargar_exclusiones())
        actualizar_ledger(ledger, virtual)
        guardar_ledger(ledger)

        lista, anomalias, prog_stats, prog_stats_raw = agregar_por_curso(
            virtual, cohortes, retirados, ledger)
        guardar_cohorte(prog_stats_raw, args.anio)
        aplicar_maximos(lista)
        datos = generar_json(args.anio, lista, cohortes, anomalias, prog_stats)
        guardar_json(datos)

        if args.sin_push:
            log("Modo --sin-push: no se toca git.")
        else:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
            log("Ejecutando git commit y push...")
            git_commit_y_push(timestamp)

        t = datos["totales"]
        log("=" * 60)
        for c in lista:
            log(f"  {c['curso'][:44]:<44} cursaron={c['cursaron']:>4} "
                f"aprobados={c['aprobados_total']:>4} "
                f"(act {c['aprobados']} + ret {c['aprobados_retirados']}) "
                f"({c['pct_aprobados']}%)"
                f"{' [FINALIZADO]' if c['finalizado'] else ''}")
        log("=" * 60)
        print(f"EXPORT: cursos={t['total_cursos']} "
              f"matriculas={t['total_matriculas']} "
              f"aprobados={t['total_aprobados']} estado=exito", flush=True)

    except SystemExit:
        raise
    except Exception as e:
        import traceback
        print(f"\nERROR inesperado: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
