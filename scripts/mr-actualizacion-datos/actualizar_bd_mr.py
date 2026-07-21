# -*- coding: utf-8 -*-
"""
Actualización de BD-Mujeres ROFÉ 2026 (pestaña General) desde el formulario
"Actualización de datos MR2024 (respuestas)".

- Cruce por cédula (col G de General). Gana la respuesta más reciente del form.
- Actualiza: Nombre (D), Correo (E y H), Tipo doc (F), Celular (J), Celular +57 (K),
  Ciudad (M), Departamento (N), Emprendimiento (S).
- Solo escribe celdas cuyo valor cambia; valores vacíos nunca sobreescriben datos.
- Fila tocada → columna "Fecha Actualización" = fecha de la corrida (dd/mm/yyyy).
- Cédulas del form que no existen en General se clasifican antes de agregar:
    * cédula en la pestaña Inactivas → RETIRADA, no se agrega (solo se reporta);
    * match fuerte con otra fila (>=2 señales entre correo, celular, nombre,
      cédula parecida) → POSIBLE TYPO de cédula, no se agrega (solo se reporta);
    * sin candidata → fila nueva al final con fondo naranja.

Uso:
    python actualizar_bd_mr.py            # escribe
    python actualizar_bd_mr.py --dry-run  # solo reporta, no escribe

Salida parseable para n8n (última línea):
    RESUMEN: respuestas=N unicas=M filas_actualizadas=X sin_cambios=Y nuevas=Z retiradas=R posibles_typos=T omitidas=W estado=exito
"""
import sys
import io
import os
import re
import time
import argparse
import unicodedata
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import truststore
truststore.inject_into_ssl()

import gspread
from google.oauth2.service_account import Credentials

# --- Configuración -----------------------------------------------------------
RUTA_CRED = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         "..", "q10-consolidacion", "credenciales_service_account.json")
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

FUENTE_ID = "13a32oExVw64Scpo2YgnMjytXsIIMVNi07NvYoD8QYH0"
FUENTE_PESTANA = "Respuestas de formulario 1"

DESTINO_ID = "1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8"
DESTINO_PESTANA = "General"
INACTIVAS_PESTANA = "Inactivas"

HEADER_FECHA = "Fecha Actualización"
COLOR_FILA_NUEVA = {"red": 1.0, "green": 0.85, "blue": 0.6}  # naranja claro

# Índices 0-based en General
COL_NUM = 0        # A  '#'
COL_NOMBRE = 3     # D
COL_CORREO1 = 4    # E
COL_TIPODOC = 5    # F
COL_CEDULA = 6     # G  (llave — nunca se escribe en filas existentes)
COL_CORREO2 = 7    # H
COL_CELULAR = 9    # J
COL_CEL57 = 10     # K
COL_CIUDAD = 12    # M
COL_DEPTO = 13     # N
COL_EMPREND = 18   # S

# Índices 0-based en Inactivas
INA_NOMBRE = 2     # C  'Completo'
INA_CEDULA = 4     # E
INA_CELULAR = 5    # F
INA_CORREO = 6     # G

# Índices 0-based en el formulario
F_TIMESTAMP = 0
F_NOMBRES = 1
F_APELLIDOS = 2
F_CORREO = 3
F_TIPODOC = 4
F_CEDULA = 5
F_CELULAR = 6
F_DEPTO = 7
F_CIUDAD = 8
F_TIENE_EMPR = 9
F_CUAL_EMPR = 10

LOTE_RANGOS = 400   # ranges por llamada a values.batchUpdate
PAUSA_LOTE = 1.2

CONECTORES = {"de", "del", "la", "las", "los", "y", "e", "da", "do"}


# --- Normalización -----------------------------------------------------------
def solo_digitos(v):
    return re.sub(r"\D", "", str(v or ""))


def limpiar(v):
    return re.sub(r"\s+", " ", str(v or "")).strip()


