---
name: protect-creds
enabled: true
event: file
action: block
conditions:
  - field: file_path
    operator: regex_match
    pattern: (\.env$|credenciales_service_account\.json)
---

BLOQUEADO: Archivo de credenciales protegido — no editar vía Claude.

`.env` y `credenciales_service_account.json` contienen secretos que no deben aparecer
en el contexto de conversación. Editar manualmente en el editor del sistema operativo.

Si necesitas ver qué variables existen: leer solo los nombres de las claves, nunca los valores.
