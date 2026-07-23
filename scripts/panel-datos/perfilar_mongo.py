# -*- coding: utf-8 -*-
"""
Perfilado de solo-lectura de MongoDB (histórico Power BI) — análisis de brecha.

No extrae ni copia datos individuales. Solo agrega: conteos totales, rangos de
fecha (creationDate/updatedAt/otros) y distribución de algunos campos categóricos,
para decidir qué colecciones traen información genuinamente nueva vs. qué ya se
cubre con fuentes vivas (Q10, Emoflow API, Sheets sociodemográficos, etc.).

Uso:
    python perfilar_mongo.py
"""

import os
import sys
from collections import Counter
from datetime import datetime

try:
    import truststore

    truststore.inject_into_ssl()
except ImportError:
    pass

from pymongo import MongoClient
from pymongo.errors import PyMongoError


def cargar_env_local():
    raiz = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    ruta = os.path.join(raiz, ".env.local")
    if not os.path.exists(ruta):
        return
    with open(ruta, encoding="utf-8") as f:
        for linea in f:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            os.environ.setdefault(clave.strip(), valor.strip())


def rango_fecha(col, campo):
    """Min/max de un campo fecha vía índice/scan barato (find + sort, sin traer todo)."""
    try:
        primero = col.find_one(sort=[(campo, 1)])
        ultimo = col.find_one(sort=[(campo, -1)])
    except PyMongoError:
        return None, None
    if not primero or not ultimo:
        return None, None
    return primero.get(campo), ultimo.get(campo)


def fmt(v):
    if isinstance(v, datetime):
        return v.strftime("%Y-%m-%d")
    return str(v)[:10] if v else "?"


def perfilar_coleccion(col, campo_fecha="creationDate", campos_categoricos=None):
    total = col.estimated_document_count()
    minf, maxf = rango_fecha(col, campo_fecha)
    print(f"    total={total}  {campo_fecha}: {fmt(minf)} -> {fmt(maxf)}")

    for campo in campos_categoricos or []:
        try:
            valores = col.distinct(campo)
        except PyMongoError:
            continue
        if 0 < len(valores) <= 15:
            print(f"    distinct({campo}) = {valores}")

    # Distribución por año del campo fecha (barata: aggregation, no trae documentos)
    try:
        pipeline = [
            {"$match": {campo_fecha: {"$type": "date"}}},
            {"$group": {"_id": {"$year": f"${campo_fecha}"}, "n": {"$sum": 1}}},
            {"$sort": {"_id": 1}},
        ]
        por_anio = {d["_id"]: d["n"] for d in col.aggregate(pipeline)}
        if por_anio:
            print(f"    por año ({campo_fecha}): {por_anio}")
    except PyMongoError as e:
        print(f"    (no se pudo agregar por año: {e})")


def main():
    cargar_env_local()
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        print("ERROR: definir MONGO_URI")
        return 1

    cliente = MongoClient(uri, serverSelectionTimeoutMS=15000)

    objetivo = {
        "mujeres-rofe-db": {
            "Users": dict(campo_fecha="creationDate", campos_categoricos=["stratum", "maritalStatus", "housingType", "isPremium"]),
        },
        "jovenes-creativos": {
            "User": dict(campo_fecha="creationDate", campos_categoricos=["isRejected", "firstPhase"]),
            "Applicant": dict(campo_fecha="creationDate", campos_categoricos=["isRejected", "firstPhase"]),
        },
        "Asistencia-JC": {
            "registros": dict(campo_fecha="createdAt", campos_categoricos=["ciudad", "semana"]),
        },
        "emoflow-reports": {
            "registros": dict(campo_fecha="ultimoIngreso", campos_categoricos=["ciudad"]),
            "estudiantes": dict(campo_fecha="createdAt", campos_categoricos=["ciudad"]),
        },
        # Sanity check rápido de las que sospechamos son de prueba
        "test": {"Users": dict(campo_fecha="creationDate", campos_categoricos=[])},
        "test-jovenes": {"User": dict(campo_fecha="creationDate", campos_categoricos=[])},
        "plataforma_dev": {"users": dict(campo_fecha="createdAt", campos_categoricos=[])},
    }

    for nombre_bd, colecciones in objetivo.items():
        bd = cliente[nombre_bd]
        print(f"\n=== {nombre_bd} ===")
        for nombre_col, cfg in colecciones.items():
            print(f"  -- {nombre_col} --")
            try:
                perfilar_coleccion(bd[nombre_col], **cfg)
            except PyMongoError as e:
                print(f"    ERROR: {e}")

    print("\nListo — perfilado de solo-lectura completo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