def titulo(v):
    """Title case respetando conectores en minúscula (no el primer token)."""
    palabras = limpiar(v).split(" ")
    out = []
    for i, p in enumerate(palabras):
        pl = p.lower()
        out.append(pl if (i > 0 and pl in CONECTORES) else pl.capitalize())
    return " ".join(out)


def norm_tipodoc(v):
    t = limpiar(v).lower()
    if not t:
        return ""
    if "ciudadan" in t:
        return "cc"
    if "extranjer" in t:
        return "ce"
    if "ppt" in t or "permiso" in t or "protecc" in t:
        return "ppt"
    if "pasaporte" in t:
        return "pasaporte"
    if "identidad" in t or t == "ti":
        return "ti"
    return t


def norm_celular(v):
    d = solo_digitos(v)
    if len(d) == 12 and d.startswith("57"):
        d = d[2:]
    return d


def norm_correo(v):
    return limpiar(v).lower()


def parse_ts(v):
    for fmt in ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M"):
        try:
            return datetime.strptime(limpiar(v), fmt)
        except ValueError:
            pass
    return None


def col_a1(idx0):
    """Índice 0-based → letra de columna A1."""
    return gspread.utils.rowcol_to_a1(1, idx0 + 1).rstrip("1")


# --- Lectura y cruce ---------------------------------------------------------
def leer_fuente(gc):
    ws = gc.open_by_key(FUENTE_ID).worksheet(FUENTE_PESTANA)
    vals = ws.get_all_values()
    total = len(vals) - 1
    registros = {}   # cedula -> (ts, fila)
    omitidas = 0
    for i, fila in enumerate(vals[1:], start=2):
        if len(fila) <= F_CEDULA:
            omitidas += 1
            continue
        ced = solo_digitos(fila[F_CEDULA])
        if not ced or len(ced) < 4:
            omitidas += 1
            continue
        ts = parse_ts(fila[F_TIMESTAMP]) or datetime.min
        prev = registros.get(ced)
        if prev is None or ts >= prev[0]:
            registros[ced] = (ts, fila)
    return total, registros, omitidas


def construir_valores(fila_form):
    """Valores normalizados que el form aporta para cada columna de General."""
    correo = norm_correo(fila_form[F_CORREO])
    celular = norm_celular(fila_form[F_CELULAR])
    tiene = limpiar(fila_form[F_TIENE_EMPR]).lower()
    cual = limpiar(fila_form[F_CUAL_EMPR]) if len(fila_form) > F_CUAL_EMPR else ""
    if tiene.startswith("s"):
        emprendimiento = cual  # si dijo Sí pero no dijo cuál → vacío → no sobreescribe
    elif tiene.startswith("n"):
        emprendimiento = "N/A"
    else:
        emprendimiento = ""
    return {
        COL_NOMBRE: titulo(fila_form[F_NOMBRES] + " " + fila_form[F_APELLIDOS]),
        COL_CORREO1: correo,
        COL_TIPODOC: norm_tipodoc(fila_form[F_TIPODOC]),
        COL_CORREO2: correo,
        COL_CELULAR: celular,
        COL_CEL57: ("57" + celular) if celular else "",
        COL_CIUDAD: titulo(fila_form[F_CIUDAD]),
        COL_DEPTO: titulo(fila_form[F_DEPTO]),
        COL_EMPREND: emprendimiento,
    }


def sin_tildes(v):
    return "".join(c for c in unicodedata.normalize("NFD", v)
                   if unicodedata.category(c) != "Mn")


def difiere(actual, nuevo, col):
    """True si vale la pena escribir: nuevo no vacío y distinto del actual.

    La comparación ignora tildes: el form suele venir sin acentos y reemplazar
    'Sofía' por 'Sofia' no es información nueva — degradaría el dato de la BD.
    """
    if not nuevo:
        return False
    a, n = limpiar(actual), limpiar(nuevo)
    if col in (COL_CELULAR, COL_CEL57):
        return solo_digitos(a) != solo_digitos(n)
    return sin_tildes(a.lower()) != sin_tildes(n.lower())


