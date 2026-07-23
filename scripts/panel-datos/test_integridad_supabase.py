# -*- coding: utf-8 -*-
"""
test_integridad_supabase.py — Suite de integridad/seguridad de panel-datos-rofe.

SOLO LECTURA. Cada test imprime PASS/FAIL con evidencia; exit code = nº de FAILs.
Tolerancias explícitas (no números mágicos ocultos). Diseñada para correr a mano o
como chequeo diario post-sync (modo --rapido omite los tests pesados).

Uso:
    python scripts/panel-datos/test_integridad_supabase.py [--rapido]
Última línea (parseable por n8n):
    RESUMEN: total=N pass=X fail=Y estado=exito|fallo

Fundación ROFÉ | panel-datos-etl · ver docs/procesos/supabase-estructura.md
"""

import argparse
import io
import json
import os
import sys
import urllib.error
import urllib.request
from collections import Counter
from datetime import date, timedelta

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
USER_AGENT        = "panel-datos-etl/1.0"

CIUDADES = {"BAQ", "BOG", "CAL", "CTG", "MED", "GYL", "QTO", "PAN", "UY"}

# Tolerancias explícitas (documentadas en supabase-estructura.md)
TOL_CUADRE_EMOFLOW_PCT = 2.0   # discrepancia conocida 0,7% por parámetros de descarga distintos
TOL_ROSTER_VS_USUARIOS = 25    # roster semanal (scope=all) ≥ usuarios filtrados; margen absoluto
TOL_OVERLAP_COHORTE    = 5     # personas que pueden estar en activos Y retirados (reingresos)
DIAS_FRESCURA          = 2     # un sync diario puede llevar hasta 2 días si el PC estuvo apagado

