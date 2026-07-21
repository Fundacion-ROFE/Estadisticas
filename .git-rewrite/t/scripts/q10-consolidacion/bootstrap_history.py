# -*- coding: utf-8 -*-
"""
bootstrap_history.py — Ejecución ÚNICA.

Lee el historial de git de docs/dashboard/data.json y genera
docs/dashboard/history.json con un snapshot por período de ~4 días.

Toma el commit MÁS RECIENTE dentro de cada período (datos más frescos).

Uso:
    cd scripts/q10-consolidacion
    python bootstrap_history.py
"""

import json
import os
import subprocess
import sys
from datetime import datetime

DIRECTORIO_SCRIPT      = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT          = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_GIT_DATA          = "docs/dashboard/data.json"   # ruta relativa al repo (barras normales)
RUTA_HISTORY_JSON      = os.path.join(PROYECTO_ROOT, "docs", "dashboard", "history.json")
INTERVALO_DIAS         = 4


def git(cmd: list) -> str:
    r = subprocess.run(cmd, cwd=PROYECTO_ROOT, capture_output=True, text=True, encoding="utf-8")
    return r.stdout.strip()


def log(msg: str) -> None:
    print(f"[bootstrap-history] {msg}", flush=True)


def _snapshot_from_data(datos: dict, fecha: str) -> dict:
    def resumir(por_curso: list, total_unicos: int) -> dict:
        cursos = [
            {"curso": c["curso"], "promedio": c["promedio"], "estudiantes": c["estudiantes"]}
            for c in por_curso
        ]
        total_est = sum(c["estudiantes"] for c in cursos)
        prom_global = (
            round(sum(c["promedio"] * c["estudiantes"] for c in cursos) / total_est, 2)
            if total_est else 0.0
        )
        return {"total_estudiantes_unicos": total_unicos, "promedio_global": prom_global, "por_curso": cursos}

    jc = resumir(datos.get("por_curso", []),
                 datos.get("totales", {}).get("total_estudiantes_unicos", 0))
    mr = resumir(datos.get("mr", {}).get("por_curso", []),
                 datos.get("mr", {}).get("totales", {}).get("total_estudiantes_unicos", 0))
    return {"fecha": fecha, "jc": jc, "mr": mr}


def main() -> None:
    if os.path.isfile(RUTA_HISTORY_JSON):
        resp = input(f"Ya existe {RUTA_HISTORY_JSON}. ¿Sobreescribir? [s/N] ").strip().lower()
        if resp != "s":
            log("Cancelado.")
            return

    # 1. Obtener commits que tocaron data.json (más reciente primero)
    log_raw = git(["git", "log", "--pretty=format:%H %ai", "--", RUTA_GIT_DATA])
    if not log_raw:
        log("ERROR: No se encontraron commits con data.json.")
        sys.exit(1)

    commits = []  # [(date, hash_str)]
    for linea in log_raw.splitlines():
        partes = linea.split()
        if len(partes) < 2:
            continue
        hash_   = partes[0]
        fecha_s = partes[1]            # "2026-06-24"
        try:
            fecha = datetime.strptime(fecha_s, "%Y-%m-%d").date()
            commits.append((fecha, hash_))
        except ValueError:
            continue

    # Ordenar cronológicamente (más antiguo primero)
    commits.sort(key=lambda x: x[0])
    log(f"Commits encontrados: {len(commits)} ({commits[0][0]} → {commits[-1][0]})")

    # 2. Agrupar por períodos de INTERVALO_DIAS — conservar el más reciente por período
    periodos: list = []           # [(fecha, hash)] — un elemento por período
    inicio_periodo = None

    for fecha, hash_ in commits:
        if inicio_periodo is None:
            inicio_periodo = fecha
            periodos.append((fecha, hash_))
        else:
            delta = (fecha - inicio_periodo).days
            if delta >= INTERVALO_DIAS:
                inicio_periodo = fecha
                periodos.append((fecha, hash_))
            else:
                # Mismo período — reemplazar con el más reciente (datos frescos)
                periodos[-1] = (fecha, hash_)

    log(f"Períodos identificados: {len(periodos)}")

    # 3. Extraer data.json de cada commit seleccionado
    history = []
    for fecha, hash_ in periodos:
        contenido = git(["git", "show", f"{hash_}:{RUTA_GIT_DATA}"])
        if not contenido:
            log(f"  ⚠ {hash_[:7]} ({fecha}) — contenido vacío, saltando")
            continue
        try:
            datos = json.loads(contenido)
        except json.JSONDecodeError as e:
            log(f"  ⚠ {hash_[:7]} ({fecha}) — JSON inválido ({e}), saltando")
            continue

        entrada = _snapshot_from_data(datos, fecha.isoformat())
        history.append(entrada)
        log(f"  ✓ {fecha}  {hash_[:7]}  — JC prom: {entrada['jc']['promedio_global']}%  MR prom: {entrada['mr']['promedio_global']}%")

    if not history:
        log("No se generaron entradas. Verifica el historial de git.")
        sys.exit(1)

    # 4. Guardar
    os.makedirs(os.path.dirname(RUTA_HISTORY_JSON), exist_ok=True)
    with open(RUTA_HISTORY_JSON, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)

    log(f"\nGuardado: {RUTA_HISTORY_JSON}")
    log(f"Entradas: {len(history)}")
    log("Próximos pasos:")
    log("  1. Revisa el archivo generado")
    log("  2. git add docs/dashboard/history.json && git commit -m 'chore: inicializar historial' && git push")


if __name__ == "__main__":
    main()
