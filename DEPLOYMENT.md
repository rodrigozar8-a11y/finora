# Publicar Finora y abrirla desde el móvil

## Opción rápida: Render

1. Crea un repositorio privado/público en GitHub y sube todo el contenido de esta carpeta.
2. En Render: New → Blueprint.
3. Selecciona el repositorio.
4. Render leerá `render.yaml`.
5. Define:
   - `APP_BASE_URL` con la URL HTTPS que te dé Render.
   - `TWELVE_DATA_API_KEY`
   - `COINGECKO_API_KEY`
   - `ALPHAVANTAGE_API_KEY`
   - Las variables de Stripe solo cuando quieras cobrar Premium.
6. Cuando termine el deploy, Render dará una URL `https://...onrender.com`.
7. Desde tu móvil abre esa URL.

### Instalar como app en el móvil

En Android/Chrome: menú del navegador → "Instalar aplicación" / "Añadir a pantalla de inicio".

En iPhone/Safari: Compartir → "Añadir a pantalla de inicio".

Finora utiliza `manifest.webmanifest` y un service worker, por lo que está preparada como PWA.

## Importante para una base de datos de producción

Esta versión arranca con SQLite para que sea fácil de probar.
En un servicio efímero, SQLite no debe considerarse una base de datos de producción a largo plazo.

La evolución recomendada es:
- PostgreSQL gestionado (por ejemplo, Supabase)
- migraciones
- backups
- monitorización
- 2FA y recuperación de cuenta

## Uso desde tu ordenador sin publicar

Arranca:
`uvicorn server:app --host 0.0.0.0 --port 8000`

Busca la IP local de tu ordenador (por ejemplo 192.168.1.25) y, conectado a la misma Wi-Fi,
abre en el móvil:
`http://192.168.1.25:8000`

Para instalar la PWA en el móvil desde una dirección HTTP local puede haber limitaciones;
para la experiencia completa de instalación y service worker se recomienda HTTPS en el despliegue público.

## Datos de mercado y noticias

Las claves se quedan en el backend. Nunca las metas en el JavaScript del navegador.

Antes de un lanzamiento comercial:
- revisa la licencia de display de los datos de cada proveedor;
- revisa la licencia de noticias;
- registra la fuente, timestamp y tipo de dato;
- trata correctamente NAV de fondos frente a precios intradía;
- revisa RGPD, cookies y términos de uso.
