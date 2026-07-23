# -*- coding: utf-8 -*-
"""
extraer_mongo_mr_historico.py — mujeres-rofe-db.Users (Mongo Atlas, backend histórico de
la app Mujeres ROFÉ) → payload local, cohortes 2023 y 2024.

Solo LECTURA en Mongo (usuario Atlas "Read Only"); no escribe nada en Mongo. Escribe un
único payload PII en tools/ (gitignoreado) para que cargar_mongo_mr_historico.py lo suba
a Supabase en un proceso APARTE — pymongo + urllib(Supabase) en el mismo proceso cuelga
las conexiones HTTPS (conflicto de backend TLS, confirmado empíricamente 2026-07-22);
separar extracción de carga lo evita y de paso deja un artefacto revisable antes de cargar.

Uso:
    python extraer_mongo_mr_historico.py
"""

import io
import json
import os
import re
import sys
from datetime import datetime

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

from pymongo import MongoClient

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "mongo_mr_historico_payload.json")

COHORTES_DISPONIBLES = (2023, 2024)

MAPA_NIVEL = [
    ("especializac", "postgrado"),
    ("tecn",         "técnico"),
    ("bachiller",    "secundaria"),
    ("primaria",     "primaria"),
    ("profesional",  "profesional"),
]
MAPA_CIVIL = [
    ("unión libre",  "unión_libre"),
    ("union libre",  "unión_libre"),
    ("soltera",      "soltero"),
    ("casada",       "casado"),
    ("divorci",      "divorciado"),
    ("separada",     "divorciado"),
    ("viuda",        "otro"),
    ("otro",         "otro"),
]
MAPA_VIVIENDA = [
    ("arrend",   "arrendado"),
    ("familiar", "familiar"),
    ("propia",   "propia"),
]


def log(msg: str) -> None:
    print(f"[extraer-mongo-mr] {msg}", flush=True)


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


def norm_id(valor) -> str:
    """Cédula a solo dígitos. Gotcha BSON/openpyxl: float 11086478896.0 → str directo
    mete '.0' y el strip de no-dígitos agrega un CERO EXTRA al final (ver convenciones.md).
    mujeres-rofe-db.Users guarda documentNumber como string (verificado 2026-07-22), pero
    el guard se deja por si acaso — mismo bug real encontrado en extraer_mongo_jc_historico.py."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor or ""))


def texto(valor) -> str:
    return str(valor).strip() if valor is not None else ""


def norm_celular(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    return d


def mapear(valor, mapa):
    v = texto(valor).lower()
    if not v:
        return None
    return next((destino for clave, destino in mapa if clave in v), None)


def anio_de(creation_date) -> int | None:
    """creationDate es inconsistente en Mongo: a veces str ISO, a veces datetime BSON."""
    if isinstance(creation_date, datetime):
        return creation_date.year
    s = str(creation_date or "")
    m = re.match(r"(\d{4})-\d{2}-\d{2}", s)
    return int(m.group(1)) if m else None


def _num(valor, lo, hi) -> int | None:
    v = str(valor).strip() if valor is not None else ""
    if v.isdigit() and lo <= int(v) <= hi:
        return int(v)
    return None


def extraer_mongo() -> dict:
    """{anio: {cedula: fila}}"""
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        raise RuntimeError("Falta MONGO_URI")
    cliente = MongoClient(uri, serverSelectionTimeoutMS=15000)
    col = cliente["mujeres-rofe-db"]["Users"]

    por_anio: dict[int, dict] = {a: {} for a in COHORTES_DISPONIBLES}
    proyeccion = {
        "documentNumber": 1, "firstName": 1, "lastName": 1, "email": 1, "phoneNumber": 1,
        "location": 1, "age": 1, "education": 1, "stratum": 1, "maritalStatus": 1,
        "housingType": 1, "creationDate": 1,
    }
    for doc in col.find({}, proyeccion):
        anio = anio_de(doc.get("creationDate"))
        if anio not in por_anio:
            continue
        ced = norm_id(doc.get("documentNumber"))
        if not ced:
            continue
        nombre = " ".join(p for p in (texto(doc.get("firstName")), texto(doc.get("lastName"))) if p)
        loc = doc.get("location") or {}
        fila = {
            "nombre": nombre or None,
            "email": texto(doc.get("email")).lower() or None,
            "celular": norm_celular(doc.get("phoneNumber")) or None,
            "ciudad": texto(loc.get("cityName")) or None,
            "genero": "Femenino",
            "fuente_pestana": f"mongo_historico_{anio}",
            "fecha_creacion": texto(doc.get("creationDate")) or None,
            "edad": _num(doc.get("age"), 14, 90),
            "nivel_estudio": mapear(doc.get("education"), MAPA_NIVEL),
            "estrato": _num(doc.get("stratum"), 1, 6),
            "estado_civil": mapear(doc.get("maritalStatus"), MAPA_CIVIL),
            "tipo_vivienda": mapear(doc.get("housingType"), MAPA_VIVIENDA),
        }
        por_anio[anio].setdefault(ced, fila)  # una cédula repetida en el año → gana la primera
    cliente.close()
    return por_anio


def main() -> int:
    cargar_env_local()
    log("Extrayendo mujeres-rofe-db.Users (Mongo, solo lectura)...")
    por_anio = extraer_mongo()
    for anio in COHORTES_DISPONIBLES:
        log(f"  cohorte {anio}: {len(por_anio[anio])} cédulas extraídas")

    with open(RUTA_PAYLOAD, "w", encoding="utf-8") as f:
        json.dump({
            "_nota": "PII — no subir a git",
            "generado": datetime.now().isoformat(timespec="seconds"),
            "por_anio": {str(a): d for a, d in por_anio.items()},
        }, f, ensure_ascii=False, indent=1)
    log(f"Payload → {RUTA_PAYLOAD}")

    total = sum(len(d) for d in por_anio.values())
    print(f"RESUMEN: extraidos_2023={len(por_anio[2023])} extraidos_2024={len(por_anio[2024])} "
          f"total={total} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
