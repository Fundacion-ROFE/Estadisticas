# -*- coding: utf-8 -*-
"""
cargar_plataforma_mr_completa.py — "BD-Mujeres ROFÉ 2026 - Plataforma MR.csv" (export
completo de la plataforma, 5.158 filas, años 2022-2026) → contraste + carga en
Supabase `postulantes_mr`.

Contexto (2026-08-12): cerraba la limitante documentada en
docs/procesos/plan-enriquecimiento-final-2026-08-12.md ("MR no viene seccionada por año
de origen") — la pestaña "Plataforma MR" del Sheet que ya sincroniza sync_postulantes_mr.py
solo tiene 49 cédulas (snapshot viejo/truncado); este CSV es el export real y completo de
la plataforma, con año de registro casi 100% confiable (columna "Año").

Estrategia NO DESTRUCTIVA (mismo patrón de agrupar por conjunto-de-claves que ya usa
sync_postulantes_mr.py, para que un upsert en lote nunca ponga en NULL una columna que
una fila del mismo lote no trae):
  - Cédulas YA en `postulantes_mr`: SOLO se backfillea `fecha_creacion` si hoy está vacía/
    "N/A" — nunca se sobreescribe un valor ya cargado por otra fuente (General/Inactivas).
    Nada más se toca (nombre/ciudad/etc de esas filas se dejan como están).
  - Cédulas NUEVAS: se insertan completas (nombre, email, celular, ciudad, fecha_creacion=
    año, sociodemografía mapeada a los mismos enums que sync_postulantes_mr.py, genero=
    "Femenino" constante, fuente_pestana="plataforma_mr_completa" para distinguirlas de la
    pestaña vieja truncada).

Reusa los mapas MAPA_NIVEL/MAPA_CIVIL/MAPA_VIVIENDA de sync_postulantes_mr.py — mismos
enums, mismo criterio de substring, cero riesgo de inconsistencia con lo ya cargado.

Modo por defecto: SOLO REPORTE (contraste, no escribe). Pasar --aplicar para cargar.

Uso:
    python cargar_plataforma_mr_completa.py             # reporte/contraste
    python cargar_plataforma_mr_completa.py --aplicar    # inserta nuevas + backfillea fecha_creacion
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

sys.path.insert(0, DIRECTORIO_SCRIPT)
from enriquecimiento_helper import cargar_hoja  # noqa: E402
from sync_postulantes_mr import (  # noqa: E402 — reusar mapas/normalizadores tal cual
    MAPA_CIVIL, MAPA_NIVEL, MAPA_VIVIENDA, Supa, cargar_env_local, mapear, norm_celular,
    norm_id, texto,
)

USER_AGENT = "panel-datos-etl/1.0"
LOTE = 500
FUENTE_NUEVA = "plataforma_mr_completa"
SIN_FECHA = {"", "n/a", "#n/a", "null", "na"}


def log(msg: str) -> None:
    print(f"[plataforma-mr-completa] {msg}", flush=True)


def leer_csv():
    _cols, filas = cargar_hoja(RUTA_CSV)
    limpias, sin_cedula, vistos = [], 0, set()
    for f in filas:
        ced = norm_id(f.get("documentNumber"))
        if not ced:
            sin_cedula += 1
            continue
        if ced in vistos:
            continue  # primera aparición gana (mismo criterio que sync_postulantes_mr.py)
        vistos.add(ced)
        nombre = " ".join(p for p in ((f.get("firstName") or "").strip(),
                                       (f.get("lastName") or "").strip()) if p) or None
        limpias.append({
            "cedula": ced,
            "anio": texto(f.get("Año")) or None,
            "nombre": nombre,
            "email": texto(f.get("email")).lower() or None,
            "celular": norm_celular(f.get("phoneNumber")) or None,
            "ciudad": texto(f.get("location.cityName")) or None,
            "edad": (lambda v: int(v) if str(v).strip().isdigit() and 14 <= int(v) <= 90 else None)
                    (f.get("age")),
            "nivel_estudio": mapear(f.get("education"), MAPA_NIVEL),
            "estado_civil": mapear(f.get("maritalStatus"), MAPA_CIVIL),
            "tipo_vivienda": mapear(f.get("housingType"), MAPA_VIVIENDA),
            "estrato": (lambda v: int(v) if str(v).strip().isdigit() and 1 <= int(v) <= 6 else None)
                       (f.get("stratum")),
        })
    log(f"CSV: {len(filas)} filas → {len(limpias)} limpias (sin_cedula={sin_cedula}, "
        f"duplicadas={len(filas) - sin_cedula - len(limpias)})")
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
    log("Descargando postulantes_mr existentes (cedula, fecha_creacion, fuente_pestana)...")
    existentes = supa.get_todo("/postulantes_mr?select=cedula,fecha_creacion,fuente_pestana")
    fecha_por_cedula = {p["cedula"]: p.get("fecha_creacion") for p in existentes}
    # GOTCHA (encontrado 2026-08-12): `INSERT ... ON CONFLICT DO UPDATE` valida las columnas
    # NOT NULL de la fila candidata del INSERT ANTES de decidir si actualiza — aunque la fila
    # ya exista y el UPDATE nunca fuera a tocar esa columna. `fuente_pestana` es NOT NULL sin
    # default, así que un backfill que solo manda {cedula, fecha_creacion} revienta. Fix: se
    # manda de vuelta su valor actual (sin cambiarlo) para satisfacer la constraint.
    fuente_por_cedula = {p["cedula"]: p.get("fuente_pestana") for p in existentes}
    log(f"postulantes_mr hoy: {len(existentes)} filas")

    nuevas = [f for f in filas if f["cedula"] not in fecha_por_cedula]
    ya_existian = [f for f in filas if f["cedula"] in fecha_por_cedula]
    backfill = [f for f in ya_existian
                if (fecha_por_cedula.get(f["cedula"]) or "").strip().lower() in SIN_FECHA
                and f["anio"]]

    log(f"CONTRASTE: {len(filas)} personas en el CSV · {len(nuevas)} NUEVAS (no están en "
        f"postulantes_mr) · {len(ya_existian)} ya existían · de esas, {len(backfill)} sin "
        f"fecha_creacion útil hoy (se les puede completar el año)")

    if not args.aplicar:
        log("Modo reporte (sin --aplicar): no se escribió nada en Supabase.")
        return 0

    log("Descargando participants (para enlazar participant_id si ya matricularon)...")
    participantes = supa.get_todo("/participants?select=id,q10_id")
    q10_a_participant = {p["q10_id"]: p["id"] for p in participantes if p.get("q10_id")}

    payload = []
    for f in nuevas:
        fila = {"cedula": f["cedula"], "genero": "Femenino", "fuente_pestana": FUENTE_NUEVA,
                "updated_at": datetime.now().isoformat(timespec="seconds")}
        for campo in ("nombre", "email", "celular", "ciudad", "edad", "nivel_estudio",
                      "estado_civil", "tipo_vivienda", "estrato"):
            if f.get(campo) is not None:
                fila[campo] = f[campo]
        if f["anio"]:
            fila["fecha_creacion"] = f["anio"]
        pid = q10_a_participant.get(f["cedula"])
        if pid:
            fila["participant_id"] = pid
        payload.append(fila)
    for f in backfill:
        payload.append({
            "cedula": f["cedula"], "fecha_creacion": f["anio"],
            "fuente_pestana": fuente_por_cedula.get(f["cedula"]) or FUENTE_NUEVA,
            "updated_at": datetime.now().isoformat(timespec="seconds"),
        })

    # Agrupar por conjunto-de-claves EXACTO antes de subir en lote — si no, PostgREST usa la
    # unión de columnas del lote y pone NULL en las filas que no traían esa clave (mismo
    # gotcha ya resuelto en sync_postulantes_mr.py:main()).
    grupos: dict[frozenset, list] = {}
    for fila in payload:
        grupos.setdefault(frozenset(fila), []).append(fila)

    total_enviadas = fallos_lotes = 0
    for claves, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            lote = grupo[i:i + LOTE]
            try:
                supa._req("POST", "/postulantes_mr?on_conflict=cedula", lote,
                          prefer="resolution=merge-duplicates,return=minimal")
                total_enviadas += len(lote)
            except RuntimeError as e:
                fallos_lotes += 1
                log(f"ERROR en lote de {len(lote)} filas (claves={sorted(claves)}): {e}")
    log(f"RESUMEN --aplicar: nuevas_insertadas={len(nuevas)} backfill_fecha={len(backfill)} "
        f"filas_enviadas={total_enviadas} fallos_lotes={fallos_lotes} en {len(grupos)} grupos "
        f"de columnas · estado={'exito' if fallos_lotes == 0 else 'con_errores'}")
    return 0 if fallos_lotes == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
