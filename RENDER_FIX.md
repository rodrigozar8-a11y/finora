# Finora v0.4.2 — Render fix

El build anterior completó correctamente. El fallo estaba en el arranque:

`bash: uvicorn: command not found`

Aunque `uvicorn` se instaló correctamente, el ejecutable no estaba disponible en el PATH de la fase de arranque.
La solución es ejecutar Uvicorn como módulo del mismo intérprete de Python.

## Render

Settings:

Runtime:
`Python`

Build Command:
`python -m pip install -r requirements.txt`

Start Command:
`python -m uvicorn server:app --host 0.0.0.0 --port $PORT`

Health Check Path:
`/api/health`

Root Directory:
vacío, si `requirements.txt` y `server.py` están en la raíz del repo.

No necesitas configurar ninguna API key para que la app arranque.

## Qué NO es el problema

Los mensajes:
- Using Erlang...
- Using Elixir...
- Using Poetry...

no son el error que ha detenido el deploy. El build terminó con `Build successful`.

## Deploy

Sube los archivos de este ZIP al repositorio y haz commit/push. Después Render debería lanzar un nuevo deploy automáticamente
si el auto-deploy está activo; si no, usa Manual Deploy → Deploy latest commit.

Si vuelve a fallar, copia desde `==> Running 'python -m uvicorn...` hasta el primer `ERROR`.

## Nota sobre base de datos

Esta beta usa SQLite en `/tmp`, por lo que NO es persistente. Es suficiente para arrancar/probar la app, pero no para usuarios reales.
El siguiente paso de producción será PostgreSQL (por ejemplo Supabase) + migraciones + backups.
