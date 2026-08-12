# -*- coding: utf-8 -*-
"""
cargar_plataforma_mr_completa.py — "BD-Mujeres ROFÉ 2026 - Plataforma MR.csv" (export
completo de la plataforma, 5.158 filas, años 2022-2026) → historial completo en Supabase.

Pedido del usuario (2026-08-12): llenar el historial de TODAS las mujeres de esta fuente.
- Con participant_id (ya tienen Q10/matrícula real): se backfillea `participants` (estado_
  civil/nivel_estudio/tipo_vivienda/estrato/edad, SOLO si están NULL — nunca sobreescribe) +
  se cargan los campos que `participants` no tiene a `enriquecimiento_mr_extendido` (mismo
  vocabulario del cluster F: direccion/presentacion_personal/personas_nucleo/ingresos_
  familiares/canal_adquisicion/grupo_etnico/sostenimiento).
- Sin participant_id (candidatas que nunca matricularon): se agregan/actualizan en
  `postulantes_mr` — universo completo de candidatas, con las mismas 7 columnas ricas
  (migración 046) + fecha_creacion. Backfill SOLO donde está NULL, igual criterio.
- Lo que la fuente no trae para una persona queda NULL — nunca se inventa un valor
  (pedido explícito: "pon en null los valores que no posean").

Reusa los mapas MAPA_NIVEL/MAPA_CIVIL/MAPA_VIVIENDA de sync_postulantes_mr.py — mismos
enums en participants Y postulantes_mr (verificado 2026-08-12), cero riesgo de inconsistencia.

Modo por defecto: SOLO REPORTE (contraste, no escribe). Pasar --aplicar para cargar.

Uso:
    python cargar_plataforma_mr_completa.py             # reporte/contraste
    python cargar_plataforma_mr_completa.py --aplicar    # carga todo el historial
"""

import argparse
import io
import os
import re
import sys
from collections import Counter
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
RUTA_CSV = r"C:\Users\EstudiantesJC\Downloads\BD-Mujeres ROFÉ 2026 - Plataforma MR.csv"
FUENTE_ARCHIVO = "BD-Mujeres ROFÉ 2026 - Plataforma MR.csv"

sys.path.insert(0, DIRECTORIO_SCRIPT)
from enriquecimiento_helper import cargar_hoja  # noqa: E402
from cargar_supabase import Supa, cargar_env_local  # noqa: E402 — Supa.upsert() (batch + merge-duplicates)
from sync_postulantes_mr import (  # noqa: E402 — reusar mapas/normalizadores tal cual
    MAPA_CIVIL, MAPA_NIVEL, MAPA_VIVIENDA, mapear, norm_celular, norm_id, texto,
)

USER_AGENT = "panel-datos-etl/1.0"
LOTE = 500
FUENTE_NUEVA = "plataforma_mr_completa"
SIN_FECHA = {"", "n/a", "#n/a", "null", "na"}
SIN_DATO = {"", "n/a", "#n/a", "null", "na", "-", "0"}

# Campos ricos (mismo vocabulario que enriquecimiento_mr_extendido, cluster F 2026-08-12):
# nombre_campo → columna del CSV
CAMPOS_RICOS = {
    "direccion": "address",
    "presentacion_personal": "description",
    "personas_nucleo": "familyCore",
    "ingresos_familiares": "familyIncome",
    "canal_adquisicion": "disclosure",
    "grupo_etnico": "ethnicGroup[0].name",
    "sostenimiento": "sustaining[0].name",
}


def log(msg: str) -> None:
    print(f"[plataforma-mr-completa] {msg}", flush=True)


def _limpio(v):
    s = texto(v)
    return s if s.lower() not in SIN_DATO else ""


