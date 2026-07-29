# -*- coding: utf-8 -*-
"""
check_frescura.py — Chequeo de frescura del pipeline vía v_frescura (anon key).

SOLO LECTURA. Pensado para correr cada 30 min desde n8n (workflow
alerta-frescura-vencida) y avisar por Telegram si algún proceso superó su
umbral de horas sin sincronizar (ver migración 020_v_frescura_umbrales.sql).

Uso:
    python scripts/panel-datos/check_frescura.py
Última línea (parseable por n8n):
    RESUMEN: vencidos=N estado=alerta|ok
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from test_integridad_supabase import Supa, cargar_env_local  # reutiliza el helper ya probado

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")


def _md_seguro(texto: str) -> str:
    """Evita que Telegram (parse_mode Markdown) interprete '_'/'*'/'`'/'[' del texto crudo."""
    for ch in ("_", "*", "`", "["):
        texto = texto.replace(ch, "\\" + ch)
    return texto


def main() -> int:
    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not anon:
        print("ERROR: faltan SUPABASE_URL / SUPABASE_ANON_KEY en .env.local")
        print("RESUMEN: vencidos=0 estado=alerta")
        return 1

    supa = Supa(url, anon)
    filas = supa.get_todo("/v_frescura?select=proceso,horas_desde_ultimo,umbral_horas,vencido")
    vencidos = [f for f in filas if f.get("vencido")]

    if vencidos:
        # Mensaje completo aquí (no en la expresión de n8n) — evita el gotcha de \n
        # literal vs escapado en expresiones JS embebidas en JSON (ver convenciones.md).
        # Formato sin corchetes (Telegram/Markdown los interpreta como sintaxis de link
        # y los borra sin avisar) y con proceso escapado (trae guiones bajos crudos).
        print("Datos desactualizados:")
        for f in sorted(filas, key=lambda x: -x["horas_desde_ultimo"]):
            marca = "VENCIDO" if f.get("vencido") else "ok"
            proceso = _md_seguro(f["proceso"])
            print(f"  • {marca}: {proceso} - {f['horas_desde_ultimo']}h (umbral {f['umbral_horas']}h)")

    print(f"RESUMEN: vencidos={len(vencidos)} estado={'alerta' if vencidos else 'ok'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
