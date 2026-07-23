# -*- coding: utf-8 -*-
"""
sync_postulantes_mr.py — BD-Mujeres ROFÉ (Sheet vivo) → Supabase postulantes_mr.

Universo COMPLETO de postulantes/candidatas de Mujeres ROFÉ — no solo las matriculadas
en Q10 (esas ya viven en `participants`, sync_sociodemograficos_mr.py). Lee las 5
pestañas del Sheet que tienen cédula (auditoría Fase 0, 2026-07-22): `General` e
`Inactivas` (fuente primaria de demografía) + `Cursos`/`Cursos%`/`Plataforma MR`
(exports de plataformas legadas que aportan 193 cédulas que NO están en
General∪Inactivas — confirmado, no es basura: nombres/correos reales y, en
Plataforma MR, también socio-demografía usable).

Precedencia por cédula (gana la primera fuente que la trae, incluye más campos):
General > Inactivas > Plataforma MR > Cursos > Cursos%. Mismo criterio "primera
fuente gana" que sync_sociodemograficos_mr.py.

NO crea `participants`: si la cédula matchea un q10_id existente se enlaza vía
participant_id, si no queda NULL (mayoría esperada — ver
docs/procesos/postulantes-mr-supabase.md). Upsert idempotente por cédula.

Detección de posibles typos de cédula (≥2 señales entre correo/celular/nombre,
ver docs/convenciones.md): solo se REPORTA a tools/, nunca se corrige sola ni
bloquea la carga — mismo criterio que actualizar_bd_mr.py.

Uso:
    python sync_postulantes_mr.py [--dry-run]
Consola (parseable por n8n si algún día se encadena):
    RESUMEN: universo=N cargados=X con_match_participant=Y typos_detectados=Z estado=exito

Fundación ROFÉ | Mujeres ROFÉ
"""

import argparse
import io
import json
import os
import re
import sys
from collections import Counter
from datetime import datetime

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import gspread
from google.oauth2.service_account import Credentials
import urllib.error
import urllib.request

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))
PROYECTO_ROOT     = os.path.abspath(os.path.join(DIRECTORIO_SCRIPT, "..", ".."))
RUTA_ENV          = os.path.join(PROYECTO_ROOT, ".env.local")
RUTA_CREDENCIALES = os.path.join(PROYECTO_ROOT, "scripts", "q10-consolidacion",
                                 "credenciales_service_account.json")
RUTA_EXCLUSIONES  = os.path.join(PROYECTO_ROOT, "tools", "exclusiones_prueba.json")
SHEET_ID          = "1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8"  # BD-Mujeres ROFÉ 2026
RUTA_REPORTE      = os.path.join(PROYECTO_ROOT, "tools",
                                 f"postulantes_mr_report_{datetime.now():%Y%m%d}.json")

USER_AGENT = "panel-datos-etl/1.0"
LOTE       = 500

SIN_DATO = {"", "n/a", "#n/a", "null", "na", "no", "-", "0", "ninguno", "ninguna", "no tengo"}

MAPA_NIVEL = [
    ("especializac", "postgrado"),
    ("tecn",         "técnico"),
    ("bachiller",    "secundaria"),
    ("profesional",  "profesional"),
    ("primaria",     "primaria"),
]
MAPA_CIVIL = [
    ("unión libre",  "unión_libre"),
    ("union libre",  "unión_libre"),
    ("soltera",      "soltero"),
    ("sola",         "soltero"),
    ("casada",       "casado"),
    ("divorci",      "divorciado"),
    ("separada",     "divorciado"),
    ("viuda",        "otro"),
    ("madre cabeza", "otro"),
    ("otro",         "otro"),
]
MAPA_VIVIENDA = [
    ("arrend",   "arrendado"),
    ("familiar", "familiar"),
    ("propia",   "propia"),
]


def log(msg: str) -> None:
    print(f"[sync-postulantes-mr] {msg}", flush=True)


def norm_id(valor) -> str:
    if isinstance(valor, float) and valor.is_integer():
        valor = int(valor)
    return re.sub(r"\D", "", str(valor))


def texto(valor) -> str:
    s = str(valor).strip() if valor is not None else ""
    return "" if s.lower() in SIN_DATO else s


def mapear(valor, mapa):
    v = texto(valor).lower()
    if not v:
        return None
    return next((destino for clave, destino in mapa if clave in v), None)


