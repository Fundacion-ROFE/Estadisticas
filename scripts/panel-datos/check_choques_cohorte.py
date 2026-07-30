# -*- coding: utf-8 -*-
"""
check_choques_cohorte.py — Chequeo de saltos imposibles en cohorte_ingresos vía
v_choques_cohorte.

SOLO LECTURA. Pensado para correr diario desde n8n (workflow alerta-choques-cohorte)
y avisar por Telegram solo si hay severidad=alta (ver migración
028_v_choques_cohorte_APLICADA.sql). Mismo patrón que check_choques_cursos.py: el
texto completo del mensaje se arma acá (no en la expresión de n8n) para evitar el
gotcha de '\\n' literal vs escapado en expresiones JS embebidas en JSON.

v_choques_cohorte es service_role-only (sin PII, pero sin consumidor público), por
eso este script usa SUPABASE_SERVICE_ROLE_KEY y no el anon key.

Uso:
    python scripts/panel-datos/check_choques_cohorte.py
    python scripts/panel-datos/check_choques_cohorte.py --todas   # incluye media
                                                                    # (solo para probar
                                                                    # el formato del
                                                                    # mensaje; producción
                                                                    # usa severidad=alta)
Última línea (parseable por n8n):
    RESUMEN: alta=N estado=alerta|ok
"""

import argparse
import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from cargar_supabase import Supa, cargar_env_local  # reutiliza el cliente REST ya probado

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
    ap = argparse.ArgumentParser(description="Chequeo de v_choques_cohorte")
    ap.add_argument("--todas", action="store_true",
                    help="Incluye severidad media (solo para probar el formato del mensaje)")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        print("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY en .env.local")
        print("RESUMEN: alta=0 estado=alerta")
        return 1

    supa = Supa(url, key)
    filtro = "&severidad=not.is.null" if args.todas else "&severidad=eq.alta"
    filas = supa.get_todo(
        "/v_choques_cohorte?select=tipo,severidad,programa,cohorte,detalle,updated_at" + filtro
    )

    if filas:
        print("Choques de cohorte detectados:")
        for f in filas:
            tipo = _md_seguro(f["tipo"])
            programa = _md_seguro(f["programa"])
            cohorte = _md_seguro(str(f["cohorte"]))
            detalle = _md_seguro(f["detalle"])
            print(f"  • {tipo} ({programa} {cohorte}) — {detalle}")

    alta = [f for f in filas if f["severidad"] == "alta"]
    print(f"RESUMEN: alta={len(alta)} estado={'alerta' if alta else 'ok'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
