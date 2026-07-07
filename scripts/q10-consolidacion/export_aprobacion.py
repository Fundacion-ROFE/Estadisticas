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
retirados → inhabilitado = retirado = no aprobó.

El JSON público solo lleva agregados (NUNCA PII). Marca de agua en
docs/aprobacion/maximos.json: `aprobados` nunca decae (si Q10 archiva a un estudiante
que ya iba en 100%, el conteo vivo bajaría — se congela el máximo).

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
def agregar_por_curso(virtual: dict, cohortes: dict, retirados: dict) -> tuple[list, dict]:
    """Agrega por asignatura, fusionando periodos que comparten nombre
    (ej. Desarrollo Web en periodos 20 y 24 — cohortes disjuntas)."""
    cursos: dict[str, dict] = {}
    inhab_sin_retiro_total = 0
    inhabilitados_todos: set[str] = set()

    for pid, df in virtual.items():
        info = cohortes[pid]
        ids_activos_periodo = set(df[COL_ID].map(norm_id)) - {""}
        inhabilitados = info["ids"] - ids_activos_periodo
        inhabilitados_todos |= inhabilitados
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

            c = cursos.setdefault(clave, {
                "curso": clave, "programa": programa, "periodos": [],
                "activos": 0, "aprobados": 0, "retirados": 0,
                "cursaron": 0, "_suma_avance": 0.0,
            })
            c["periodos"].append(info["etiqueta"])
            c["activos"]      += activos
            c["aprobados"]    += aprobados
            c["retirados"]    += len(inhabilitados)
            c["cursaron"]     += activos + len(inhabilitados)
            c["_suma_avance"] += promedio * activos

    lista = []
    for c in cursos.values():
        promedio = round(c.pop("_suma_avance") / c["activos"], 2) if c["activos"] else 0.0
        no_aprobados = c["cursaron"] - c["aprobados"]
        lista.append({
            **c,
            "no_aprobados":   no_aprobados,
            "sin_finalizar":  c["activos"] - c["aprobados"],
            "promedio":       promedio,
            "pct_aprobados":  round(100 * c["aprobados"] / c["cursaron"], 1)
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
    return lista, anomalias


# ── Marca de agua (aprobados nunca decae) ─────────────────────────────────────
def aplicar_maximos(lista: list) -> None:
    """Si Q10 archiva a un estudiante que iba en 100%, el conteo vivo de aprobados
    baja. Se congela el máximo histórico por curso (mismo patrón que
    maximos_cursos.json del dashboard)."""
    maximos = {}
    if os.path.isfile(RUTA_MAXIMOS):
        try:
            with open(RUTA_MAXIMOS, encoding="utf-8") as f:
                maximos = json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            log(f"ADVERTENCIA: maximos.json ilegible ({e}) — se regenera")

    for c in lista:
        m = maximos.setdefault(c["curso"], {"aprobados": 0, "cursaron": 0})
        m["aprobados"] = max(m["aprobados"], c["aprobados"])
        m["cursaron"]  = max(m["cursaron"], c["cursaron"])
        if c["aprobados"] < m["aprobados"]:
            log(f"  marca de agua: {c['curso'][:40]!r} aprobados {c['aprobados']} "
                f"→ {m['aprobados']} (congelado)")
        c["aprobados"] = m["aprobados"]
        c["cursaron"]  = max(c["cursaron"], m["cursaron"])
        c["no_aprobados"]     = c["cursaron"] - c["aprobados"]
        c["pct_aprobados"]    = round(100 * c["aprobados"] / c["cursaron"], 1) \
            if c["cursaron"] else 0.0
        c["pct_no_aprobados"] = round(100 * c["no_aprobados"] / c["cursaron"], 1) \
            if c["cursaron"] else 0.0

    os.makedirs(os.path.dirname(RUTA_MAXIMOS), exist_ok=True)
    with open(RUTA_MAXIMOS, "w", encoding="utf-8") as f:
        json.dump(maximos, f, ensure_ascii=False, indent=2)
    log(f"  maximos.json actualizado ({len(maximos)} cursos)")


# ── JSON final ────────────────────────────────────────────────────────────────
def generar_json(anio: str, lista: list, cohortes: dict, anomalias: dict) -> dict:
    programas: dict[str, dict] = {}
    for c in lista:
        p = programas.setdefault(c["programa"] or "Sin programa", {
            "cursos": 0, "cursaron": 0, "aprobados": 0, "retirados": 0,
        })
        p["cursos"]    += 1
        p["cursaron"]  += c["cursaron"]
        p["aprobados"] += c["aprobados"]
        p["retirados"] += c["retirados"]
    for p in programas.values():
        p["pct_aprobados"] = round(100 * p["aprobados"] / p["cursaron"], 1) \
            if p["cursaron"] else 0.0

    return {
        "ultima_actualizacion": datetime.now().astimezone().isoformat(),
        "anio": anio,
        "nota_metodo": (
            "Cohorte = matriculados del periodo (habilitados + inhabilitados). "
            "Aprobado = avance >= 100. Los retirados cuentan como no aprobados."
        ),
        "por_curso": lista,
        "por_programa": [
            {"programa": nombre, **valores}
            for nombre, valores in sorted(programas.items())
        ],
        "totales": {
            "total_cursos":       len(lista),
            "total_matriculas":   sum(c["cursaron"] for c in lista),
            "total_aprobados":    sum(c["aprobados"] for c in lista),
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
        virtual, cohortes, retirados = descargar_fuentes(session, args.anio)
        if not virtual:
            log(f"ERROR: ningún periodo del año {args.anio} devolvió datos.")
            sys.exit(1)

        lista, anomalias = agregar_por_curso(virtual, cohortes, retirados)
        aplicar_maximos(lista)
        datos = generar_json(args.anio, lista, cohortes, anomalias)
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
            log(f"  {c['curso'][:48]:<48} cursaron={c['cursaron']:>4} "
                f"aprobados={c['aprobados']:>4} ({c['pct_aprobados']}%)"
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