def _num(valor, lo, hi):
    v = str(valor).strip() if valor is not None else ""
    if v.isdigit() and lo <= int(v) <= hi:
        return int(v)
    return None


def norm_celular(v) -> str:
    d = re.sub(r"\D", "", str(v or ""))
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    return d


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


def cargar_exclusiones() -> dict:
    """Cédulas/emails de perfiles de prueba — advertir y seguir si falta el archivo."""
    if not os.path.isfile(RUTA_EXCLUSIONES):
        log(f"AVISO: no se encontró {RUTA_EXCLUSIONES} — no se excluirá ningún perfil de prueba")
        return {"cedulas": set(), "emails": set()}
    with open(RUTA_EXCLUSIONES, encoding="utf-8") as f:
        data = json.load(f)
    perfiles = data.get("perfiles", [])
    return {
        "cedulas": {norm_id(p.get("cedula")) for p in perfiles if p.get("cedula")},
        "emails": {texto(p.get("email")).lower() for p in perfiles if p.get("email")},
    }


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
            raise RuntimeError(f"HTTP {e.code} en {metodo} {ruta}: "
                               f"{e.read().decode(errors='replace')[:500]}") from None

    def get_todo(self, ruta: str, page: int = 1000) -> list:
        filas, offset = [], 0
        sep = "&" if "?" in ruta else "?"
        while True:
            _, lote = self._req("GET", f"{ruta}{sep}limit={page}&offset={offset}")
            filas.extend(lote or [])
            if not lote or len(lote) < page:
                return filas
            offset += page


def _conectar_sheet():
    creds = Credentials.from_service_account_file(
        RUTA_CREDENCIALES, scopes=["https://www.googleapis.com/auth/spreadsheets.readonly"])
    return gspread.authorize(creds).open_by_key(SHEET_ID)


def _fila_sociodemo(r, idx) -> dict:
    """Campos sociodemográficos comunes a General/Inactivas/Plataforma MR (mismo mapeo
    por substring que sync_sociodemograficos_mr.py — los tres traen texto en español)."""
    d = {}
    if "edad" in idx:
        d["edad"] = _num(r[idx["edad"]], 14, 90) if len(r) > idx["edad"] else None
    if "nivel" in idx:
        d["nivel_estudio"] = mapear(r[idx["nivel"]], MAPA_NIVEL) if len(r) > idx["nivel"] else None
    if "estrato" in idx:
        d["estrato"] = _num(r[idx["estrato"]], 1, 6) if len(r) > idx["estrato"] else None
    if "civil" in idx:
        d["estado_civil"] = mapear(r[idx["civil"]], MAPA_CIVIL) if len(r) > idx["civil"] else None
    if "vivienda" in idx:
        d["tipo_vivienda"] = mapear(r[idx["vivienda"]], MAPA_VIVIENDA) if len(r) > idx["vivienda"] else None
    if "emprend" in idx and len(r) > idx["emprend"]:
        emprend = texto(r[idx["emprend"]])
        if emprend:
            d["nombre_emprendimiento"] = emprend[:200]
            d["tiene_emprendimiento"] = True
    return d


# Índices 0-based (ver inspección de headers, docs/procesos/postulantes-mr-supabase.md)
IDX_GENERAL = {"cedula": 6, "nombre": 3, "email": 4, "celular": 9, "ciudad": 12,
               "estado": 1, "fecha_creacion": 2, "edad": 11, "nivel": 16, "emprend": 18,
               "estrato": 19, "civil": 20, "vivienda": 23}
IDX_INACTIVAS = {"cedula": 4, "nombre": 2, "email": 6, "celular": 5, "ciudad": 23,
                  "estado": 26, "edad": 10, "nivel": 15, "emprend": 11,
                  "estrato": 16, "civil": 8, "vivienda": 14}
IDX_PLATAFORMA_MR = {"cedula": 4, "nombre": (1, 2), "email": 3, "celular": 6, "ciudad": 20,
                      "fecha_creacion": 21, "edad": 11, "nivel": 15, "civil": 9,
                      "vivienda": 14, "estrato": 16}
IDX_CURSOS = {"cedula": 3, "nombre": 0, "email": 1, "celular": 4}
# Cursos%: columnas repetidas por bloque de curso, solo nombre+cédula (sin email/celular)
COLS_CEDULA_CURSOS_PCT = [1, 5, 9, 13, 17, 21, 25, 29, 33, 37, 42]