def leer_csv():
    _cols, filas = cargar_hoja(RUTA_CSV)
    limpias, sin_cedula, vistos = [], 0, set()
    for f in filas:
        ced = norm_id(f.get("documentNumber"))
        if not ced:
            sin_cedula += 1
            continue
        if ced in vistos:
            continue  # primera aparición gana
        vistos.add(ced)
        nombre = " ".join(p for p in ((f.get("firstName") or "").strip(),
                                       (f.get("lastName") or "").strip()) if p) or None
        fila = {
            "cedula": ced,
            "anio": texto(f.get("Año")) or None,
            "nombre": nombre,
            "email": texto(f.get("email")).lower() or None,
            "celular": norm_celular(f.get("phoneNumber")) or None,
            "ciudad": texto(f.get("location.cityName")) or None,
            "edad": (lambda v: str(int(v)) if str(v).strip().isdigit() and 14 <= int(v) <= 99 else None)
                    (f.get("age")),
            "nivel_estudio": mapear(f.get("education"), MAPA_NIVEL),
            "estado_civil": mapear(f.get("maritalStatus"), MAPA_CIVIL),
            "tipo_vivienda": mapear(f.get("housingType"), MAPA_VIVIENDA),
            "estrato": (lambda v: str(int(v)) if str(v).strip().isdigit() and 1 <= int(v) <= 6 else None)
                       (f.get("stratum")),
        }
        for campo, col in CAMPOS_RICOS.items():
            fila[campo] = _limpio(f.get(col)) or None
        limpias.append(fila)
    log(f"CSV: {len(filas)} filas → {len(limpias)} limpias (sin_cedula={sin_cedula})")
    return limpias


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--aplicar", action="store_true", help="ejecuta las escrituras (default: solo reporte)")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan credenciales Supabase")
        return 1
    if not os.path.isfile(RUTA_CSV):
        log(f"ERROR: no existe el CSV: {RUTA_CSV}")
        return 1

    filas = leer_csv()
    log(f"Por año: {dict(sorted(Counter(f['anio'] for f in filas).items()))}")

    supa = Supa(url, key)
    log("Descargando postulantes_mr existentes...")
    cols_pm = ("cedula,fecha_creacion,fuente_pestana,direccion,presentacion_personal,"
               "personas_nucleo,ingresos_familiares,canal_adquisicion,grupo_etnico,sostenimiento")
    existentes_pm = {p["cedula"]: p for p in supa.get_todo(f"/postulantes_mr?select={cols_pm}")}
    log(f"postulantes_mr hoy: {len(existentes_pm)} filas")

    log("Descargando participants (para enlazar + backfill de sociodemografía)...")
    cols_p = "id,q10_id,estado_civil,nivel_estudio,tipo_vivienda,estrato,edad"
    participantes = {p["q10_id"]: p for p in supa.get_todo(f"/participants?select={cols_p}") if p.get("q10_id")}

    con_participante = [f for f in filas if f["cedula"] in participantes]
    sin_participante = [f for f in filas if f["cedula"] not in participantes]
    nuevas_pm = [f for f in filas if f["cedula"] not in existentes_pm]
    log(f"CONTRASTE: {len(filas)} personas · {len(con_participante)} CON participant_id "
        f"(reciben enriquecimiento_mr_extendido + backfill de participants) · "
        f"{len(sin_participante)} sin participant_id (solo postulantes_mr) · "
        f"{len(nuevas_pm)} nuevas en postulantes_mr")

    if not args.aplicar:
        log("Modo reporte (sin --aplicar): no se escribió nada en Supabase.")
        return 0

    # ── 1) postulantes_mr: TODAS, backfill solo-si-vacío (universo completo) ───────────
    payload_pm = []
    for f in filas:
        existente = existentes_pm.get(f["cedula"])
        fila = {"cedula": f["cedula"],
                "fuente_pestana": (existente.get("fuente_pestana") if existente else None) or FUENTE_NUEVA,
                "updated_at": datetime.now().isoformat(timespec="seconds")}
        if existente is None:  # nueva: fila completa
            fila["genero"] = "Femenino"
            for campo in ("nombre", "email", "celular", "ciudad", "edad", "nivel_estudio",
                          "estado_civil", "tipo_vivienda", "estrato"):
                if f.get(campo) is not None:
                    fila[campo] = f[campo]
            if f["anio"]:
                fila["fecha_creacion"] = f["anio"]
            for campo in CAMPOS_RICOS:
                if f.get(campo) is not None:
                    fila[campo] = f[campo]
        else:  # ya existía: SOLO completar lo que está vacío
            if (existente.get("fecha_creacion") or "").strip().lower() in SIN_FECHA and f["anio"]:
                fila["fecha_creacion"] = f["anio"]
            for campo in CAMPOS_RICOS:
                if not (existente.get(campo) or "").strip() and f.get(campo):
                    fila[campo] = f[campo]
        payload_pm.append(fila)

    grupos: dict[frozenset, list] = {}
    for fila in payload_pm:
        grupos.setdefault(frozenset(fila), []).append(fila)
    enviadas_pm = fallos_pm = 0
    for claves, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            lote = grupo[i:i + LOTE]
            try:
                supa._req("POST", "/postulantes_mr?on_conflict=cedula", lote,
                          prefer="resolution=merge-duplicates,return=minimal")
                enviadas_pm += len(lote)
            except RuntimeError as e:
                fallos_pm += 1
                log(f"ERROR postulantes_mr lote de {len(lote)} (claves={sorted(claves)}): {e}")
    log(f"postulantes_mr: {enviadas_pm} filas enviadas en {len(grupos)} grupos, "
        f"{fallos_pm} lotes fallidos")

    # ── 2) participants: backfill SOLO si NULL (nunca sobreescribe un valor real) ──────
    actualizados_p = fallos_p = 0
    for f in con_participante:
        p = participantes[f["cedula"]]
        cambios = {}
        for campo in ("estado_civil", "nivel_estudio", "tipo_vivienda", "estrato", "edad"):
            if p.get(campo) is None and f.get(campo):
                cambios[campo] = f[campo]
        if not cambios:
            continue
        try:
            supa._req("PATCH", f"/participants?id=eq.{p['id']}", cambios)
            actualizados_p += 1
        except RuntimeError as e:
            fallos_p += 1
            log(f"ERROR participants cedula={f['cedula']}: {e}")
    log(f"participants: {actualizados_p} backfilleados, {fallos_p} fallos")

    # ── 3) enriquecimiento_mr_extendido: campos que participants no tiene ──────────────
    payload_enr = []
    for f in con_participante:
        pid = participantes[f["cedula"]]["id"]
        for campo in CAMPOS_RICOS:
            valor = f.get(campo)
            if valor:
                payload_enr.append({"participant_id": pid, "campo": campo, "valor": valor[:2000],
                                    "fuente_archivo": FUENTE_ARCHIVO, "metodo_match": "cedula"})
    enviadas_enr = supa.upsert("enriquecimiento_mr_extendido", payload_enr,
                               "participant_id,campo,fuente_archivo,valor") if payload_enr else 0
    log(f"enriquecimiento_mr_extendido: {enviadas_enr} filas enviadas")

    log(f"RESUMEN --aplicar: postulantes_mr={enviadas_pm} participants_backfill={actualizados_p} "
        f"enriquecimiento={enviadas_enr} fallos_pm={fallos_pm} fallos_p={fallos_p} · "
        f"estado={'exito' if fallos_pm == 0 and fallos_p == 0 else 'con_errores'}")
    return 0 if fallos_pm == 0 and fallos_p == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
