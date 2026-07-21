#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preparar_certificados.py — Divide un PDF de certificados (una página por persona) en archivos
individuales y cruza el nombre impreso en cada página contra la pestaña General de la
BD-Mujeres ROFÉ para hallar el correo.

USO:
  python preparar_certificados.py --dividir RUTA_AL_PDF.pdf
      Separa el PDF en tools/mujeres-rofe-correos/data/certificados/pagina_NN.pdf y extrae el
      texto de cada página a certificados_texto.csv. Imprime el texto de la página 1 con
      número de línea para identificar en qué línea está el nombre.

  python preparar_certificados.py --emparejar --linea N
      Usa la línea N del texto extraído como nombre de cada certificado, la cruza contra la
      pestaña General de la BD-Mujeres ROFÉ (Google Sheet) y escribe certificados_matches.csv
      con nombre, correo y un score de confianza para revisión manual.

PRIVACIDAD: todo lo que toca nombres/correos va a tools/ (gitignoreado), nunca a scripts/ (git).
"""
import argparse
import csv
import os
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

from pypdf import PdfReader, PdfWriter

BASE = Path(__file__).parent
PROYECTO_ROOT = BASE.parent.parent.parent  # admin-usable/
TOOLS_DATA = PROYECTO_ROOT / "tools" / "mujeres-rofe-correos" / "data" / "certificados"
TOOLS_DATA.mkdir(parents=True, exist_ok=True)

CRED_SA = PROYECTO_ROOT / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"
SHEET_ID = "1ZsC4WyY26aOCEMrnZ_l8Tn-l69DB_0ADs5lnecaoEP8"  # BD-Mujeres ROFÉ 2026
SHEET_TAB = "General"
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

RUTA_TEXTO = TOOLS_DATA / "certificados_texto.csv"
RUTA_MATCHES = TOOLS_DATA / "certificados_matches.csv"

UMBRAL_OK = 0.85


# ============================================================================
def normalizar(nombre):
    """Mayúsculas, sin tildes, espacios colapsados — para comparar nombres de forma robusta."""
    nombre = unicodedata.normalize("NFKD", nombre or "")
    nombre = "".join(c for c in nombre if not unicodedata.combining(c))
    nombre = re.sub(r"\s+", " ", nombre).strip().upper()
    return nombre


def similitud_caracteres(a, b):
    return SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()


def similitud_tokens(a, b):
    """Fracción de las palabras del nombre más corto que aparecen también en el más largo.
    Cubre el caso frecuente en la BD de nombres incompletos (falta un nombre o apellido):
    'Ady Luz Martinez' vs 'Ady Luz Martinez Hernandez' debe puntuar alto aunque
    la comparación por caracteres los penalice por la diferencia de longitud."""
    ta, tb = set(normalizar(a).split()), set(normalizar(b).split())
    menor = min(len(ta), len(tb))
    if not menor:
        return 0.0
    return len(ta & tb) / menor


def similitud(a, b):
    """Mejor de dos métricas: caracteres (para variantes ortográficas/tildes) y
    tokens (para nombres incompletos en la BD)."""
    return max(similitud_caracteres(a, b), similitud_tokens(a, b))


def reconstruir_texto_espaciado(linea):
    """Canva a veces exporta el texto con cada letra como glyph separado, generando líneas
    como 'A d y  L u z' (espacio simple = separador de letra, espacio doble = separador de
    palabra real). Si detecta ese patrón (hay al menos un espacio doble), reconstruye las
    palabras usando los dobles como frontera. Si la línea viene con espaciado normal
    (sin dobles espacios), la deja intacta."""
    if "  " not in linea:
        return linea
    palabras, actual = [], []
    for tok in linea.split(" "):
        if tok == "":
            if actual:
                palabras.append("".join(actual))
                actual = []
        else:
            actual.append(tok)
    if actual:
        palabras.append("".join(actual))
    return " ".join(palabras)


# ============================================================================
def accion_dividir(ruta_pdf):
    reader = PdfReader(ruta_pdf)
    n = len(reader.pages)
    print(f"[*] PDF con {n} páginas: {ruta_pdf}")

    filas_texto = []
    for i, pagina in enumerate(reader.pages, start=1):
        writer = PdfWriter()
        writer.add_page(pagina)
        archivo = TOOLS_DATA / f"pagina_{i:02d}.pdf"
        with open(archivo, "wb") as f:
            writer.write(f)

        texto = pagina.extract_text() or ""
        filas_texto.append({"pagina": i, "texto": texto})

    with open(RUTA_TEXTO, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pagina", "texto"])
        w.writeheader()
        w.writerows(filas_texto)

    print(f"[OK] {n} archivos individuales en {TOOLS_DATA}")
    print(f"[OK] Texto extraído guardado en {RUTA_TEXTO}")

    print(f"\n[*] Texto de la página 1 (línea por línea) — identifica en cuál está el nombre:\n")
    lineas = filas_texto[0]["texto"].splitlines()
    if not lineas or not any(l.strip() for l in lineas):
        print("  [AVISO] No se extrajo texto legible de la página 1.")
        print("  Puede que el nombre esté como imagen/curvas en vez de texto real.")
        print("  Antes de continuar, revisa manualmente pagina_01.pdf.")
    for idx, linea in enumerate(lineas):
        print(f"  [{idx:2}] {linea}")
    print(f"\nCuando identifiques la línea del nombre, corre:")
    print(f"  python preparar_certificados.py --emparejar --linea N")


# ============================================================================
def cargar_general_sheet():
    """Lee la pestaña General de la BD-Mujeres ROFÉ: lista de (nombre, correo)."""
    import gspread
    from google.oauth2.service_account import Credentials

    if not CRED_SA.is_file():
        raise FileNotFoundError(f"Falta credencial Service Account: {CRED_SA}")

    creds = Credentials.from_service_account_file(str(CRED_SA), scopes=SCOPES)
    sh = gspread.authorize(creds).open_by_key(SHEET_ID)
    ws = sh.worksheet(SHEET_TAB)

    candidatos = []
    for row in ws.get_all_values()[1:]:
        nombre = row[3].strip() if len(row) > 3 else ""
        correo = ""
        if len(row) > 4 and (row[4] or "").strip():
            correo = row[4].strip().lower()
        elif len(row) > 7 and (row[7] or "").strip():
            correo = row[7].strip().lower()
        if nombre and correo:
            candidatos.append((nombre, correo))
    return candidatos


def mejor_match(nombre_certificado, candidatos):
    """Devuelve (nombre_bd, correo, score, ambiguo) del mejor candidato en la pestaña General."""
    puntuados = sorted(
        ((similitud(nombre_certificado, nombre_bd), nombre_bd, correo) for nombre_bd, correo in candidatos),
        key=lambda t: t[0],
        reverse=True,
    )
    if not puntuados:
        return "", "", 0.0, False
    mejor_score, mejor_nombre, mejor_correo = puntuados[0]
    ambiguo = len(puntuados) > 1 and (mejor_score - puntuados[1][0]) < 0.03 and mejor_score < 0.98
    return mejor_nombre, mejor_correo, round(mejor_score, 3), ambiguo


def accion_emparejar(linea):
    if not RUTA_TEXTO.exists():
        raise FileNotFoundError(f"Falta {RUTA_TEXTO} — corre primero --dividir")

    with open(RUTA_TEXTO, encoding="utf-8-sig", newline="") as f:
        filas = list(csv.DictReader(f))

    print(f"[*] Conectando a la pestaña '{SHEET_TAB}' de la BD-Mujeres ROFÉ...")
    candidatos = cargar_general_sheet()
    print(f"[OK] {len(candidatos)} personas con nombre+correo en la BD")

    resultados = []
    n_revisar = 0
    for fila in filas:
        pagina = int(fila["pagina"])
        lineas_texto = (fila["texto"] or "").splitlines()
        nombre_cert = lineas_texto[linea].strip() if linea < len(lineas_texto) else ""
        nombre_cert = reconstruir_texto_espaciado(nombre_cert)

        nombre_bd, correo, score, ambiguo = mejor_match(nombre_cert, candidatos) if nombre_cert else ("", "", 0.0, False)
        revisar = "SI" if (not nombre_cert or not correo or score < UMBRAL_OK or ambiguo) else ""
        if revisar:
            n_revisar += 1

        resultados.append({
            "pagina": pagina,
            "archivo_pdf": f"pagina_{pagina:02d}.pdf",
            "nombre_certificado": nombre_cert,
            "nombre_bd": nombre_bd,
            "correo": correo,
            "score": score,
            "revisar": revisar,
        })

    with open(RUTA_MATCHES, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pagina", "archivo_pdf", "nombre_certificado", "nombre_bd", "correo", "score", "revisar"])
        w.writeheader()
        w.writerows(resultados)

    print(f"[OK] {len(resultados)} filas escritas en {RUTA_MATCHES}")
    print(f"  {len(resultados) - n_revisar} con match confiable | {n_revisar} para revisar a mano")
    if n_revisar:
        print(f"  Abre {RUTA_MATCHES} en Excel y corrige las filas con revisar=SI antes de enviar.")


# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="Divide certificados PDF y los cruza con la BD-Mujeres ROFÉ")
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument("--dividir", metavar="PDF", help="Separa el PDF en páginas individuales y extrae texto")
    g.add_argument("--emparejar", action="store_true", help="Cruza el nombre de cada página con la BD (usa --linea)")
    parser.add_argument("--linea", type=int, help="Índice de línea (0-based) donde está el nombre, requerido con --emparejar")
    args = parser.parse_args()

    if args.dividir:
        accion_dividir(args.dividir)
    elif args.emparejar:
        if args.linea is None:
            parser.error("--emparejar requiere --linea N (mira la salida de --dividir)")
        accion_emparejar(args.linea)


if __name__ == "__main__":
    main()
