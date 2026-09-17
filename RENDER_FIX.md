# Finora — Render fix v0.4.1

Esta variante usa el runtime Python nativo de Render, no Docker.

## En Render

Si ya tienes creado el Web Service:
1. Settings.
2. Runtime: Python.
3. Build Command:
   `pip install -r requirements.txt`
4. Start Command:
   `uvicorn server:app --host 0.0.0.0 --port $PORT`
5. Health Check Path:
   `/api/health`
6. Guarda y vuelve a desplegar.

Si vas a crear un Blueprint nuevo, conecta este repositorio/versión y Render leerá `render.yaml`.

## Variables

Para que la app ARRANQUE no necesitas las APIs externas todavía.

Puedes dejar vacías:
- TWELVE_DATA_API_KEY
- COINGECKO_API_KEY
- ALPHAVANTAGE_API_KEY
- STRIPE_SECRET_KEY
- STRIPE_WEBHOOK_SECRET
- STRIPE_PRICE_ID

Solo añade `APP_BASE_URL` con la URL HTTPS de Render después del primer deploy.

## Importante sobre SQLite

Esta versión usa `/tmp/finora.db` para que el servicio pueda arrancar en Free.
Ese archivo NO es almacenamiento persistente. Los datos pueden perderse al reiniciar/redeployar.

Antes de usar usuarios reales, migrar la base de datos a PostgreSQL (por ejemplo Supabase) y configurar backups.

## Si vuelve a fallar

En Render, abre el deploy y copia las líneas desde:
`==> Running build command ...`
hasta el primer mensaje de error.

No copies claves API ni secretos.
