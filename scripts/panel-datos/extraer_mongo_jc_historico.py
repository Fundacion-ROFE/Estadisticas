# -*- coding: utf-8 -*-
"""
extraer_mongo_jc_historico.py — jovenes-creativos.User + Applicant (Mongo Atlas, backend
de la app Jóvenes creaTIvos) → payload local, todos los años disponibles (2023-2026).

Solo LECTURA en Mongo (usuario Atlas "Read Only"); no escribe nada en Mongo ni en Supabase.
Mismo patrón que extraer_mongo_mr_historico.py: separar extracción de cualquier carga futura
(pymongo + urllib(Supabase) en el mismo proceso puede colgar conexiones HTTPS — ver
docs/procesos/panel-datos-etl.md, investigación Mongo MR 2026-07-22).

Precedencia: User (cuenta de usuario, incluye egresados/actuales) gana sobre Applicant
(formulario de postulación reciente) cuando una cédula aparece en ambas colecciones.

Uso:
    python extraer_mongo_jc_historico.py

Fundación ROFÉ | Jóvenes creaTIvos
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
RUTA_PAYLOAD      = os.path.join(PROYECTO_ROOT, "tools", "mongo_jc_historico_payload.json")

# Cuentas de staff/pruebas detectadas por rol — no son candidatas reales
ROLES_EXCLUIDOS = {"ADMIN"}


def log(msg: str) -> None:
    print(f"[extraer-mongo-jc] {msg}", flush=True)


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
    mete '.0' y el strip de no-dígitos agrega un CERO EXTRA al final (ver convenciones.md)."""
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor or ""))


def norm_celular(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    return d


def anio_de(creation_date) -> str:
    if isinstance(creation_date, datetime):
        return str(creation_date.year)
    s = str(creation_date or "")
    m = re.match(r"(\d{4})-\d{2}-\d{2}", s)
    return m.group(1) if m else "?"


def extraer_mongo() -> dict:
    """{cedula: fila} — User se lee primero y gana sobre Applicant si la cédula repite."""
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        raise RuntimeError("Falta MONGO_URI")
    cliente = MongoClient(uri, serverSelectionTimeoutMS=15000)

    datos: dict[str, dict] = {}
    proyeccion = {"profile": 1, "creationDate": 1}
    for nombre_col in ("User", "Applicant"):
        col = cliente["jovenes-creativos"][nombre_col]
        n = 0
        for doc in col.find({}, proyeccion):
            p = doc.get("profile", {})
            ced = norm_id(p.get("documentNumber"))
            if not ced or len(ced) < 5:
                continue
            rol = p.get("rol")
            if rol in ROLES_EXCLUIDOS:
                continue
            if ced not in datos:
                datos[ced] = {
                    "nombre": (p.get("completeName") or "").strip().title() or None,
                    "email": (p.get("email") or "").strip().lower() or None,
                    "celular": norm_celular(p.get("phoneNumber")) or None,
                    "ciudad": (p.get("city") or {}).get("name") if isinstance(p.get("city"), dict) else None,
                    "promo_year": p.get("promoYear"),
                    "rol": rol,
                    "coleccion": nombre_col,
                    "fecha_creacion": str(doc.get("creationDate") or ""),
                    "anio_creacion": anio_de(doc.get("creationDate")),
                }
                n += 1
        log(f"jovenes-creativos.{nombre_col}: {n} cédulas nuevas (acumulado {len(datos)})")
    cliente.close()
    return datos


def main() -> int:
    cargar_env_local()
    log("Extrayendo jovenes-creativos.User + Applicant (Mongo, solo lectura)...")
    datos = extraer_mongo()

    with open(RUTA_PAYLOAD, "w", encoding="utf-8") as f:
        json.dump({
            "_nota": "PII — no subir a git",
            "generado": datetime.now().isoformat(timespec="seconds"),
            "total": len(datos),
            "documentos": datos,
        }, f, ensure_ascii=False, indent=1)
    log(f"Payload → {RUTA_PAYLOAD}")

    print(f"RESUMEN: total={len(datos)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