# --- Clasificación de respuestas sin match -----------------------------------
def tokens_nombre(v):
    return set(sin_tildes(limpiar(v).lower()).split())


def dist_lev(a, b):
    """Distancia Levenshtein entre dos cédulas (99 si no vale la pena calcular)."""
    if not a or not b or abs(len(a) - len(b)) > 2:
        return 99
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


def senales_match(ced, nombre, correo, celular, cand):
    """Señales de que la respuesta y la fila candidata son la misma persona.

    cand = (cedula, nombre, set_correos, celular). Se considera misma persona
    con >=2 señales — una sola (p.ej. celular compartido en la familia) no basta.
    """
    c_ced, c_nombre, c_correos, c_cel = cand
    s = []
    if correo and correo in c_correos:
        s.append("correo igual")
    if celular and len(celular) == 10 and celular == c_cel:
        s.append("celular igual")
    tn, tc = tokens_nombre(nombre), tokens_nombre(c_nombre)
    if tn and tn == tc:
        s.append("nombre exacto")
    elif tn and tc and len(tn & tc) >= 2 and len(tn & tc) == min(len(tn), len(tc)):
        s.append("nombre contenido")
    if len(ced) >= 6 and dist_lev(ced, c_ced) <= 2:
        s.append(f"cédula parecida ({c_ced})")
    return s


def clasificar_sin_match(nuevas, gen_cand, inac_ced, inac_cand):
    """Separa las respuestas sin match en retiradas / posibles typos / nuevas reales."""
    retiradas, typos, reales = [], [], []
    for ced, fila_form, valores in nuevas:
        nombre = valores[COL_NOMBRE]
        correo = valores[COL_CORREO1]
        celular = valores[COL_CELULAR]
        if ced in inac_ced:
            n_fila, nom_i = inac_ced[ced]
            retiradas.append((ced, nombre, f"Inactivas fila {n_fila} ({nom_i})", ["cédula en Inactivas"]))
            continue
        if celular and ced == celular:
            typos.append((ced, nombre, "—", ["la cédula digitada es el mismo celular"]))
            continue
        mejor = None  # (n_señales, origen, n_fila, cand, señales)
        for origen, filas in (("Inactivas", inac_cand), ("General", gen_cand)):
            for n_fila, cand in filas:
                s = senales_match(ced, nombre, correo, celular, cand)
                if len(s) >= 2 and (mejor is None or len(s) > mejor[0]):
                    mejor = (len(s), origen, n_fila, cand, s)
        if mejor is None:
            reales.append((ced, fila_form, valores))
        elif mejor[1] == "Inactivas":
            retiradas.append((ced, nombre, f"Inactivas fila {mejor[2]} ({mejor[3][1]})", mejor[4]))
        else:
            typos.append((ced, nombre, f"General fila {mejor[2]} · cc {mejor[3][0]} · {mejor[3][1]}", mejor[4]))
    return retiradas, typos, reales


