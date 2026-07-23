# -*- coding: utf-8 -*-
"""
sync_sociodemograficos_mr.py — BD-Mujeres ROFÉ (Sheet vivo) → Supabase participants (solo MR).

Espejo de sync_sociodemograficos.py (que cubre JC desde la BD de monitorias). Extrae de la
pestaña `General` (headers fila 1, cruce por cédula c7): Edad(c12), Ciudad(c13),
Nivel de estudios(c17), Emprendimiento(c19, nombre libre), Estrato(c20), Estado civil(c21),
Tipo de vivienda(c24); y de `Inactivas` (retiradas históricas — mismos campos en columnas
distintas: cédula c5, civil c9, edad c11, emprendimiento c12, vivienda c15, nivel c16,
estrato c17, ciudad c24) como fuente SECUNDARIA: General gana si la cédula está en ambas.
Es la PRIMERA fuente real de vivienda/estrato/estado_civil/nivel_estudio (en JC siguen sin
fuente). genero = "Femenino" constante (programa exclusivo de mujeres). La pestaña
HerpowerED NO se lee (copia de General, ver [[mr-actualizacion-datos]]).

Actualiza SOLO participantes matriculados en cursos programa=mr (si una cédula estuviera
también en JC, la BD de monitorias — corrida después — conserva precedencia en los campos
compartidos; los 4 campos nuevos solo los escribe este script). No crea participantes:
las ~4.000 mujeres de la BD que no están en Q10 se reportan, no se cargan.

⚠ PRIVACIDAD: PII en memoria y en tools/ solamente.

**2026-07-21: se dejó de leer el xlsx exportado a mano de Downloads — ahora lee el Google
Sheet en vivo** de [[mr-actualizacion-datos]] (id `1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8`,
pestañas `General`/`Inactivas`), que el workflow n8n `mr-actualizacion-datos` actualiza a
diario a las 9:30. Permite encadenar este sync a un schedule sin depender de un export manual.

Uso:
    python sync_sociodemograficos_mr.py [--dry-run]
Consola (parseable por n8n):
    RESUMEN: actualizados=N sin_match_supabase=X sin_datos=Y estado=exito

Fundación ROFÉ | Mujeres ROFÉ
"""

import argparse
import io
import json
import os
import re
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                 "credenciales_service_account.json")
SHEET_ID          = "1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8"  # BD-Mujeres ROFÉ 2026
RUTA_REPORTE      = os.path.join(PROYECTO_ROOT, "tools",
                                 f"sociodemograficos_mr_report_{datetime.now():%Y%m%d}.json")

USER_AGENT = "panel-datos-etl/1.0"  # Supabase rechaza secrets con UA de navegador
LOTE       = 500

# Valores que significan "sin dato" en las celdas de texto de General
SIN_DATO = {"", "n/a", "#n/a", "null", "na", "no", "-", "0", "ninguno", "ninguna", "no tengo"}

# Nivel de estudios (c17) → enum nivel_estudio_type. Match por substring, en orden.
MAPA_NIVEL = [
    ("especializac", "postgrado"),
    ("tecn",         "técnico"),      # tecnica/tecnologa + variantes con typo
    ("bachiller",    "secundaria"),
    ("profesional",  "profesional"),
    ("primaria",     "primaria"),
]

# Estado civil (c21) → enum estado_civil_type. Match por substring, en orden
# (el orden importa: "madre soltera" debe caer en soltero antes que "madre cabeza" en otro).
MAPA_CIVIL = [
    ("unión libre",  "unión_libre"),
    ("union libre",  "unión_libre"),
    ("soltera",      "soltero"),
    ("sola",         "soltero"),
    ("casada",       "casado"),
    ("divorci",      "divorciado"),   # divorciada + "proceso de divorcio"
    ("separada",     "divorciado"),
    ("viuda",        "otro"),
    ("madre cabeza", "otro"),
    ("otro",         "otro"),
]

# Tipo de vivienda (c24) → enum vivienda_type
MAPA_VIVIENDA = [
    ("arrend",   "arrendado"),
    ("familiar", "familiar"),
    ("propia",   "propia"),
]


def log(msg: str) -> None:
    print(f"[sync-sociodem-mr] {msg}", flush=True)


