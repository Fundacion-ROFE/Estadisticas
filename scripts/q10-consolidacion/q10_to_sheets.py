# -*- coding: utf-8 -*-
"""
q10_to_sheets.py — Extracción automática Q10 → Google Sheets
Fundación ROFÉ | Jóvenes creaTIvos
"""

import argparse
import io
import os
import re
import sys
import time

# truststore: en Windows con interceptación SSL corporativa, usa el cert store del SO
try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

# UTF-8 en consola Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding and sys.stderr.encoding.lower() != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import requests
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

# ── Configuración ─────────────────────────────────────────────────────────────
Q10_USUARIO  = "soporte@tocaunavida.org"
Q10_PASSWORD = "JCMR$Form!26"
Q10_BASE_URL = "https://site6.q10.com"

CREDENCIALES_JSON = "credenciales_service_account.json"
SHEET_ID          = "1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0"
NOMBRE_HOJA       = "H1Test"   # valor por defecto; sobreescrito por --grupo en main()
FILA_INICIO       = 2

# Mapa argumento --grupo → nombre de pestaña en Google Sheets
# NOTA: "h2test" es minúsculas intencional — así está nombrada la pestaña en Google Sheets
MAPEO_GRUPOS: dict[str, str] = {
    "h1test": "H1Test",
    "h2test": "h2test",
}

# Mapa argumento --grupo → Sheet ID de Google Sheets (cada grupo puede vivir en un Sheet distinto)
MAPEO_SHEET_IDS: dict[str, str] = {
    "h1test": "1d3S41J9nlVI3qCy-WF_D3ZezTwRCW17vnL7u284XDG0",
    "h2test": "1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs",
}
TAMANIO_LOTE      = 500
PAUSA_LOTE        = 1.2   # segundos entre lotes (cuota API Sheets)

PERIODOS = [21, 22, 23]  # períodos 2026 activos con datos

# Columnas del Excel Consolidado (confirmadas en HAR 2026-06-26)
# El Consolidado ya incluye toda la info del estudiante — no se necesita endpoint Estudiantes
COL_NOMBRES   = "Nombres estudiante"
COL_APELLIDOS = "Apellidos estudiante"
COL_ID        = "Número identificación estudiante"
COL_CELULAR   = "Celular"
COL_EMAIL     = "Email"
COL_CURSO     = "Nombre asignatura"
COL_AVANCE    = "Porcentaje progreso"

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

DIRECTORIO_SCRIPT = os.path.dirname(os.path.abspath(__file__))


# ── Utilidades ────────────────────────────────────────────────────────────────
def log(msg: str) -> None:
    print(f"[Q10-Sheets] {msg}", flush=True)


def leer_excel_bytes(contenido: bytes) -> pd.DataFrame:
    """Lee bytes de un xlsx y detecta automáticamente la fila de encabezados."""
    df_raw = pd.read_excel(io.BytesIO(contenido), header=None, dtype=str)

    palabras_clave = {
        "nombre", "apellido", "matricula", "matrícula",
        "identificacion", "identificación", "programa",
        "codigo", "código", "estudiante", "avance", "progreso",
        "curso", "asignatura",
    }

    fila_header = 0
    # Prioridad 1: fila con ≥2 palabras clave de tabla conocida
    for i, fila in df_raw.iterrows():
        valores = [str(v).lower().strip() for v in fila if pd.notna(v) and str(v).strip()]
        texto = " ".join(valores)
        if sum(1 for p in palabras_clave if p in texto) >= 2:
            fila_header = i
            break
    else:
        # Prioridad 2: primera fila con ≥5 celdas con contenido
        for i, fila in df_raw.iterrows():
            if fila.count() >= 5:
                fila_header = i
                break

    df = pd.read_excel(io.BytesIO(contenido), header=fila_header, dtype=str)
    df = df.dropna(how="all")
    df = df.fillna("")
    df = df.astype(str)
    df = df.replace({"nan": "", "<NA>": ""})

    if not df.empty:
        primera_col = df.columns[0]
        mascara_totales = df[primera_col].str.strip().str.lower().isin(
            {"total", "subtotal", "totales", "leyenda", "nota", "notas", ""}
        )
        df = df[~mascara_totales]

    return df.reset_index(drop=True)