# --- Main --------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="solo reporta, no escribe")
    args = ap.parse_args()

    hoy = datetime.now().strftime("%d/%m/%Y")
    creds = Credentials.from_service_account_file(RUTA_CRED, scopes=SCOPES)
    gc = gspread.authorize(creds)

    total_resp, registros, omitidas = leer_fuente(gc)
    print(f"Formulario: {total_resp} respuestas · {len(registros)} cédulas únicas · {omitidas} omitidas (sin cédula)")

    sh = gc.open_by_key(DESTINO_ID)
    ws = sh.worksheet(DESTINO_PESTANA)
    gen = ws.get_all_values()
    headers = gen[0]

    # Columna de fecha: buscar por nombre; si no existe, primera columna después del último header
    col_fecha = None
    for i, h in enumerate(headers):
        if limpiar(h).lower() == HEADER_FECHA.lower():
            col_fecha = i
            break
    if col_fecha is None:
        ultimo = max(i for i, h in enumerate(headers) if limpiar(h))
        col_fecha = ultimo + 1
        print(f"Columna '{HEADER_FECHA}' no existe → se crea en {col_a1(col_fecha)}1")

    # Índice de General por cédula (una cédula puede tener >1 fila)
    idx = {}
    for n_fila, fila in enumerate(gen[1:], start=2):  # n_fila = fila real en el Sheet
        if len(fila) > COL_CEDULA:
            ced = solo_digitos(fila[COL_CEDULA])
            if ced:
                idx.setdefault(ced, []).append(n_fila)

    updates = []          # ValueRanges
    filas_tocadas = set()
    sin_cambios = 0
    nuevas = []           # filas del form sin match
    detalle_cambios = []

    for ced, (_ts, fila_form) in registros.items():
        valores = construir_valores(fila_form)
        if ced not in idx:
            nuevas.append((ced, fila_form, valores))
            continue
        for n_fila in idx[ced]:
            fila_bd = gen[n_fila - 1]
            cambios_fila = []
            for col, nuevo in valores.items():
                actual = fila_bd[col] if len(fila_bd) > col else ""
                if difiere(actual, nuevo, col):
                    updates.append({
                        "range": f"'{DESTINO_PESTANA}'!{col_a1(col)}{n_fila}",
                        "values": [[nuevo]],
                    })
                    cambios_fila.append(f"{headers[col] or col_a1(col)}: {limpiar(actual)!r}→{nuevo!r}")
            if cambios_fila:
                filas_tocadas.add(n_fila)
                detalle_cambios.append((n_fila, ced, cambios_fila))
            else:
                sin_cambios += 1

    # Fecha de corrida en filas tocadas
    for n_fila in sorted(filas_tocadas):
        updates.append({
            "range": f"'{DESTINO_PESTANA}'!{col_a1(col_fecha)}{n_fila}",
            "values": [[hoy]],
        })

    # --- Clasificar las respuestas sin match: retiradas / typos / nuevas reales
    retiradas, typos = [], []
    if nuevas:
        inac = sh.worksheet(INACTIVAS_PESTANA).get_all_values()
        inac_ced, inac_cand = {}, []
        for n_fila, fila in enumerate(inac[1:], start=2):
            ced = solo_digitos(fila[INA_CEDULA]) if len(fila) > INA_CEDULA else ""
            nombre = limpiar(fila[INA_NOMBRE]) if len(fila) > INA_NOMBRE else ""
            correo = norm_correo(fila[INA_CORREO]) if len(fila) > INA_CORREO else ""
            cel = norm_celular(fila[INA_CELULAR]) if len(fila) > INA_CELULAR else ""
            if ced:
                inac_ced[ced] = (n_fila, nombre)
            if ced or nombre:
                inac_cand.append((n_fila, (ced, nombre, {correo} if correo else set(), cel)))
        gen_cand = []
        for n_fila, fila in enumerate(gen[1:], start=2):
            ced = solo_digitos(fila[COL_CEDULA]) if len(fila) > COL_CEDULA else ""
            nombre = limpiar(fila[COL_NOMBRE]) if len(fila) > COL_NOMBRE else ""
            correos = {norm_correo(fila[c]) for c in (COL_CORREO1, COL_CORREO2)
                       if len(fila) > c and limpiar(fila[c])}
            cel = norm_celular(fila[COL_CELULAR]) if len(fila) > COL_CELULAR else ""
            gen_cand.append((n_fila, (ced, nombre, correos, cel)))
        retiradas, typos, nuevas = clasificar_sin_match(nuevas, gen_cand, inac_ced, inac_cand)

    print(f"\nCruce: {len(registros) - len(nuevas) - len(retiradas) - len(typos)} con match · "
          f"sin match: {len(retiradas)} retiradas · {len(typos)} posibles typos · {len(nuevas)} nuevas reales")
    print(f"Filas a actualizar: {len(filas_tocadas)} · ya al día: {sin_cambios} · celdas a escribir: {len(updates)}")
    for n_fila, ced, cambios in detalle_cambios[:15]:
        print(f"  fila {n_fila} (cc {ced}): " + " | ".join(cambios))
    if len(detalle_cambios) > 15:
        print(f"  ... y {len(detalle_cambios) - 15} filas más")
    for ced, nombre, ref, s in retiradas:
        print(f"  RETIRADA (no se agrega): cc {ced} · {nombre} → {ref} [{', '.join(s)}]")
    for ced, nombre, ref, s in typos:
        print(f"  POSIBLE TYPO (no se agrega, revisar): form cc {ced} · {nombre} → {ref} [{', '.join(s)}]")
    for ced, fila_form, _v in nuevas:
        print(f"  NUEVA: cc {ced} · {titulo(fila_form[F_NOMBRES] + ' ' + fila_form[F_APELLIDOS])}")

    if args.dry_run:
        print("\n[DRY-RUN] No se escribió nada.")
        print(f"RESUMEN: respuestas={total_resp} unicas={len(registros)} "
              f"filas_actualizadas={len(filas_tocadas)} sin_cambios={sin_cambios} "
              f"nuevas={len(nuevas)} retiradas={len(retiradas)} posibles_typos={len(typos)} "
              f"omitidas={omitidas} estado=dry-run")
        return

    # --- Escritura ---
    if col_fecha >= len(headers) or limpiar(headers[col_fecha] if col_fecha < len(headers) else "") == "":
        ws.update_cell(1, col_fecha + 1, HEADER_FECHA)

    for i in range(0, len(updates), LOTE_RANGOS):
        lote = updates[i:i + LOTE_RANGOS]
        sh.values_batch_update({"valueInputOption": "RAW", "data": lote})
        if i + LOTE_RANGOS < len(updates):
            time.sleep(PAUSA_LOTE)

    # Filas nuevas al final, con color
    if nuevas:
        ultima_fila_datos = len(gen)  # gen incluye header → última fila ocupada
        try:
            ultimo_num = max(int(solo_digitos(f[COL_NUM]) or 0) for f in gen[1:] if len(f) > COL_NUM)
        except ValueError:
            ultimo_num = len(gen) - 1
        bloque = []
        for k, (ced, fila_form, valores) in enumerate(nuevas, start=1):
            fila_nueva = [""] * (col_fecha + 1)
            fila_nueva[COL_NUM] = str(ultimo_num + k)
            fila_nueva[COL_CEDULA] = ced
            for col, val in valores.items():
                fila_nueva[col] = val
            fila_nueva[col_fecha] = hoy
            bloque.append(fila_nueva)

        fila_ini = ultima_fila_datos + 1
        fila_fin = ultima_fila_datos + len(bloque)
        if fila_fin > ws.row_count:
            ws.add_rows(fila_fin - ws.row_count)
        ws.update(bloque, f"A{fila_ini}", raw=True)

        sh.batch_update({"requests": [{
            "repeatCell": {
                "range": {
                    "sheetId": ws.id,
                    "startRowIndex": fila_ini - 1,
                    "endRowIndex": fila_fin,
                    "startColumnIndex": 0,
                    "endColumnIndex": col_fecha + 1,
                },
                "cell": {"userEnteredFormat": {"backgroundColor": COLOR_FILA_NUEVA}},
                "fields": "userEnteredFormat.backgroundColor",
            }
        }]})
        print(f"Filas nuevas escritas: {fila_ini}–{fila_fin} (fondo naranja)")

    print(f"\nRESUMEN: respuestas={total_resp} unicas={len(registros)} "
          f"filas_actualizadas={len(filas_tocadas)} sin_cambios={sin_cambios} "
          f"nuevas={len(nuevas)} retiradas={len(retiradas)} posibles_typos={len(typos)} "
          f"omitidas={omitidas} estado=exito")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        print("RESUMEN: estado=error")
        sys.exit(1)
