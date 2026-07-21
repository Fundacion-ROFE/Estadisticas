# -*- coding: utf-8 -*-
"""
alerta_desercion.py — Alerta de deserción (Tarea 4 de plan-ejecucion-sonnet).

Versión "una sola fuente" de tools/panel_riesgo.py: en vez de cruzar h2test (Q10) ×
pestaña Avance (manual) desde Google Sheets, lee la fuente ya consolidada en Supabase
(panel-datos-rofe) — enrollments.porcentaje_avance — y detecta estudiantes en riesgo de
deserción por curso.

Regla de riesgo (una sola fuente, decisión Samuel 2026-07-15):
  matrícula NO completada con avance < UMBRAL (default 60, mismo que panel_riesgo).
    · avance == 0        → "posible abandono" (no ha iniciado)
    · 0 < avance < umbral → "avance bajo (X%)"

Alcance por defecto: programa=jc, cohorte=2026 (las cohortes viejas son cursos ya
cerrados = ruido). Configurable con --programa / --cohorte.

Salidas:
  · Mensaje resumido listo para Telegram → stdout (lo captura el nodo Execute Command
    de n8n y lo envía el nodo Telegram del bot q10-consolidacion a Samuel).
  · Detalle con PII (nombre/email/ciudad) → tools/reportes/alerta_desercion_YYYYMMDD.csv
    (carpeta gitignoreada) con --csv.
  · Línea parseable por n8n:
        RESUMEN: en_riesgo=N abandono=X avance_bajo=Y estado=exito

Credenciales: SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY de .env.local (raíz). El
service_role bypasea RLS (participants tiene PII con RLS activa) — SOLO backend/n8n,
jamás exponerlo. Mismo patrón que cargar_supabase.py.

⚠ PRIVACIDAD: el CSV y el mensaje de Telegram llevan PII (nombres/correos). Van a
carpeta local gitignoreada y al chat privado de Samuel — NUNCA a GitHub.

Uso:
    python scripts/panel-datos/alerta_desercion.py            # resumen a consola
    python scripts/panel-datos/alerta_desercion.py --csv      # + CSV detallado en tools/
    python scripts/panel-datos/alerta_desercion.py --programa jc --cohorte 2026 --umbral 60

Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import csv
import io
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import date, datetime

try:
    import truststore
    truststore.inject_into_ssl()  # SSL corporativo (convención del proyecto)
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
CARPETA_REPORTES  = os.path.join(PROYECTO_ROOT, "tools", "reportes")

USER_AGENT = "panel-datos-etl/1.0"  # NO Mozilla — Supabase bloquea secrets "de navegador"


def log(msg: str) -> None:
    print(f"[alerta-desercion] {msg}", file=sys.stderr, flush=True)


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
    """Cliente REST mínimo (stdlib) con service key. Copiado de cargar_supabase.py."""

    def __init__(self, url: str, key: str):
        self.base = url.rstrip("/") + "/rest/v1"
        self.key = key

    def _req(self, metodo: str, ruta: str):
        headers = {
            "apikey": self.key,
            "Authorization": f"Bearer {self.key}",
            "Content-Type": "application/json",
            "User-Agent": USER_AGENT,
        }
        req = urllib.request.Request(self.base + ruta, method=metodo, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                datos = resp.read()
                return resp.status, json.loads(datos) if datos else None
        except urllib.error.HTTPError as e:
            detalle = e.read().decode(errors="replace")[:500]
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: {detalle}") from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        """GET paginado (PostgREST corta en ~1000 filas por defecto)."""
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


# ── Lectura de riesgo desde Supabase ────────────────────────────────────────────
def leer_riesgo(supa: Supa, programa: str, cohorte: str, umbral: int) -> list:
    """
    Enrollments NO completadas con avance < umbral en cursos del programa/cohorte.
    Retorna filas planas: {nombre, email, ciudad, grupo_ciudad, curso, avance}.
    El filtro embebido usa !inner para que courses.programa/cohorte realmente excluya.
    """
    select = (
        "porcentaje_avance,estado,"
        "participants!inner(nombre,email,ciudad,grupo_ciudad),"
        "courses!inner(nombre,programa,cohorte)"
    )
    ruta = (
        "/enrollments?"
        + urllib.parse.urlencode({"select": select})
        + f"&courses.programa=eq.{programa}"
        + f"&courses.cohorte=eq.{cohorte}"
        + f"&porcentaje_avance=lt.{umbral}"
        + "&estado=neq.completado"
    )
    filas = []
    for e in supa.get_todo(ruta):
        p = e.get("participants") or {}
        c = e.get("courses") or {}
        filas.append({
            "nombre":       (p.get("nombre") or "").strip(),
            "email":        (p.get("email") or "").strip().lower(),
            "ciudad":       (p.get("ciudad") or "").strip(),
            "grupo_ciudad": (p.get("grupo_ciudad") or "").strip(),
            "curso":        (c.get("nombre") or "").strip(),
            "avance":       int(e.get("porcentaje_avance") or 0),
        })
    return filas


# ── Agregación por estudiante ────────────────────────────────────────────────────
def agrupar(filas: list) -> list:
    """
    Colapsa por email → un estudiante con la lista de sus cursos en riesgo.
    motivo del estudiante = "abandono" si tiene algún curso en 0%, si no "avance_bajo".
    Ordena por severidad (avance mínimo ascendente).
    """
    por_est: dict = {}
    for f in filas:
        clave = f["email"] or f"{f['nombre']}|{f['curso']}"  # fallback si no hay email
        est = por_est.setdefault(clave, {
            "nombre": f["nombre"], "email": f["email"],
            "ciudad": f["ciudad"], "grupo_ciudad": f["grupo_ciudad"],
            "cursos": [],
        })
        est["cursos"].append({"curso": f["curso"], "avance": f["avance"]})

    estudiantes = []
    for est in por_est.values():
        min_av = min(c["avance"] for c in est["cursos"])
        est["min_avance"] = min_av
        est["motivo"] = "abandono" if min_av == 0 else "avance_bajo"
        estudiantes.append(est)

    estudiantes.sort(key=lambda e: (e["min_avance"], -len(e["cursos"])))
    return estudiantes


def _label_grupo(est: dict) -> str:
    return est["grupo_ciudad"] or est["ciudad"] or "—"


# ── Salidas ──────────────────────────────────────────────────────────────────────
def construir_mensaje(estudiantes: list, programa: str, cohorte: str, umbral: int,
                      top: int) -> str:
    abandono = [e for e in estudiantes if e["motivo"] == "abandono"]
    avance_bajo = [e for e in estudiantes if e["motivo"] == "avance_bajo"]

    # Conteo por grupo/ciudad
    por_grupo: dict = defaultdict(int)
    for e in estudiantes:
        por_grupo[_label_grupo(e)] += 1
    linea_grupo = " · ".join(
        f"{g} {n}" for g, n in sorted(por_grupo.items(), key=lambda x: -x[1])
    )

    hoy = date.today().isoformat()
    L = []
    L.append(f"🚨 Alerta de deserción — {programa.upper()} {cohorte} ({hoy})")
    L.append(f"Estudiantes en riesgo (avance < {umbral}%): {len(estudiantes)}")
    L.append(f"  • 🔴 Posible abandono (0%): {len(abandono)}")
    L.append(f"  • 🟡 Avance bajo (1–{umbral - 1}%): {len(avance_bajo)}")
    if linea_grupo:
        L.append(f"Por grupo: {linea_grupo}")
    L.append("")
    L.append(f"Top {min(top, len(abandono))} posibles abandonos:")
    for e in abandono[:top]:
        cursos = ", ".join(c["curso"] for c in e["cursos"] if c["avance"] == 0)
        L.append(f"  - {e['nombre'] or e['email']} — {cursos or '—'} [{_label_grupo(e)}]")
    if len(abandono) > top:
        L.append(f"  … y {len(abandono) - top} más (ver CSV)")
    L.append("")
    L.append("Detalle con correos: tools/reportes/alerta_desercion_"
             f"{datetime.now():%Y%m%d}.csv  (local, privado)")
    return "\n".join(L)


def exportar_csv(estudiantes: list) -> str:
    os.makedirs(CARPETA_REPORTES, exist_ok=True)
    ruta = os.path.join(CARPETA_REPORTES, f"alerta_desercion_{datetime.now():%Y%m%d}.csv")
    with open(ruta, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Nombre", "Email", "Ciudad", "Grupo", "Motivo",
                    "Curso", "Avance_%"])
        for e in estudiantes:
            for c in e["cursos"]:
                w.writerow([e["nombre"], e["email"], e["ciudad"], _label_grupo(e),
                            e["motivo"], c["curso"], c["avance"]])
    return ruta


# ── Main ─────────────────────────────────────────────────────────────────────────
def main() -> int:
    ap = argparse.ArgumentParser(description="Alerta de deserción — ROFÉ (Supabase)")
    ap.add_argument("--programa", default="jc", help="jc / mr / stand (default jc)")
    ap.add_argument("--cohorte", default="2026", help="Cohorte a evaluar (default 2026)")
    ap.add_argument("--umbral", type=int, default=60, help="Umbral de riesgo %% (default 60)")
    ap.add_argument("--top", type=int, default=15, help="Nº de nombres en el mensaje (default 15)")
    ap.add_argument("--csv", action="store_true", help="Exportar detalle PII a tools/reportes/")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY (.env.local o entorno)")
        print("RESUMEN: en_riesgo=0 abandono=0 avance_bajo=0 estado=error_credenciales")
        return 1

    supa = Supa(url, key)
    try:
        filas = leer_riesgo(supa, args.programa, args.cohorte, args.umbral)
    except RuntimeError as e:
        log(f"ERROR leyendo Supabase: {e}")
        print("RESUMEN: en_riesgo=0 abandono=0 avance_bajo=0 estado=error_supabase")
        return 1

    estudiantes = agrupar(filas)
    abandono = sum(1 for e in estudiantes if e["motivo"] == "abandono")
    avance_bajo = len(estudiantes) - abandono
    log(f"{len(filas)} matrículas en riesgo → {len(estudiantes)} estudiantes "
        f"({abandono} abandono, {avance_bajo} avance bajo)")

    # Mensaje para Telegram → stdout
    print(construir_mensaje(estudiantes, args.programa, args.cohorte, args.umbral, args.top))

    if args.csv:
        ruta = exportar_csv(estudiantes)
        log(f"CSV detallado (PII): {ruta}")

    print(f"\nRESUMEN: en_riesgo={len(estudiantes)} abandono={abandono} "
          f"avance_bajo={avance_bajo} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