def extraer_general_inactivas(sh) -> dict:
    datos = {}
    for pestana, idx, min_cols in (("General", IDX_GENERAL, 24), ("Inactivas", IDX_INACTIVAS, 24)):
        n = 0
        for r in sh.worksheet(pestana).get_all_values()[1:]:
            if len(r) < min_cols:
                continue
            ced = norm_id(r[idx["cedula"]])
            if not ced:
                continue
            fila = {
                "nombre": texto(r[idx["nombre"]]) or None,
                "email": texto(r[idx["email"]]).lower() or None,
                "celular": norm_celular(r[idx["celular"]]) or None,
                "ciudad": texto(r[idx["ciudad"]]) or None,
                "estado": texto(r[idx["estado"]]) or None,
                "genero": "Femenino",
                "fuente_pestana": pestana.lower(),
            }
            if "fecha_creacion" in idx and len(r) > idx["fecha_creacion"]:
                fila["fecha_creacion"] = texto(r[idx["fecha_creacion"]]) or None
            fila.update(_fila_sociodemo(r, idx))
            if ced not in datos:
                datos[ced] = fila
                n += 1
        log(f"{pestana}: {n} cédulas nuevas (acumulado {len(datos)})")
    return datos


def extraer_plataforma_mr(sh, datos: dict) -> None:
    idx = IDX_PLATAFORMA_MR
    ws = sh.worksheet("Plataforma MR")
    vals = ws.get_all_values()[1:]
    n = 0
    for r in vals:
        if len(r) <= idx["cedula"]:
            continue
        ced = norm_id(r[idx["cedula"]])
        if not ced or ced in datos:
            continue
        c_nom1, c_nom2 = idx["nombre"]
        nombre = " ".join(p for p in (texto(r[c_nom1]) if len(r) > c_nom1 else "",
                                       texto(r[c_nom2]) if len(r) > c_nom2 else "") if p).strip()
        fila = {
            "nombre": nombre or None,
            "email": texto(r[idx["email"]]).lower() if len(r) > idx["email"] else None,
            "celular": norm_celular(r[idx["celular"]]) if len(r) > idx["celular"] else None,
            "ciudad": texto(r[idx["ciudad"]]) if len(r) > idx["ciudad"] else None,
            "fecha_creacion": texto(r[idx["fecha_creacion"]]) if len(r) > idx["fecha_creacion"] else None,
            "genero": "Femenino",
            "fuente_pestana": "plataforma_mr",
        }
        fila.update(_fila_sociodemo(r, idx))
        datos[ced] = fila
        n += 1
    log(f"Plataforma MR: {n} cédulas nuevas (acumulado {len(datos)})")


def extraer_cursos(sh, datos: dict) -> None:
    idx = IDX_CURSOS
    ws = sh.worksheet("Cursos")
    vals = ws.get_all_values()
    n = 0
    for r in vals[2:]:  # doble header: fila1 cohorte, fila2 subheader
        if len(r) <= idx["cedula"]:
            continue
        ced = norm_id(r[idx["cedula"]])
        if not ced or ced in datos:
            continue
        datos[ced] = {
            "nombre": texto(r[idx["nombre"]]) or None,
            "email": texto(r[idx["email"]]).lower() or None,
            "celular": norm_celular(r[idx["celular"]]) or None,
            "genero": "Femenino",
            "fuente_pestana": "cursos",
        }
        n += 1
    log(f"Cursos: {n} cédulas nuevas (acumulado {len(datos)})")


def extraer_cursos_pct(sh, datos: dict) -> None:
    ws = sh.worksheet("Cursos%")
    vals = ws.get_all_values()
    n = 0
    for r in vals[3:]:  # triple header: cohorte / curso / Nombre-Número de cédula-Avance
        for col_ced in COLS_CEDULA_CURSOS_PCT:
            if len(r) <= col_ced:
                continue
            ced = norm_id(r[col_ced])
            if not ced or ced in datos:
                continue
            nombre = texto(r[col_ced - 1]) if col_ced > 0 else ""
            datos[ced] = {
                "nombre": nombre or None,
                "genero": "Femenino",
                "fuente_pestana": "cursos_pct",
            }
            n += 1
    log(f"Cursos%: {n} cédulas nuevas (acumulado {len(datos)})")


