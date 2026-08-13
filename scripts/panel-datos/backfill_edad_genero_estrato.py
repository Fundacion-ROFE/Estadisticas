# -*- coding: utf-8 -*-
"""
backfill_edad_genero_estrato.py — completa campos faltantes de `participants` (2026-08-13):
  • género + edad  ← BD Seguimiento de Monitorías JC2026 (CSV). Edad se CALCULA de la
    fecha de nacimiento (el CSV no trae columna Edad).
  • estrato        ← "Convocatoria Fase 1 - Respuestas Colombia" (CSV). Es un universo GRANDE
    de postulantes (11k, no todos JC): se cruza por cédula/correo contra `participants`, así
    solo se tocan los que YA son participantes (los no-JC no matchean).

REGLAS: solo se ESCRIBE donde el campo está NULL (nunca sobrescribe). Cruce cédula → correo.
Match contra `participants` (persona), no por cohorte: género/edad/estrato son atributos de
persona. PATCH con guarda `&campo=is.null` (idempotente).

Uso:
    python backfill_edad_genero_estrato.py --dry-run   # preview
    python backfill_edad_genero_estrato.py             # aplica
"""
import argparse, csv, io, os, re, sys
from datetime import date
from collections import Counter

try:
    import truststore; truststore.inject_into_ssl()
except ImportError:
    pass
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, DIR)
from cargar_supabase import Supa, cargar_env_local  # noqa: E402

CSV_SEG = r"C:\Users\EstudiantesJC\Downloads\BD Seguimiento de Monitorias - JC2026 - Seguimiento (4).csv"
CSV_CONV = r"C:\Users\EstudiantesJC\Downloads\Convocatoria Fase 1 - Respuestas Colombia.csv"


def log(m): print(f"[backfill-egv] {m}", flush=True)
def norm_ced(v): return re.sub(r"\D", "", str(v or "")).lstrip("0")
def norm_email(v):
    m = re.search(r"[a-z0-9._%+\-]+@[a-z0-9.\-]+\.[a-z]{2,}", str(v or "").strip().lower())
    return m.group(0) if m else ""


def edad_desde_fnac(s):
    s = str(s or "").strip()
    m = re.match(r"(\d{1,2})[/\-](\d{1,2})[/\-](\d{4})", s)
    if not m:
        return None
    d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
    try:
        nac = date(y, mo, d)
    except ValueError:
        return None
    hoy = date.today()
    e = hoy.year - nac.year - ((hoy.month, hoy.day) < (nac.month, nac.day))
    return e if 10 <= e <= 90 else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    cargar_env_local()
    supa = Supa(os.environ["SUPABASE_URL"], os.environ["SUPABASE_SERVICE_ROLE_KEY"])

    # 1) Seguimiento → género + edad
    seg_ced, seg_email = {}, {}
    with open(CSV_SEG, encoding="utf-8-sig", newline="") as fh:
        for r in csv.DictReader(fh):
            R = {(k or "").strip(): v for k, v in r.items()}
            rec = {"genero": (R.get("Género") or "").strip() or None,
                   "edad": edad_desde_fnac(R.get("Fecha Nacimiento"))}
            c, e = norm_ced(R.get("ID")), norm_email(R.get("E-mail"))
            if c: seg_ced.setdefault(c, rec)
            if e: seg_email.setdefault(e, rec)
    log(f"Seguimiento: cédula={len(seg_ced)} correo={len(seg_email)}")

    # 2) Convocatoria → estrato (por índice de columna: cédula=8, correo=2, estrato=34)
    conv_ced, conv_email = {}, {}
    with open(CSV_CONV, encoding="utf-8-sig", newline="") as fh:
        rows = list(csv.reader(fh))[1:]
    for r in rows:
        if len(r) <= 34:
            continue
        est = re.sub(r"\D", "", r[34] or "")
        if est not in ("1", "2", "3", "4", "5", "6"):
            continue
        c, e = norm_ced(r[8]), norm_email(r[2])
        if c: conv_ced[c] = int(est)          # last-wins = postulación más reciente
        if e: conv_email[e] = int(est)
    log(f"Convocatoria: cédula={len(conv_ced)} correo={len(conv_email)} (postulantes con estrato válido)")

    # 3) participants con algún hueco
    parts = supa.get_todo("/participants?select=id,q10_id,email,genero,edad,estrato")
    def vac(v): return v is None or str(v).strip() == ""

    updates = {}  # q10_id -> {campo: valor}
    cont = Counter()
    for p in parts:
        c, e = norm_ced(p.get("q10_id")), norm_email(p.get("email"))
        seg = seg_ced.get(c) or seg_email.get(e)
        est = conv_ced.get(c) or conv_email.get(e)
        u = {}
        if vac(p.get("genero")) and seg and seg["genero"]:
            u["genero"] = seg["genero"]; cont["genero"] += 1
        if vac(p.get("edad")) and seg and seg["edad"]:
            u["edad"] = seg["edad"]; cont["edad"] += 1
        if vac(p.get("estrato")) and est:
            u["estrato"] = est; cont["estrato"] += 1
        if u:
            updates[p["q10_id"]] = u

    log(f"Participantes a actualizar: {len(updates)}  |  género={cont['genero']} edad={cont['edad']} estrato={cont['estrato']}")
    if args.dry_run:
        for qid, u in list(updates.items())[:8]:
            log(f"  ej {qid}: {u}")
        log("DRY-RUN: no se escribió nada.")
        return 0

    ok = 0
    for qid, u in updates.items():
        filtro = f"/participants?q10_id=eq.{qid}&" + "&".join(f"{k}=is.null" for k in u)
        try:
            supa._req("PATCH", filtro, u, prefer="return=minimal")
            ok += 1
        except Exception as ex:
            log(f"  aviso {qid}: {ex}")
    log(f"PATCH aplicado a {ok} participantes (solo campos NULL).")
    st, _ = supa._req("POST", "/rpc/recompute_aggregates", {})
    log(f"recompute_aggregates → HTTP {st}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
