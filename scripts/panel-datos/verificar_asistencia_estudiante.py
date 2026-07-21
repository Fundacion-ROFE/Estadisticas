# -*- coding: utf-8 -*-
"""
Obtiene ejemplo de estudiante real con asistencia Zoom de Supabase.
"""
import json
import urllib.request

url = "https://kbxptoowtnteflhrfwid.supabase.co"
key = "sb_publishable_2i9Sq2dwGh6euVvDwExkZg_Rn0_jp0L"

print("\n" + "="*80)
print("EJEMPLO: Estudiante real con asistencia Zoom")
print("="*80 + "\n")

try:
    # Obtener primeros registros (sin select para ver si el endpoint responde)
    req = urllib.request.Request(
        f"{url}/rest/v1/asistencia_zoom?limit=100",
        method="GET",
        headers={
            "apikey": key,
            "Authorization": f"Bearer {key}",
        }
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        datos = json.loads(resp.read().decode("utf-8"))

    if not datos:
        print("[ERROR] No hay datos en asistencia_zoom")
        exit(1)

    # Agrupar por email y calcular promedios
    por_email = {}
    for row in datos:
        email = row.get("email", "").lower()
        if not email:
            continue

        pct_str = row.get("porcentaje_asistencia", "0%")
        pct = float(pct_str.replace("%", "").strip() or 0)

        inst_str = row.get("instancias", "0/3")
        try:
            inst = int(inst_str.split("/")[0])
        except:
            inst = 0

        if email not in por_email:
            por_email[email] = {
                "nombre": row.get("nombre", ""),
                "apellido": row.get("apellido", ""),
                "registros": []
            }
        por_email[email]["registros"].append({
            "curso": row.get("curso", ""),
            "fecha": row.get("fecha", ""),
            "pct": pct,
            "inst": inst,
        })

    # Calcular promedios
    estudiantes = []
    for email, datos_est in por_email.items():
        n = len(datos_est["registros"])
        prom_pct = sum(r["pct"] for r in datos_est["registros"]) / n if n > 0 else 0
        prom_inst = sum(r["inst"] for r in datos_est["registros"]) / n if n > 0 else 0

        estudiantes.append({
            "email": email,
            "nombre": datos_est["nombre"],
            "apellido": datos_est["apellido"],
            "promedio_asistencia": round(prom_pct, 1),
            "promedio_momentos": round(prom_inst, 2),
            "clases": n,
            "registros": datos_est["registros"],
        })

    # Mostrar 3 ejemplos
    for i, est in enumerate(estudiantes[:3], 1):
        print(f"[{i}] {est['nombre']} {est['apellido']}")
        print(f"    Email: {est['email']}")
        print(f"    Promedio Asistencia: {est['promedio_asistencia']}%")
        print(f"    Promedio Momentos: {est['promedio_momentos']}/3")
        print(f"    Clases asistidas: {est['clases']}\n")

        print(f"    Detalles por clase:")
        for reg in est['registros'][:5]:
            print(f"      - {reg['curso']} ({reg['fecha']}): {reg['pct']}%, {reg['inst']}/3 momentos")
        if len(est['registros']) > 5:
            print(f"      ... y {len(est['registros']) - 5} clases mas")
        print()

    print("="*80)
    print(f"Total: {len(estudiantes)} estudiantes en Supabase")
    print("="*80 + "\n")

    print("INSTRUCCIONES PARA VERIFICAR EN PANEL DE RIESGO:")
    print("1. Abre el Panel de Riesgo (tools/panel_riesgo_gui.py)")
    print("2. Presiona 'Actualizar datos'")
    print("3. Ve a tab 'ATENCIÓN'")
    print("4. Busca en la columna 'Email' uno de estos:")
    for est in estudiantes[:3]:
        print(f"   - {est['email']}")
    print("5. Verifica que aparezca el 'Asistencia %' en la tabla")
    print("6. Doble-click en el estudiante para ver popup con detalles de faltas")

except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
