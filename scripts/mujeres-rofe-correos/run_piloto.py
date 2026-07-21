#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script seguro para enviar piloto sin exponer credenciales en logs
"""
import os
import getpass
import subprocess
import sys

def main():
    print("=" * 60)
    print("PRUEBA PILOTO - MUJERES ROFE")
    print("=" * 60)
    print()

    campana = sys.argv[1] if len(sys.argv) > 1 else "campanas/mr_ultimos_3_anios.json"
    correo_piloto = sys.argv[2] if len(sys.argv) > 2 else "samueldavidvida@gmail.com"
    cuenta = input("Cuenta SMTP [mujeres.rofe@tocaunavida.org]: ").strip() or "mujeres.rofe@tocaunavida.org"
    password = getpass.getpass("Contraseña app Google (16 dígitos): ")

    os.environ["SMTP_USER"] = cuenta
    os.environ["SMTP_PASSWORD"] = password
    os.environ["SMTP_HOST"] = "smtp.gmail.com"

    print()
    print(f"[*] Enviando piloto a {correo_piloto} desde {cuenta}...")
    print()

    result = subprocess.run(
        [sys.executable, "enviar_campana.py", campana, "--piloto", correo_piloto],
        env=os.environ.copy()
    )

    print()
    if result.returncode == 0:
        print("[OK] Piloto enviado exitosamente.")
        print(f"Revisa: {correo_piloto} (bandeja + spam)")
    else:
        print("[ERROR] Fallo en el envio. Revisa el error arriba.")
        sys.exit(1)

if __name__ == "__main__":
    main()
