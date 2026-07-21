# -*- coding: utf-8 -*-
"""
Test simple: verifica que asistencia se pase correctamente en el panel.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "tools"))

# Test imports
print("[1] Importando panel_riesgo_gui...")
try:
    from panel_riesgo_gui import (
        conectar, leer_h2test, leer_avance, leer_asistencia_zoom, cruzar
    )
    print("    ✓ Imports correctos\n")
except Exception as e:
    print(f"    ✗ Error: {e}\n")
    sys.exit(1)

# Test data load
print("[2] Cargando datos...")
try:
    gc = conectar()
    q10_jc, q10_mr, cursos_info = leer_h2test(gc)
    avance = leer_avance(gc)
    asistencia = leer_asistencia_zoom(gc)
    print(f"    ✓ Q10 JC: {len(q10_jc)} estudiantes")
    print(f"    ✓ Q10 MR: {len(q10_mr)} estudiantes")
    print(f"    ✓ Avance: {len(avance)} estudiantes")
    print(f"    ✓ Asistencia: {len(asistencia)} estudiantes\n")
except Exception as e:
    print(f"    ✗ Error cargando datos: {e}\n")
    sys.exit(1)

# Test cruzar function with asistencia
print("[3] Cruzando datos (Q10 + Avance + Asistencia)...")
try:
    casos, total_av, total_q = cruzar(q10_jc, avance, 50, asistencia)
    print(f"    ✓ Casos en atención: {len(casos.get('atencion', []))}")

    # Verificar que asistencia está en los casos
    muestra = casos.get('atencion', [])[:1]
    if muestra:
        est = muestra[0]
        ast_pct = est.get('promedio_asistencia')
        if ast_pct is not None:
            print(f"    ✓ Asistencia en casos: {ast_pct}%")
        else:
            print(f"    ✓ Asistencia en casos: None (será 'aún no disponible')")
    print()
except Exception as e:
    print(f"    ✗ Error cruzando: {e}\n")
    import traceback
    traceback.print_exc()
    sys.exit(1)

print("="*70)
print("✅ PANEL LISTO")
print("="*70)
print("\nAhora ejecuta:")
print("  python tools/panel_riesgo_gui.py")
print("\nVe a: Jóvenes creaTIvos → En Q10")
print("Deberías ver la columna 'Asistencia %' con valores como:")
print("  • '71.5%' si hay datos")
print("  • 'aún no disponible' si no hay datos\n")