def extraer_bd() -> dict:
    log(f"Leyendo Sheet vivo (id {SHEET_ID})...")
    sh = _conectar_sheet()
    datos = extraer_general_inactivas(sh)
    extraer_plataforma_mr(sh, datos)
    extraer_cursos(sh, datos)
    extraer_cursos_pct(sh, datos)
    return datos


# --- Detección de posibles typos de cédula (≥2 señales, ver docs/convenciones.md) ---
def dist_lev(a: str, b: str) -> int:
    if not a or not b or abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def tokens_nombre(v) -> set:
    return set((v or "").lower().split())


def senales_match(ced, nombre, email, celular, c_ced, c_nombre, c_email, c_celular) -> list:
    s = []
    if email and c_email and email == c_email:
        s.append("correo igual")
    if celular and len(celular) == 10 and celular == c_celular:
        s.append("celular igual")
    tn, tc = tokens_nombre(nombre), tokens_nombre(c_nombre)
    if tn and tn == tc:
        s.append("nombre exacto")
    elif tn and tc and len(tn & tc) >= 2 and len(tn & tc) == min(len(tn), len(tc)):
        s.append("nombre contenido")
    if len(ced) >= 6 and dist_lev(ced, c_ced) <= 2:
        s.append(f"cédula parecida ({c_ced})")
    return s


def detectar_typos(datos: dict) -> list:
    """Compara candidatos por bloques (no O(n²) completo — con ~5.300 filas la fuerza
    bruta genera ~14M pares y, peor, slices de lista repetidos que explotan en memoria).

    Bloques de candidatos (cada uno barato de construir): mismo correo exacto, mismo
    celular exacto, mismo conjunto de tokens de nombre, y vecindad en la cédula
    ordenada numéricamente (ventana chica — un typo de un dígito cambia poco el valor
    numérico, cubre el caso real Gina Gleisy 22519636/22519536). Dentro de cada bloque
    sí se exige el criterio completo de ≥2 señales de docs/convenciones.md."""
    items = list(datos.items())
    ced_a_fila = dict(items)

    pares_candidatos = set()

    def agregar_bucket(bucket: dict) -> None:
        for ceds in bucket.values():
            if len(ceds) < 2:
                continue
            for i in range(len(ceds)):
                for j in range(i + 1, len(ceds)):
                    a, b = ceds[i], ceds[j]
                    pares_candidatos.add((a, b) if a < b else (b, a))

    # Tope de tamaño de bucket: un valor compartido por muchas filas (correo/celular
    # institucional tipo soporte@tocaunavida.org) no es señal de identidad — generaría
    # O(k²) pares sin sentido. Se descarta el bucket entero y se avisa.
    TOPE_BUCKET = 25

    por_email, por_celular, por_nombre = {}, {}, {}
    for ced, fila in items:
        if fila.get("email"):
            por_email.setdefault(fila["email"], []).append(ced)
        if fila.get("celular") and len(fila["celular"]) == 10:
            por_celular.setdefault(fila["celular"], []).append(ced)
        tn = frozenset(tokens_nombre(fila.get("nombre")))
        if tn:
            por_nombre.setdefault(tn, []).append(ced)

    for nombre_bucket, bucket in (("email", por_email), ("celular", por_celular), ("nombre", por_nombre)):
        grandes = {k: len(v) for k, v in bucket.items() if len(v) > TOPE_BUCKET}
        if grandes:
            log(f"AVISO: {len(grandes)} valores de {nombre_bucket} compartidos por >{TOPE_BUCKET} filas "
                f"(descartados del cruce de typos, probable dato institucional/placeholder): "
                f"{sorted(grandes.items(), key=lambda kv: -kv[1])[:5]}")
        for k in grandes:
            del bucket[k]

    log(f"Bloques: {len(por_email)} correos, {len(por_celular)} celulares, {len(por_nombre)} nombres")
    agregar_bucket(por_email)
    agregar_bucket(por_celular)
    agregar_bucket(por_nombre)
    log(f"Pares candidatos tras correo/celular/nombre: {len(pares_candidatos)}")

    # Vecindad numérica de cédula (ventana chica) para typos de un dígito
    ordenadas = sorted(ced for ced, _ in items if len(ced) >= 6)
    VENTANA = 8
    for i, ced in enumerate(ordenadas):
        for j in range(i + 1, min(i + 1 + VENTANA, len(ordenadas))):
            c_ced = ordenadas[j]
            if dist_lev(ced, c_ced) <= 2:
                pares_candidatos.add((ced, c_ced) if ced < c_ced else (c_ced, ced))
    log(f"Pares candidatos tras vecindad de cédula: {len(pares_candidatos)}")

    typos = []
    for ced, c_ced in pares_candidatos:
        fila, c_fila = ced_a_fila[ced], ced_a_fila[c_ced]
        s = senales_match(ced, fila.get("nombre"), fila.get("email"), fila.get("celular"),
                          c_ced, c_fila.get("nombre"), c_fila.get("email"), c_fila.get("celular"))
        if len(s) >= 2:
            typos.append({"cedula_a": ced, "nombre_a": fila.get("nombre"),
                          "cedula_b": c_ced, "nombre_b": c_fila.get("nombre"),
                          "senales": s})
    return typos