# ── Q10: Login ────────────────────────────────────────────────────────────────
def _q10_post_ajax(session: requests.Session, url: str, data: dict | list,
                   referer: str = f"{Q10_BASE_URL}/login") -> requests.Response:
    resp = session.post(
        url, data=data,
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": referer,
        },
        allow_redirects=True, timeout=30,
    )
    resp.raise_for_status()
    return resp


def _extraer_input(html: str, name: str) -> str:
    m = re.search(
        rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]*)"',
        html, re.IGNORECASE,
    )
    return m.group(1) if m else ""


def login_q10() -> requests.Session:
    """
    Flujo de login Q10 (7 pasos AJAX / form-submits):
    1. GET /login            → cookies iniciales
    2. POST /User/NewLogin   → aplentId (dentro del HTML del modal subdominios)
    3. POST /Subdominios     → JSON {aplentId} (retornarSoloAplent=True)
    4. POST /User/NewLogin   → con contraseña → HTML modal subdominios v2
    5. POST /Subdominios     → HTML modal instituciones (retornarSoloAplent=False)
    6. POST /Instituciones   → HTML modal roles
    7. POST /Roles           → HTML modal doble factor
    8. POST /AutenticarUsuario → sesión autenticada (.AspNet.ApplicationCookie)
    """
    log("Iniciando sesión en Q10 (proceso multi-paso)...")
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept-Language": "es-CO,es;q=0.9",
    })

    base_referer = f"{Q10_BASE_URL}/login"

    # 1. GET /login — cookies iniciales
    session.get(f"{Q10_BASE_URL}/login", timeout=30).raise_for_status()
    log("  Paso 1/7: cookies iniciales obtenidas.")

    # 2. POST /User/NewLogin con solo el usuario → aplentId en el HTML
    r2 = _q10_post_ajax(session, f"{Q10_BASE_URL}/User/NewLogin",
                        {"NombreUsuario": Q10_USUARIO, "AplentId": "", "Contrasena": ""})
    aplent_match = re.search(r"aplentId=([a-f0-9\-]{36})", r2.text)
    if not aplent_match:
        print("\nERROR: No se pudo obtener el aplentId de Q10.\n"
              "Verifica que el usuario exista en la plataforma.", file=sys.stderr)
        sys.exit(1)
    aplent_id = aplent_match.group(1)
    log(f"  Paso 2/7: aplentId = {aplent_id[:8]}...")

    # 3. POST /Subdominios → JSON {aplentId} confirmado
    r3 = _q10_post_ajax(
        session,
        (f"{Q10_BASE_URL}/Subdominios?userName={Q10_USUARIO.replace('@','%40')}"
         f"&recordarme=False&aplentId={aplent_id}&retornarSoloAplent=True"),
        {"pass": "", "subdomain": "."},
    )
    aplent_final = r3.json().get("aplentId", aplent_id)
    log(f"  Paso 3/7: aplentId confirmado.")

    # 4. POST /User/NewLogin con contraseña + aplentId
    r4 = _q10_post_ajax(session, f"{Q10_BASE_URL}/User/NewLogin",
                        {"NombreUsuario": Q10_USUARIO, "Contrasena": Q10_PASSWORD,
                         "AplentId": aplent_final})
    log("  Paso 4/7: credenciales enviadas.")

    # 5. POST /Subdominios retornarSoloAplent=False → modal instituciones
    r5 = _q10_post_ajax(
        session,
        (f"{Q10_BASE_URL}/Subdominios?userName={Q10_USUARIO.replace('@','%40')}"
         f"&recordarme=False&aplentId={aplent_final}&retornarSoloAplent=False"),
        {"pass": Q10_PASSWORD, "subdomain": "."},
    )
    inst_t = _extraer_input(r5.text, "inst_t")
    log("  Paso 5/7: modal instituciones.")

    # 6. POST /Instituciones → modal roles
    r6 = _q10_post_ajax(session, f"{Q10_BASE_URL}/Instituciones",
                        {"inst_t": inst_t, "aplentId": aplent_final})
    rol_t = _extraer_input(r6.text, "rol_t")
    log("  Paso 6/7: modal roles.")

    # 7. POST /Roles (Superadministrador = roleId 0)
    r7 = _q10_post_ajax(session, f"{Q10_BASE_URL}/Roles",
                        {"rol_t": rol_t, "roleId": "0",
                         "aplent": "", "studentId": "", "esSso": "False"})
    ta = _extraer_input(r7.text, "ta")
    log("  Paso 7/7: rol seleccionado.")

    # 8. POST /AutenticarUsuario — completa la sesión
    _q10_post_ajax(
        session, f"{Q10_BASE_URL}/AutenticarUsuario",
        {"codigoSeguridad": "", "ta": ta},
        referer=f"{Q10_BASE_URL}/AutenticacionUsuarioDobleFactor?t={ta}",
    )

    if ".AspNet.ApplicationCookie" not in session.cookies:
        print("\nERROR: Login completado pero no se generó la cookie de sesión.\n"
              "Posible error de credenciales o cambio en el flujo de Q10.", file=sys.stderr)
        sys.exit(1)

    log("  Login exitoso en Q10 (Fundación ROFÉ — Superadministrador).")
    return session