def norm_id(valor) -> str:
    """Cédula a solo dígitos. Gotcha openpyxl: float 1041774123.0 → str directo
    mete '.0' y el strip de no-dígitos agrega un CERO EXTRA al final."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor))


def texto(valor) -> str:
    """Celda → texto limpio en minúsculas, o '' si es un 'sin dato'."""
    s = str(valor).strip() if valor is not None else ""
    return "" if s.lower() in SIN_DATO else s


def mapear(valor, mapa) -> str | None:
    v = texto(valor).lower()
    if not v:
        return None
    return next((destino for clave, destino in mapa if clave in v), None)


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


def _num(valor, lo, hi) -> int | None:
    """Celda de texto (Sheet) → int si es dígito y cae en rango, si no None."""
    v = str(valor).strip() if valor is not None else ""
    if v.isdigit() and lo <= int(v) <= hi:
        return int(v)
    return None


def fila_participante(r, idx) -> tuple[str, dict]:
    """(cedula, campos) desde una fila cruda según el mapa de índices 0-based `idx`."""
    ced = norm_id(r[idx["cedula"]])
    if not ced:
        return "", {}
    emprend = texto(r[idx["emprend"]])
    fila = {
        "edad": _num(r[idx["edad"]], 14, 90),
        "ciudad": texto(r[idx["ciudad"]]) or None,
        "nivel_estudio": mapear(r[idx["nivel"]], MAPA_NIVEL),
        "estrato": _num(r[idx["estrato"]], 1, 6),
        "estado_civil": mapear(r[idx["civil"]], MAPA_CIVIL),
        "tipo_vivienda": mapear(r[idx["vivienda"]], MAPA_VIVIENDA),
        "genero": "Femenino",                # programa exclusivo de mujeres
    }
    if emprend:
        fila["nombre_emprendimiento"] = emprend[:200]
        fila["tiene_emprendimiento"] = True
    return ced, fila


# Índices 0-based por pestaña (misma información, columnas distintas)
IDX_GENERAL   = {"cedula": 6, "edad": 11, "ciudad": 12, "nivel": 16, "emprend": 18,
                 "estrato": 19, "civil": 20, "vivienda": 23}
IDX_INACTIVAS = {"cedula": 4, "civil": 8, "edad": 10, "emprend": 11, "vivienda": 14,
                 "nivel": 15, "estrato": 16, "ciudad": 23}


def _conectar_sheet():
    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    return gspread.authorize(creds).open_by_key(SHEET_ID)


def extraer_bd() -> dict:
    """{cedula: {edad, ciudad, nivel_estudio, estrato, estado_civil, tipo_vivienda,
                 nombre_emprendimiento, tiene_emprendimiento, genero}}"""
    log(f"Leyendo Sheet vivo (id {SHEET_ID})...")
    sh = _conectar_sheet()

    datos: dict[str, dict] = {}
    for pestana, idx, min_cols in (("General", IDX_GENERAL, 24), ("Inactivas", IDX_INACTIVAS, 24)):
        n = 0
        for r in sh.worksheet(pestana).get_all_values()[1:]:
            if len(r) < min_cols:
                continue
            ced, fila = fila_participante(r, idx)
            if not ced:
                continue
            if ced not in datos:     # General se lee primero y gana sobre Inactivas
                datos[ced] = fila
                n += 1
        log(f"{pestana}: {n} cédulas nuevas (acumulado {len(datos)})")
    return datos


def main() -> int:
    ap = argparse.ArgumentParser(description="BD-Mujeres ROFÉ → Supabase participants (MR)")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        return 1

    datos = extraer_bd()
    supa = Supa(url, key)
    # Solo participantes con matrícula en cursos MR (una cédula en ambos programas
    # no debe recibir aquí datos que pisen los de la BD de monitorias JC).
    # El eco del nombre satisface el NOT NULL del INSERT propuesto en el upsert.
    mr = supa.get_todo("/participants?select=q10_id,nombre,enrollments!inner(courses!inner(programa))"
                       "&enrollments.courses.programa=eq.mr")
    existentes = {r["q10_id"]: r["nombre"] for r in mr}
    log(f"Participantes MR en Supabase: {len(existentes)}")

    filas, sin_match, sin_datos, stats = [], [], 0, Counter()
    for ced, d in sorted(datos.items()):
        limpio = {k: v for k, v in d.items() if v is not None}
        if not limpio or set(limpio) == {"genero"}:
            sin_datos += 1
            continue
        if ced not in existentes:
            sin_match.append(ced)   # en la BD pero sin matrícula MR en Q10 (mayoría esperada)
            continue
        filas.append({"q10_id": ced, "nombre": existentes[ced], **limpio,
                      "updated_at": datetime.now().isoformat(timespec="seconds")})
        for k in limpio:
            stats[k] += 1

    log(f"A actualizar: {len(filas)} · sin match MR en Supabase: {len(sin_match)} · sin datos: {sin_datos}")
    log("Campos: " + ", ".join(f"{k}={v}" for k, v in stats.most_common()))

    if args.dry_run:
        print(f"RESUMEN: actualizados=0 sin_match_supabase={len(sin_match)} "
              f"sin_datos={sin_datos} estado=dry_run")
        return 0

    # upsert por q10_id — mismo patrón que el sync JC: agrupar por conjunto de claves
    # (gotcha PGRST102: el bulk exige claves idénticas; nunca mandar null explícito).
    grupos: dict[frozenset, list] = {}
    for fila in filas:
        grupos.setdefault(frozenset(fila), []).append(fila)
    for claves, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            supa._req("POST", "/participants?on_conflict=q10_id", grupo[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
    log(f"Actualizados: {len(filas)} (en {len(grupos)} grupos de columnas)")

    _, agg = supa._req("POST", "/rpc/recompute_aggregates", {})
    log(f"Agregados recomputados: {agg}")

    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump({"generado": datetime.now().isoformat(timespec="seconds"),
                   "actualizados": len(filas), "campos": dict(stats),
                   "sin_match_supabase": len(sin_match), "sin_datos": sin_datos},
                  f, ensure_ascii=False, indent=1)
    log(f"Reporte → {RUTA_REPORTE}")

    print(f"RESUMEN: actualizados={len(filas)} sin_match_supabase={len(sin_match)} "
          f"sin_datos={sin_datos} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
