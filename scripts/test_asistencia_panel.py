# -*- coding: utf-8 -*-
"""
Test: Verifica que el panel puede leer correctamente asistencia_promedio.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

try:
    from panel_riesgo_gui import conectar, leer_asistencia_zoom
    print("[1] Panel functions importadas OK\n")
except Exception as e:
    print(f"[ERROR] No se pudo importar: {e}")
    sys.exit(1)

print("[2] Leyendo asistencia desde Supabase...")
try:
    gc = conectar()
    asistencia = leer_asistencia_zoom(gc)
    print(f"    ✓ {len(asistencia)} estudiantes con asistencia\n")
except Exception as e:
    print(f"    ✗ Error: {e}\n")
    sys.exit(1)

print("[3] Ejemplos de datos leídos:\n")
for email, data in list(asistencia.items())[:3]:
    print(f"    {email}")
    print(f"      • Promedio: {data.get('promedio_pct')}%")
    print(f"      • Registros: {data.get('n_registros')}")
    if data.get('cursos'):
        print(f"      • Cursos: {list(data['cursos'].keys())[:2]}...")
    print()

print("="*80)
print("✅ TODO OK - Panel leerá correctamente la asistencia")
print("="*80 + "\n")

print("Ahora ejecuta:")
print("  python tools/panel_riesgo_gui.py\n")
print("Y verás la columna 'Asistencia %' con valores reales.\n")