# ── Q10: Descarga de archivos Excel ──────────────────────────────────────────
def _headers_reporte() -> dict:
    return {
        "Content-Type": "application/x-www-form-urlencoded",
        "X-Requested-With": "XMLHttpRequest",
        "Referer": f"{Q10_BASE_URL}/Informes",
        "Accept": "application/json, text/javascript, */*; q=0.01",
    }


def descargar_excel(session: requests.Session, url_azure: str) -> bytes:
    """GET inmediato a la URL de Azure Blob Storage (expira ~3 min)."""
    resp = session.get(url_azure, timeout=60)
    resp.raise_for_status()
    return resp.content


# ── Q10: Consolidado Educación Virtual ───────────────────────────────────────
def descargar_consolidado_periodo(
    session: requests.Session, periodo_id: int
) -> pd.DataFrame | None:
    log(f"  Periodo {periodo_id}...")

    url = (
        f"{Q10_BASE_URL}/Reportes/Excel/ExcelReporte/"
        "EducacionVirtual/ConsolidadoEducacionVirtual"
    )
    payload = [
        (
            "Tipo",
            "Q10.Jack.Areas.ReportesExcel.EducacionVirtual."
            "ServicioReporteConsolidadoEducacionVirtual",
        ),
        ("periodo",      str(periodo_id)),
        ("sedeJornada",  ""),
        ("programa",     ""),
        ("asignatura",   ""),
        ("publicado",    "True"),
        ("archivado",    "false"),
    ]

    resp = session.post(url, data=payload, headers=_headers_reporte(), timeout=60)
    resp.raise_for_status()

    datos = resp.json()

    if datos.get("not_results"):
        log(f"    → sin datos (not_results).")
        return None

    url_excel = datos.get("url")
    if not url_excel:
        log(f"    → respuesta sin URL ni not_results: {datos}")
        return None

    contenido = descargar_excel(session, url_excel)
    df = leer_excel_bytes(contenido)
    log(f"    → {len(df)} filas. Columnas: {df.columns.tolist()}")
    return df


def descargar_todos_consolidados(session: requests.Session) -> pd.DataFrame:
    log("Descargando Consolidado Educación Virtual (todos los periodos)...")
    frames = []
    for pid in PERIODOS:
        df = descargar_consolidado_periodo(session, pid)
        if df is not None:
            frames.append(df)

    if not frames:
        log("ADVERTENCIA: ningún periodo devolvió datos del Consolidado.")
        return pd.DataFrame()

    df_total = pd.concat(frames, ignore_index=True)
    log(f"Consolidado unificado: {len(df_total)} filas.")
    return df_total