resultados = []


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
            return e.code, None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            status, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            if status >= 400:
                raise RuntimeError(f"HTTP {status} en GET {ruta}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def test(nombre: str, ok: bool, evidencia: str) -> None:
    resultados.append((nombre, ok, evidencia))
    print(f"  [{'PASS' if ok else 'FAIL'}] {nombre} — {evidencia}", flush=True)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--rapido", action="store_true", help="omite tests pesados (enrollments completa)")
    args = ap.parse_args()

    cargar_env_local()
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    anon = os.environ.get("SUPABASE_ANON_KEY", "")
    if not url or not key:
        print("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        print("RESUMEN: total=0 pass=0 fail=1 estado=fallo")
        return 1
    supa = Supa(url, key)
    hoy = date.today()
    limite_frescura = (hoy - timedelta(days=DIAS_FRESCURA)).isoformat()

    # ---------- A. FKs / huérfanos ----------
    print("\n== A. Integridad referencial ==")
    parts = supa.get_todo("/participants?select=id,q10_id,email")
    ids_parts = {p["id"] for p in parts}

    emo = supa.get_todo("/emoflow_ingresos?select=id,participant_id,email,grupo_ciudad,ingresos,ultimo_ingreso,fecha_corte")
    huerf_emo = [e for e in emo if e["participant_id"] and e["participant_id"] not in ids_parts]
    test("emoflow_ingresos.participant_id sin huérfanos", len(huerf_emo) == 0,
         f"{len(huerf_emo)} huérfanos de {len(emo)}")

    for tabla in ("postulantes_mr", "postulantes_jc"):
        po = supa.get_todo(f"/{tabla}?select=cedula,participant_id")
        huerf = [p for p in po if p["participant_id"] and p["participant_id"] not in ids_parts]
        test(f"{tabla}.participant_id sin huérfanos", len(huerf) == 0,
             f"{len(huerf)} huérfanos de {len(po)}")
        ceds = [p["cedula"] for p in po]
        test(f"{tabla} cédulas únicas", len(ceds) == len(set(ceds)),
             f"{len(ceds)} filas, {len(set(ceds))} distintas")

    if not args.rapido:
        enr = supa.get_todo("/enrollments?select=participant_id,course_id,porcentaje_avance")
        cursos = supa.get_todo("/courses?select=id")
        ids_cursos = {c["id"] for c in cursos}
        h1 = sum(1 for e in enr if e["participant_id"] not in ids_parts)
        h2 = sum(1 for e in enr if e["course_id"] not in ids_cursos)
        test("enrollments→participants sin huérfanos", h1 == 0, f"{h1} de {len(enr)}")
        test("enrollments→courses sin huérfanos", h2 == 0, f"{h2} de {len(enr)}")
        fuera = sum(1 for e in enr if e["porcentaje_avance"] is not None
                    and not (0 <= e["porcentaje_avance"] <= 100))
        test("porcentaje_avance en [0,100]", fuera == 0, f"{fuera} fuera de rango")

    # ---------- B. Unicidad ----------
    print("\n== B. Unicidad ==")
    emails_norm = [(p["email"] or "").strip().lower() for p in parts if p.get("email")]
    dups_email = [e for e, n in Counter(emails_norm).items() if n > 1]
    test("participants email normalizado único", len(dups_email) == 0, f"{len(dups_email)} duplicados")
    q10s = [p["q10_id"] for p in parts if p.get("q10_id")]
    test("participants q10_id único y no vacío",
         len(q10s) == len(parts) and len(q10s) == len(set(q10s)),
         f"{len(parts)} filas, {len(set(q10s))} q10_id distintos")
    emails_emo = [e["email"] for e in emo]
    test("emoflow_ingresos email único", len(emails_emo) == len(set(emails_emo)),
         f"{len(emails_emo)} filas")

    # ---------- C. Dominios ----------
    print("\n== C. Dominios ==")
    malas = {e["grupo_ciudad"] for e in emo if e["grupo_ciudad"] and e["grupo_ciudad"] not in CIUDADES}
    test("emoflow_ingresos.grupo_ciudad en catálogo", not malas, f"variantes fuera: {malas or 'ninguna'}")

    diario = supa.get_todo("/emoflow_ingresos_diario?select=fecha,grupo_ciudad,ingresos,usuarios_activos")
    malas_d = {d["grupo_ciudad"] for d in diario if d["grupo_ciudad"] not in CIUDADES | {"NACIONAL"}}
    test("emoflow_ingresos_diario.grupo_ciudad en catálogo", not malas_d, f"fuera: {malas_d or 'ninguna'}")
    fut = sum(1 for d in diario if d["fecha"] > hoy.isoformat())
    test("emoflow_ingresos_diario sin fechas futuras", fut == 0, f"{fut} filas futuras")
    fut2 = sum(1 for e in emo if e.get("ultimo_ingreso") and e["ultimo_ingreso"] > hoy.isoformat())
    test("emoflow_ingresos sin ultimo_ingreso futuro", fut2 == 0, f"{fut2} filas")
    edades = supa.get_todo("/participants?select=edad&edad=not.is.null")
    raras = sum(1 for p in edades if not (10 <= p["edad"] <= 90))
    test("participants.edad en [10,90]", raras == 0, f"{raras} fuera de {len(edades)}")

    # ---------- D. Cuadres cruzados (tolerancias explícitas) ----------
    print("\n== D. Cuadres ==")
    sum_persona = sum(e["ingresos"] for e in emo)
    sum_nacional = sum(d["ingresos"] for d in diario if d["grupo_ciudad"] == "NACIONAL")
    delta_pct = abs(sum_persona - sum_nacional) / max(sum_nacional, 1) * 100
    test(f"Σingresos persona vs diario NACIONAL (tol {TOL_CUADRE_EMOFLOW_PCT}%)",
         delta_pct <= TOL_CUADRE_EMOFLOW_PCT,
         f"{sum_persona} vs {sum_nacional} (Δ{delta_pct:.1f}%) — causa conocida: params de descarga distintos")

    sum_ciudades = sum(d["ingresos"] for d in diario if d["grupo_ciudad"] != "NACIONAL")
    test("diario: NACIONAL ≥ Σ ciudades", sum_nacional >= sum_ciudades,
         f"{sum_nacional} ≥ {sum_ciudades} (Δ={sum_nacional-sum_ciudades} sin ciudad mapeada)")

    sem = supa.get_todo("/emoflow_actividad_semanal?select=grupo_ciudad,roster")
    roster_nac = max((s["roster"] for s in sem if s["grupo_ciudad"] == "NACIONAL"), default=0)
    test(f"usuarios ({len(emo)}) ≤ roster nacional ({roster_nac}) + tol {TOL_ROSTER_VS_USUARIOS}",
         len(emo) <= roster_nac + TOL_ROSTER_VS_USUARIOS,
         f"roster incluye scope=all; usuarios filtra empresa+email válido")

    coh = supa.get_todo("/cohorte_ingresos?select=cohorte,programa,ingresados,activos,retirados")
    for c in coh:
        overlap = c["activos"] + c["retirados"] - c["ingresados"]
        test(f"cohorte {c['cohorte']}/{c['programa']}: activos+retirados−ingresados en [0,{TOL_OVERLAP_COHORTE}]",
             0 <= overlap <= TOL_OVERLAP_COHORTE,
             f"{c['activos']}+{c['retirados']}−{c['ingresados']}={overlap} (overlap = retiros con reingreso; "
             f"definición en aprobacion/data.json: cohorte = habilitados ∪ retirados)")

    apro = supa.get_todo("/aprobacion_cursos?select=cohorte,curso,cursaron,activos,retirados,pct_aprobados")
    malos_pct = [a for a in apro if a["pct_aprobados"] is not None and not (0 <= a["pct_aprobados"] <= 100)]
    test("aprobacion_cursos.pct_aprobados en [0,100]", not malos_pct, f"{len(malos_pct)} fuera")

    # v_retiro_probable_jc debe cuadrar exacto con count(en_seguimiento_jc=false) — no es
    # tolerancia, son la misma cosa contada dos veces por dos caminos independientes.
    retiro_prob = supa.get_todo("/v_retiro_probable_jc?select=*")
    jc_alertas = supa.get_todo("/participants?select=id&en_seguimiento_jc=eq.false")
    total_vista = sum(r["retiro_probable_total"] for r in retiro_prob)
    test("v_retiro_probable_jc cuadra con participants.en_seguimiento_jc=false",
         total_vista == len(jc_alertas), f"vista={total_vista} vs participants={len(jc_alertas)}")
    for r in retiro_prob:
        suma = r["retiro_probable_aprobado"] + r["retiro_probable_no_aprobado"]
        test(f"v_retiro_probable_jc {r['cohorte']}: aprobado+no_aprobado=total",
             suma == r["retiro_probable_total"], f"{suma} vs {r['retiro_probable_total']}")

    # ---------- E. Frescura ----------
    print("\n== E. Frescura (syncs diarios) ==")
    max_corte = max((e["fecha_corte"] for e in emo if e.get("fecha_corte")), default="")
    test(f"emoflow_ingresos.fecha_corte ≥ {limite_frescura}", max_corte >= limite_frescura, f"max={max_corte}")
    max_diario = max((d["fecha"] for d in diario), default="")
    test(f"emoflow_ingresos_diario ≥ {limite_frescura}", max_diario >= limite_frescura, f"max={max_diario}")
    snaps = supa.get_todo("/participants_snapshots?select=snapshot_date")
    max_snap = max((s["snapshot_date"] for s in snaps), default="")
    test(f"participants_snapshots ≥ {limite_frescura}", max_snap >= limite_frescura, f"max={max_snap}")
    hist = supa.get_todo("/historial_cursos?select=fecha&order=fecha.desc&limit=1")
    max_hist = hist[0]["fecha"] if hist else ""
    test(f"historial_cursos ≥ {limite_frescura}", max_hist >= limite_frescura, f"max={max_hist}")

    # ---------- F. Seguridad (anon key) ----------
    print("\n== F. Seguridad (superficie anon) ==")
    if anon:
        supa_anon = Supa(url, anon)
        PII = ["participants", "emoflow_ingresos", "email_optout", "email_bounces",
               "participants_snapshots", "postulantes_mr", "postulantes_jc", "retiros",
               "asistencia_zoom", "asistencia_promedio", "v_puntaje_estudiante"]
        for t in PII:
            status, cuerpo = supa_anon._req("GET", f"/{t}?select=*&limit=1")
            bloqueado = status in (401, 403, 404) or (status == 200 and not cuerpo)
            test(f"anon bloqueado en {t}", bloqueado, f"HTTP {status}, filas={len(cuerpo or [])}")
    else:
        test("anon key disponible para test de seguridad", False,
             "falta SUPABASE_ANON_KEY en .env.local — sección F no ejecutada")

    # ---------- Resumen ----------
    total = len(resultados)
    fails = sum(1 for _, ok, _ in resultados if not ok)
    print(f"\n{'='*60}")
    if fails:
        print("TESTS FALLIDOS:")
        for nombre, ok, ev in resultados:
            if not ok:
                print(f"  ✗ {nombre} — {ev}")
    print(f"RESUMEN: total={total} pass={total-fails} fail={fails} "
          f"estado={'exito' if fails == 0 else 'fallo'}")
    return fails


if __name__ == "__main__":
    sys.exit(main())
