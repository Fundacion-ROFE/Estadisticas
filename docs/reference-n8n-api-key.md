# n8n API Key — Fundación ROFÉ

> **CONFIDENCIAL**: Mantener seguro. No subir a GitHub.

## API Key (JWT Token)

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJjOTk3NTEwNC1iNzU3LTRhNTEtYWQ0Yi0wNDYxZDFkMzI1MTQiLCJpc3MiOiJuOG4iLCJhdWQiOiJwdWJsaWMtYXBpIiwianRpIjoiMGEwNGIyZjEtMmQwMy00MTEzLTkwNDUtMDgxMGQyYmFhZmMyIiwiaWF0IjoxNzgzOTk4MjkyLCJleHAiOjE3ODY1MTA4MDB9.THDbwd0NHXvB5H1mCZnqL3gHBLwYcMhuX4cxyTSUSOI
```

## Detalles

| Campo | Valor |
|---|---|
| **Generada** | 2026-07-13 |
| **Expira** | 2026-07-20 |
| **Endpoint** | http://localhost:5678/api/v1 |
| **Usuario** | Samuel David Rojas Monroy (EstudiantesJC) |
| **Tipo** | JWT |

## Uso en scripts

```python
import urllib.request

N8N_API_KEY = "eyJhbGc..."  # Token arriba
headers = {
    "X-N8N-API-KEY": N8N_API_KEY,
    "Content-Type": "application/json"
}

req = urllib.request.Request(
    "http://localhost:5678/api/v1/workflows",
    method="POST",
    headers=headers,
    data=json.dumps(workflow_data).encode("utf-8")
)
```

## Endpoints principales

- `POST /workflows` — crear workflow
- `PATCH /workflows/{id}` — actualizar/activar workflow
- `GET /workflows` — listar todos los workflows
- `DELETE /workflows/{id}` — eliminar workflow

## Renovar si expira

Si llega 2026-07-20 sin renovar:

1. Abre n8n: http://localhost:5678
2. Click **usuario** (arriba derecha)
3. Click **"Settings"** → **"API"**
4. Click **"Regenerate"**
5. Copia la nueva clave
6. Actualiza este archivo

## Scripts que usan esta clave

- `scripts/crear_workflow_n8n_api.py` — crea `asistencia-zoom-diario`
- Cualquier script futuro que modifique workflows automáticamente