def mapear_columnas(df_cons: pd.DataFrame) -> pd.DataFrame:
    """Convierte el Consolidado Q10 al formato H1Test (Identificacion|Nombre|Celular|Email|Curso|Avance|Estado)."""
    df = df_cons.copy()

    partes = [c for c in [COL_NOMBRES, COL_APELLIDOS] if c in df.columns]
    df["Nombre"] = df[partes].apply(
        lambda row: " ".join(v.strip() for v in row if v.strip()), axis=1
    )

    df = df.rename(columns={
        COL_ID:      "Identificacion",
        COL_CELULAR: "Celular",
        COL_EMAIL:   "Email",
        COL_CURSO:   "Curso",
        COL_AVANCE:  "Avance",
    })

    # Estado siempre A: el Consolidado usa archivado=false — solo estudiantes activos
    df["Estado"] = "A"

    COLS_FINALES = ["Identificacion", "Nombre", "Celular", "Email", "Curso", "Avance", "Estado"]
    ausentes = [c for c in COLS_FINALES if c not in df.columns]
    if ausentes:
        log(f"ADVERTENCIA: columnas faltantes del Consolidado: {ausentes}")

    return df[[c for c in COLS_FINALES if c in df.columns]].reset_index(drop=True)


# ── Google Sheets ─────────────────────────────────────────────────────────────
def conectar_sheets() -> gspread.Worksheet:
    log("Conectando a Google Sheets con Service Account...")
    ruta_creds = os.path.join(DIRECTORIO_SCRIPT, CREDENCIALES_JSON)
    if not os.path.isfile(ruta_creds):
        raise FileNotFoundError(
            f"No se encontró '{CREDENCIALES_JSON}'.\n"
            "Colócalo en el mismo directorio que q10_to_sheets.py."
        )
    creds = Credentials.from_service_account_file(ruta_creds, scopes=SCOPES)
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(SHEET_ID)
    hoja = sh.worksheet(NOMBRE_HOJA)
    log(f"  Conectado a '{NOMBRE_HOJA}' — Sheet ID: {SHEET_ID}")
    return hoja


def subir_a_sheets(hoja: gspread.Worksheet, df: pd.DataFrame) -> None:
    log("Borrando datos anteriores desde fila 2 (encabezados intactos)...")
    filas_actuales = len(hoja.get_all_values())
    if filas_actuales > 1:
        hoja.batch_clear([f"A{FILA_INICIO}:ZZ{filas_actuales + 10}"])
        log(f"  {filas_actuales - 1} filas anteriores eliminadas.")
    else:
        log("  La hoja ya estaba vacía.")

    # Expandir la hoja si el DataFrame supera el límite actual de filas
    filas_necesarias = len(df) + FILA_INICIO + 10
    if hoja.row_count < filas_necesarias:
        log(f"  Expandiendo hoja: {hoja.row_count} → {filas_necesarias} filas...")
        hoja.resize(rows=filas_necesarias)

    total = len(df)
    if total == 0:
        log("ADVERTENCIA: DataFrame vacío, nada que subir.")
        return

    datos = df.astype(str).values.tolist()
    num_lotes = (total + TAMANIO_LOTE - 1) // TAMANIO_LOTE
    log(f"Subiendo {total} filas en {num_lotes} lote(s) de hasta {TAMANIO_LOTE}...")

    for idx in range(num_lotes):
        inicio = idx * TAMANIO_LOTE
        fin    = min(inicio + TAMANIO_LOTE, total)
        lote   = datos[inicio:fin]
        fila_destino = FILA_INICIO + inicio
        hoja.update(values=lote, range_name=f"A{fila_destino}", value_input_option="RAW")
        log(f"  Lote {idx + 1}/{num_lotes}: filas {inicio + 1}–{fin} → OK")
        if fin < total:
            time.sleep(PAUSA_LOTE)

    log(f"¡Carga completa! {total} filas subidas a '{NOMBRE_HOJA}'.")


