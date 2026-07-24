# OBSOLETO (P0 2026-07-24): diagnóstico de un solo uso; credenciales movidas a entorno.
# -*- coding: utf-8 -*-
"""
Verifica que los datos de asistencia se relacionen correctamente con Q10.
Compara emails y muestra ejemplos reales.
"""
import os
import io
import sys
import json
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

try:
    import truststore
    truststore.inject_into_ssl()
except ImportError:
    pass

import gspread
from google.oauth2.service_account import Credentials
import urllib.request

BASE = Path(__file__).resolve().parents[2]
CRED = BASE / "scripts" / "q10-consolidacion" / "credenciales_service_account.json"

# Importar funciones del panel
sys.path.insert(0, str(BASE / "tools"))
try:
    from panel_riesgo_gui import leer_h2test, leer_asistencia_zoom, conectar
    USAR_PANEL_FUNCTIONS = True
except:
    USAR_PANEL_FUNCTIONS = False

def main():
    print("\n" + "="*100)
    print("VERIFICACIÓN: Relación de asistencia Zoom con datos Q10")
    print("="*100 + "\n")

    # ─── Leer Q10 desde h2test ────────────────────────────────────────────
    print("[1/3] Leyendo datos de h2test (Q10)...")

    try:
        if USAR_PANEL_FUNCTIONS:
            gc = conectar()
            q10_jc, q10_mr, _ = leer_h2test(gc)
            asistencia = leer_asistencia_zoom(gc)
        else:
            raise Exception("Panel functions not available")
    except Exception as e:
        print(f"   ⚠️  Usando método alternativo... ({e})\n")
        creds = Credentials.from_service_account_file(str(CRED), scopes=["https://www.googleapis.com/auth/spreadsheets"])
        gc = gspread.authorize(creds)

        # Leer h2test
        try:
            h2test_sheet = gc.open_by_key("1q4VNn4ltqVEMsOjo-c2ZbsbW3VIt-XomPgXeLSN_LTs")
            h2test_valores = h2test_sheet.worksheet("h2test").get_all_values()
        except:
            print("   ✗ No se pudo leer h2test")
            return 1

        # Parsear h2test - buscar en los primeros 20 headers
        headers = h2test_valores[0]
        idx_email = None
        idx_nombre = None
        for i, h in enumerate(headers):
            h_lower = h.lower()
            if "correo" in h_lower or "email" in h_lower:
                idx_email = i
            if "nombre" in h_lower and "apellido" not in h_lower:
                idx_nombre = i

        if idx_email is None or idx_nombre is None:
            print(f"   ✗ Headers no encontrados. Headers: {headers[:10]}")
            return 1

        q10_jc = {}
        for fila in h2test_valores[1:]:
            if len(fila) > max(idx_email, idx_nombre):
                email = fila[idx_email].strip().lower() if fila[idx_email] else ""
                nombre = fila[idx_nombre].strip() if fila[idx_nombre] else ""
                if email and nombre:
                    q10_jc[email] = {"nombre": nombre}

        # Leer asistencia
        url = os.environ.get("SUPABASE_URL", "")
        key = os.environ.get("SUPABASE_PUBLISHABLE_KEY") or os.environ.get("SUPABASE_ANON_KEY", "")
        try:
            req = urllib.request.Request(
                f"{url}/rest/v1/asistencia_zoom?select=email,porcentaje_asistencia&limit=1000",
                method="GET",
                headers={"apikey": key, "Authorization": f"Bearer {key}"}
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                asistencia_data = json.loads(resp.read().decode("utf-8") or "[]")
        except:
            asistencia_data = []

        asistencia = {}
        for row in asistencia_data:
            email = (row.get("email") or "").lower()
            if email:
                pct_str = row.get("porcentaje_asistencia", "0%")
                pct = float(pct_str.replace("%", "").strip() or 0)
                if email not in asistencia:
                    asistencia[email] = {"promedio_pct": pct, "registros": []}
                asistencia[email]["registros"].append(pct)

    print(f"   ✓ {len(q10_jc)} estudiantes en Q10\n")
    print("[2/3] Leyendo asistencia_zoom desde Supabase...")
    print(f"   ✓ {len(asistencia)} estudiantes con asistencia en Supabase\n")

    # ─── Análisis de relación ─────────────────────────────────────────────
    print("[3/3] Analizando relación...\n")

    # Estudiantes en ambas bases
    en_ambas = set(q10_jc.keys()) & set(asistencia.keys())
    solo_q10 = set(q10_jc.keys()) - set(asistencia.keys())
    solo_asistencia = set(asistencia.keys()) - set(q10_jc.keys())

    print(f"📊 RESUMEN DE COBERTURA:")
    print(f"   • En Q10 y con asistencia:     {len(en_ambas):3d} ✅")
    print(f"   • Solo en Q10 (sin asistencia): {len(solo_q10):3d} ⚠️")
    print(f"   • Solo asistencia (no en Q10):  {len(solo_asistencia):3d} ⚠️")
    print(f"   • Total Q10: {len(q10_jc)}")
    if len(q10_jc) > 0:
        print(f"   • Cobertura: {len(en_ambas)/len(q10_jc)*100:.1f}%\n")

    # Ejemplos con asistencia
    if en_ambas:
        print("📋 EJEMPLOS CON ASISTENCIA (para verificar relación correcta):\n")
        ejemplos = sorted(list(en_ambas))[:5]

        for i, email in enumerate(ejemplos, 1):
            q10_info = q10_jc[email]
            asist_info = asistencia[email]
            registros = asist_info.get("registros", [])
            if registros:
                prom = sum(registros) / len(registros)
                print(f"[{i}] {q10_info['nombre']}")
                print(f"    Email: {email}")
                print(f"    Promedio asistencia: {prom:.1f}%")
                print(f"    # registros: {len(registros)}")
                if len(registros) > 0:
                    print(f"    Rango: {min(registros):.0f}% — {max(registros):.0f}%")
                print()

        # Sin asistencia
        if solo_q10:
            print(f"⚠️  ESTUDIANTES SIN ASISTENCIA REGISTRADA ({len(solo_q10)} personas):\n")
            ejemplos_sin = sorted(list(solo_q10))[:5]
            for i, email in enumerate(ejemplos_sin, 1):
                q10_info = q10_jc[email]
                print(f"[{i}] {q10_info['nombre']} — {email}")
            if len(solo_q10) > 5:
                print(f"    ... y {len(solo_q10) - 5} más")
            print()

        print("="*100)
        print("✅ Verificación completada.")
        print("="*100 + "\n")

        print("CÓMO USAR EN PANEL:")
        print("1. Abre 'python tools/panel_riesgo_gui.py'")
        print("2. Ve al tab 'Jóvenes creaTIvos'")
        print("3. Selecciona vista 'En Q10'")
        print(f"4. Busca a '{q10_jc[ejemplos[0]]['nombre']}' (email: {ejemplos[0]}) en la tabla")
        print("5. Verifica que la columna 'Asistencia %' muestre el dato correcto (debe coincidir con el cálculo arriba)")
        print("\nOTRAS VISTAS DONDE APARECE 'Asistencia %':")
        print("• Tab 'Jóvenes creaTIvos' → vista 'match' → compara Q10, Manual y Asistencia")
        print("• Tab 'Jóvenes creaTIvos' → vista 'atencion' → detalle por curso con asistencia")
        print("• Tab 'Mujeres ROFÉ' → vista 'mujeres' → asistencia por estudiante MR")
        print("• Tab 'Diferencias' → vista 'ambas' → Q10 vs Manual vs Asistencia\n")
    else:
        print("⚠️  No hay datos para verificar. Asegúrate de que:")
        print("   1. El Sheet h2test tenga datos de Q10")
        print("   2. La tabla asistencia_zoom en Supabase tenga datos")
        print("   3. Los emails en ambas bases coincidan (mismo formato)\n")

    return 0

if __name__ == "__main__":
    sys.exit(main())
