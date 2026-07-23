# -*- coding: utf-8 -*-
"""
Test de conexión a MongoDB (histórico Power BI) — Fase 0 del import a Supabase.

Solo LECTURA: lista bases, colecciones y conteos de documentos. No escribe nada
(y el usuario de Atlas está restringido a rol "Read Only" como segunda barrera).
No imprime contenido de documentos (podría ser PII) — solo nombres de campos del
primer documento de cada colección, para reconocer la forma del esquema.

Uso:
    python test_conexion_mongo.py
Lee MONGO_URI de variables de entorno o de .env.local en la raíz del repo.
"""

import os
import sys

try:
    import truststore

    truststore.inject_into_ssl()  # Convención del proyecto: SSL corporativo
except ImportError:
    pass

from pymongo import MongoClient
from pymongo.errors import PyMongoError


def cargar_env_local():
    """Carga .env.local de la raíz del repo si existe (sin sobreescribir el entorno)."""
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


def main():
    cargar_env_local()
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        print("ERROR: definir MONGO_URI (entorno o .env.local)")
        return 1

    print("Conectando a MongoDB Atlas...")
    try:
        cliente = MongoClient(uri, serverSelectionTimeoutMS=15000)
        cliente.admin.command("ping")
    except PyMongoError as e:
        print(f"FALLO de conexión: {e}")
        return 1

    print("OK — conexión establecida\n" + "-" * 60)

    nombres_sistema = {"admin", "local", "config"}
    bases = [b for b in cliente.list_database_names() if b not in nombres_sistema]

    if not bases:
        print("Conectó, pero no se ven bases visibles para este usuario (¿rol muy restringido?).")
        return 1

    for nombre_bd in bases:
        bd = cliente[nombre_bd]
        colecciones = bd.list_collection_names()
        print(f"\nBase: {nombre_bd}  ({len(colecciones)} colecciones)")
        for nombre_col in colecciones:
            col = bd[nombre_col]
            try:
                total = col.estimated_document_count()
            except PyMongoError:
                total = "?"
            doc = col.find_one()
            campos = sorted(doc.keys()) if doc else []
            print(f"  - {nombre_col}: {total} docs — campos: {campos}")

    print("-" * 60)
    print("RESULTADO: TODO OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
