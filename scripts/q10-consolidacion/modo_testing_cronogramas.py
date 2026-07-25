"""Activa o revierte el modo testing (cada 2h) en los workflows del pipeline de datos.

Uso:
    python modo_testing_cronogramas.py activar
    python modo_testing_cronogramas.py revertir

Contexto: testeo fuerte del 2026-07-25/26 tras el corte nocturno del 24-jul. Solo toca el
nodo Schedule Trigger de cada workflow (cronExpression), nada mas. El backup del JSON
original vive en tools/backups/n8n_workflows_pre_testing/<id>.json (ya capturado antes de
cualquier cambio), asi que "revertir" lee el cron original de ahi.
"""
import json
import os
import sys
import urllib.request

RAIZ = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RUTA_ENV = os.path.join(RAIZ, "scripts", "q10-consolidacion", ".env")
RUTA_BACKUPS = os.path.join(RAIZ, "tools", "backups", "n8n_workflows_pre_testing")
BASE_URL = "http://localhost:5678/api/v1"

# workflow_id -> (nombre del nodo Schedule Trigger, cron de testing)
WORKFLOWS_TESTING = {
    "DFPiF1RtD58FhGoZ": ("Schedule Diario 21:30", "0 */2 * * *"),   # emoflow-ingresos-diario
    "GFGKNmNkQQ430iWP": ("Cron diario (8:15)", "0 */2 * * *"),      # datos-respaldo-diario
    "LgkDbNPERYgKMrYj": ("Schedule Diario 9:30", "0 */2 * * *"),    # mr-actualizacion-datos
    "N7ouRIdgbomCGNxa": ("Cron diario (6:30)", "0 */2 * * *"),      # correos-rebotes-diario
    "en36vJCa8vOCRViz": ("Cron diario (8:00)", "0 */2 * * *"),      # panel-verificacion-diaria
    # q10-sync-supabase ya corre cada 2h (30 17,19,21,23,1,3,5,7 * * *) -> no se toca
}


def cargar_api_key() -> str:
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("N8N_API_KEY="):
                return linea.strip().split("=", 1)[1]
    raise SystemExit("N8N_API_KEY no encontrada en " + RUTA_ENV)


def notificar_telegram(mensaje: str) -> None:
    token = None
    with open(RUTA_ENV, encoding="utf-8") as f:
        for linea in f:
            if linea.startswith("TELEGRAM_BOT_TOKEN="):
                token = linea.strip().split("=", 1)[1]
                break
    if not token:
        return
    chat_id = "8141703221"
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = json.dumps({"chat_id": chat_id, "text": mensaje}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=15)
    except Exception:
        pass


def api_get(path: str, api_key: str) -> dict:
    req = urllib.request.Request(BASE_URL + path, headers={"X-N8N-API-KEY": api_key})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def api_put(path: str, api_key: str, body: dict) -> dict:
    data = json.dumps(body).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        method="PUT",
        headers={"X-N8N-API-KEY": api_key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))


def construir_body_minimo(wf: dict) -> dict:
    return {
        "name": wf["name"],
        "nodes": wf["nodes"],
        "connections": wf["connections"],
        "settings": wf["settings"],
        "staticData": wf.get("staticData") or {},
    }


def aplicar_cron(node_name: str, cron_expr: str, nodes: list) -> bool:
    for n in nodes:
        if n.get("name") == node_name:
            n["parameters"]["rule"] = {"interval": [{"field": "cronExpression", "expression": cron_expr}]}
            return True
    return False


def activar(api_key: str) -> None:
    for wf_id, (node_name, test_cron) in WORKFLOWS_TESTING.items():
        wf = api_get(f"/workflows/{wf_id}", api_key)
        if "data" in wf:
            wf = wf["data"]
        ok = aplicar_cron(node_name, test_cron, wf["nodes"])
        if not ok:
            print(f"AVISO: nodo '{node_name}' no encontrado en {wf_id} ({wf.get('name')})")
            continue
        body = construir_body_minimo(wf)
        api_put(f"/workflows/{wf_id}", api_key, body)
        print(f"[OK] {wf.get('name')} ({wf_id}) -> cron testing {test_cron}")


def revertir(api_key: str) -> None:
    for wf_id, (node_name, _test_cron) in WORKFLOWS_TESTING.items():
        ruta_backup = os.path.join(RUTA_BACKUPS, f"{wf_id}.json")
        if not os.path.isfile(ruta_backup):
            print(f"AVISO: sin backup para {wf_id}, se omite")
            continue
        with open(ruta_backup, encoding="utf-8") as f:
            backup = json.load(f)
        rule_original = None
        for n in backup["nodes"]:
            if n.get("name") == node_name:
                rule_original = n["parameters"]["rule"]
                break
        if rule_original is None:
            print(f"AVISO: nodo '{node_name}' no encontrado en backup de {wf_id}")
            continue
        wf = api_get(f"/workflows/{wf_id}", api_key)
        if "data" in wf:
            wf = wf["data"]
        for n in wf["nodes"]:
            if n.get("name") == node_name:
                n["parameters"]["rule"] = rule_original
                break
        body = construir_body_minimo(wf)
        api_put(f"/workflows/{wf_id}", api_key, body)
        print(f"[OK] {wf.get('name')} ({wf_id}) -> cron original restaurado ({rule_original})")


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("activar", "revertir"):
        print("Uso: python modo_testing_cronogramas.py [activar|revertir]")
        sys.exit(1)
    api_key = cargar_api_key()
    if sys.argv[1] == "activar":
        activar(api_key)
        notificar_telegram("Modo testing activado: q10-sync-supabase + 5 workflows corriendo cada 2h hasta el domingo en la noche.")
    else:
        revertir(api_key)
        notificar_telegram("Modo testing terminado: cronogramas revertidos a su cadencia normal. Listo para el lunes.")
    print("RESUMEN: estado=exito")


if __name__ == "__main__":
    main()
