# -*- coding: utf-8 -*-
"""
Test de conexión a Supabase (panel-datos-rofe) — Fase 0 del panel de datos.

Verifica, usando SOLO el anon key (el mismo camino del dashboard público):
  1. La REST API responde.
  2. Los agregados (cohorte_stats, courses) son legibles.
  3. RLS bloquea filas individuales de participants (is_public=false → 0 filas).
  4. RLS bloquea escritura anónima.

Uso:
    python test_conexion_supabase.py
Lee SUPABASE_URL y SUPABASE_ANON_KEY de variables de entorno o de .env.local
en la raíz del repo (formato KEY=VALUE, sin dependencias externas).

Sin dependencias fuera de stdlib + truststore (convención SSL corporativo del proyecto).
"""

import json
import os
import sys
import urllib.error
import urllib.request

try:
    import truststore

    truststore.inject_into_ssl()  # Convención del proyecto: SSL corporativo
except ImportError:
    pass  # En redes sin proxy corporativo funciona igual


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


def peticion(url, key, metodo="GET", cuerpo=None):
    """GET/POST a la REST API. Devuelve (status, datos | None)."""
    req = urllib.request.Request(
        url,
        method=metodo,
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
            "Content-Type": "application/json",
        },
        data=json.dumps(cuerpo).encode() if cuerpo else None,
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.status, json.loads(resp.read() or "null")
    except urllib.error.HTTPError as e:
        return e.code, None


def main():
    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    key = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        print("ERROR: definir SUPABASE_URL y SUPABASE_ANON_KEY (entorno o .env.local)")
        return 1

    resultados = []

    # 1-2. Agregados legibles
    for tabla in ("cohorte_stats", "courses"):
        status, datos = peticion(f"{url}/rest/v1/{tabla}?select=*&limit=5", key)
        ok = status == 200 and isinstance(datos, list)
        resultados.append((f"lectura {tabla} (agregado público)", ok, f"HTTP {status}, {len(datos or [])} filas"))

    # 3. PII bloqueada: participants sin is_public=true debe dar 0 filas (no error)
    status, datos = peticion(f"{url}/rest/v1/participants?select=id&limit=5", key)
    ok = status == 200 and datos == []
    resultados.append(("RLS oculta participants privados", ok, f"HTTP {status}, {len(datos or [])} filas visibles"))

    # 4. Escritura anónima bloqueada
    status, _ = peticion(f"{url}/rest/v1/cohorte_stats", key, "POST", {"cohorte": "TEST-CONEXION"})
    ok = status in (401, 403)
    resultados.append(("RLS bloquea escritura anónima", ok, f"HTTP {status}"))

    print(f"\nTest de conexión Supabase — {url}\n" + "-" * 60)
    fallos = 0
    for nombre, ok, detalle in resultados:
        print(f"  [{'OK ' if ok else 'FALLO'}] {nombre}  ({detalle})")
        fallos += 0 if ok else 1
    print("-" * 60)
    print("RESULTADO: TODO OK" if fallos == 0 else f"RESULTADO: {fallos} verificaciones fallaron")
    return 0 if fallos == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