# ── Main ──────────────────────────────────────────────────────────────────────
def main() -> None:
    global NOMBRE_HOJA, SHEET_ID

    parser = argparse.ArgumentParser(
        description="Actualiza una pestaña de H1Test con datos extraídos de Q10"
    )
    parser.add_argument(
        "--grupo",
        default="h1test",
        help=f"Grupo a actualizar. Opciones: {', '.join(MAPEO_GRUPOS)} (default: h1test)",
    )
    args = parser.parse_args()

    if args.grupo not in MAPEO_GRUPOS:
        print(
            f"\nERROR: grupo '{args.grupo}' no reconocido.\n"
            f"Grupos disponibles: {', '.join(MAPEO_GRUPOS)}",
            file=sys.stderr,
        )
        sys.exit(1)

    NOMBRE_HOJA = MAPEO_GRUPOS[args.grupo]
    SHEET_ID    = MAPEO_SHEET_IDS[args.grupo]
    log(f"Grupo: '{args.grupo}' → pestaña: '{NOMBRE_HOJA}' | Sheet ID: {SHEET_ID}")

    try:
        # 1. Login Q10
        session = login_q10()

        # 2. Consolidado Educación Virtual — ya incluye toda la info del estudiante
        df_cons = descargar_todos_consolidados(session)

        if df_cons.empty:
            log("ERROR: ningún periodo devolvió datos del Consolidado.")
            sys.exit(1)

        # 3. Mapear columnas al formato H1Test
        df_final = mapear_columnas(df_cons)
        df_final = df_final.fillna("").astype(str).replace({"nan": "", "<NA>": ""})

        log(f"DataFrame final: {len(df_final)} filas × {len(df_final.columns)} columnas.")
        log(f"  Columnas: {df_final.columns.tolist()}")

        log("Primeras 5 filas del DataFrame final:")
        for i, row in df_final.head(5).iterrows():
            log(f"  [{i+1}] " + " | ".join(f"{c}={str(v)[:20]!r}" for c, v in row.items()))

        # 4. Conectar a Sheets y verificar header
        hoja = conectar_sheets()

        cols_esperadas = df_final.columns.tolist()
        header_actual = hoja.row_values(1)
        if header_actual:
            if header_actual != cols_esperadas:
                log(f"AVISO: el header de la fila 1 en '{NOMBRE_HOJA}' NO coincide con el orden esperado.")
                log(f"  Esperado : {cols_esperadas}")
                log(f"  Actual   : {header_actual}")
                log("  → Actualiza manualmente la fila 1 del Sheet antes de usar fórmulas.")
            else:
                log(f"  Header de '{NOMBRE_HOJA}' verificado: coincide con el orden esperado.")
        else:
            log(f"AVISO: la fila 1 de '{NOMBRE_HOJA}' está vacía. Agrega los encabezados manualmente:")
            log(f"  {cols_esperadas}")

        subir_a_sheets(hoja, df_final)

        # 5. Resumen
        log("=" * 60)
        log("RESUMEN FINAL")
        log(f"  Filas del Consolidado (3 periodos) : {len(df_cons)}")
        log(f"  Filas subidas a Sheets             : {len(df_final)}")
        log(f"  Hoja actualizada                   : {NOMBRE_HOJA}")
        log("=" * 60)
        print(f"RESUMEN: grupo={args.grupo} filas={len(df_final)} estado=exito", flush=True)

    except SystemExit:
        raise
    except FileNotFoundError as e:
        print(f"\nERROR: {e}", file=sys.stderr)
        sys.exit(1)
    except gspread.exceptions.SpreadsheetNotFound:
        print(
            f"\nERROR: Hoja de cálculo no encontrada.\n"
            f"Comparte el Sheet con el Service Account como Editor:\n"
            f"  q10-automatizacion@n8n-automatizacion-q10.iam.gserviceaccount.com\n"
            f"  URL: https://docs.google.com/spreadsheets/d/{SHEET_ID}",
            file=sys.stderr,
        )
        sys.exit(1)
    except gspread.exceptions.WorksheetNotFound:
        print(
            f"\nERROR: No existe la pestaña '{NOMBRE_HOJA}'.\n"
            "Créala manualmente en la hoja de cálculo.",
            file=sys.stderr,
        )
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\nERROR inesperado: {type(e).__name__}: {e}", file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
