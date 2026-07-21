"""
Consentimiento OAuth de YouTube (una sola vez) para comunicaciones@tocaunavida.org.
Abre el navegador local, el usuario inicia sesion y acepta el permiso de subir videos.
Guarda el refresh_token en scripts/zoom-youtube/.env para que el resto del pipeline
(subir_yt_grabacion.py) lo use sin volver a pedir login.
"""
import os
import truststore
truststore.inject_into_ssl()

from google_auth_oauthlib.flow import InstalledAppFlow

ENV_PATH = os.path.join(os.path.dirname(__file__), ".env")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube",
    # Drive: subir grabaciones NOVA (MP4 + transcripcion) a la carpeta compartida.
    # La service account no sirve aqui (sin cuota de almacenamiento en My Drive),
    # por eso los archivos se crean como comunicaciones@ via este mismo OAuth.
    "https://www.googleapis.com/auth/drive",
]


def cargar_env():
    vals = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    vals[k.strip()] = v.strip()
    return vals


def guardar_refresh_token(refresh_token):
    vals = cargar_env()
    vals["YT_REFRESH_TOKEN"] = refresh_token
    with open(ENV_PATH, "w", encoding="utf-8") as f:
        for k, v in vals.items():
            f.write(f"{k}={v}\n")


def main():
    vals = cargar_env()
    client_id = vals["YT_OAUTH_CLIENT_ID"]
    client_secret = vals["YT_OAUTH_CLIENT_SECRET"]

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    print("Abriendo navegador para el consentimiento de YouTube...")
    print("Inicia sesion con comunicaciones@tocaunavida.org y acepta el permiso.")
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")

    if not creds.refresh_token:
        print("[ERROR] No se recibio refresh_token. Reintenta forzando prompt=consent")
        print("        (puede pasar si ya habias dado consentimiento antes sin access_type=offline).")
        return

    guardar_refresh_token(creds.refresh_token)
    print("[OK] refresh_token guardado en scripts/zoom-youtube/.env")


if __name__ == "__main__":
    main()