def main() -> int:
    ap = argparse.ArgumentParser(description="BD-Mujeres ROFÉ (universo completo) → Supabase postulantes_mr")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cargar_env_local()
    url, key = os.environ.get("SUPABASE_URL", ""), os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        log("ERROR: faltan SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY")
        return 1

    exclusiones = cargar_exclusiones()
    datos = extraer_bd()

    # Filtrar perfiles de prueba
    antes = len(datos)
    datos = {ced: d for ced, d in datos.items()
             if ced not in exclusiones["cedulas"] and (d.get("email") or "") not in exclusiones["emails"]}
    if antes != len(datos):
        log(f"Excluidos {antes - len(datos)} perfiles de prueba")

    log(f"Universo total: {len(datos)} cédulas")
    stats_fuente = Counter(d["fuente_pestana"] for d in datos.values())
    log("Por fuente: " + ", ".join(f"{k}={v}" for k, v in stats_fuente.most_common()))

    log("Consultando participants en Supabase...")
    supa = Supa(url, key)
    participantes = supa.get_todo("/participants?select=id,q10_id")
    q10_a_participant = {p["q10_id"]: p["id"] for p in participantes if p.get("q10_id")}
    log(f"Participantes en Supabase (para enlazar): {len(q10_a_participant)}")

    log("Detectando posibles typos de cédula (por bloques)...")
    typos = detectar_typos(datos)
    log(f"Posibles typos de cédula detectados (≥2 señales): {len(typos)}")

    filas = []
    con_match = 0
    for ced, d in sorted(datos.items()):
        fila = {"cedula": ced, **{k: v for k, v in d.items() if v is not None},
                "updated_at": datetime.now().isoformat(timespec="seconds")}
        pid = q10_a_participant.get(ced)
        if pid:
            fila["participant_id"] = pid
            con_match += 1
        filas.append(fila)

    log(f"A cargar: {len(filas)} · con match en participants: {con_match}")

    if args.dry_run:
        print(f"RESUMEN: universo={len(datos)} cargados=0 con_match_participant={con_match} "
              f"typos_detectados={len(typos)} estado=dry_run")
        return 0

    grupos: dict[frozenset, list] = {}
    for fila in filas:
        grupos.setdefault(frozenset(fila), []).append(fila)
    for claves, grupo in grupos.items():
        for i in range(0, len(grupo), LOTE):
            supa._req("POST", "/postulantes_mr?on_conflict=cedula", grupo[i:i + LOTE],
                      prefer="resolution=merge-duplicates,return=minimal")
    log(f"Cargados: {len(filas)} (en {len(grupos)} grupos de columnas)")

    with open(RUTA_REPORTE, "w", encoding="utf-8") as f:
        json.dump({
            "_nota": "PII — no subir a git",
            "generado": datetime.now().isoformat(timespec="seconds"),
            "universo_total": len(datos),
            "por_fuente": dict(stats_fuente),
            "con_match_participant": con_match,
            "posibles_typos": typos,
        }, f, ensure_ascii=False, indent=1)
    log(f"Reporte → {RUTA_REPORTE}")

    print(f"RESUMEN: universo={len(datos)} cargados={len(filas)} "
          f"con_match_participant={con_match} typos_detectados={len(typos)} estado=exito")
    return 0


if __name__ == "__main__":
    sys.exit(main())
