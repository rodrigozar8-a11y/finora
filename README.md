# Finora — Real App Starter v0.3

Esta versión deja de ser una página estática: tiene servidor FastAPI, cuentas, sesiones, base SQLite,
carteras por usuario, seguimiento de mercados, noticias, Premium y conectores para datos externos.

## 1. Arranque rápido en local

### Windows / macOS / Linux

1. Copia `.env.example` como `.env`.
2. Instala Python 3.12+.
3. Ejecuta:
   `python -m venv .venv`
   Windows: `.venv\Scripts\activate`
   macOS/Linux: `source .venv/bin/activate`
4. `pip install -r requirements.txt`
5. `uvicorn server:app --reload`
6. Abre `http://127.0.0.1:8000`

También puedes usar Docker:
`docker compose up --build`

## 2. Qué funciona ya

- Registro e inicio de sesión.
- Contraseñas almacenadas con PBKDF2-HMAC-SHA256 + salt aleatorio.
- Sesiones con token aleatorio almacenado en la base de datos.
- Carteras separadas por usuario.
- Posiciones manuales con ticker, unidades y precio medio.
- Valor actual y rentabilidad.
- Lista de seguimiento.
- Buscador de instrumentos.
- Endpoint de cotizaciones.
- Endpoint de noticias.
- Capa Premium.
- Inicio de checkout de Stripe.
- Webhook de Stripe.
- SQLite para arrancar sin infraestructura.
- Docker para desplegar el mismo proyecto.

## 3. Datos de mercado

Twelve Data está integrado como proveedor principal para acciones/ETFs y otros instrumentos compatibles.
Su plan gratuito actual sirve para desarrollo/no-display y ofrece cotizaciones en tiempo real para ciertos
mercados, pero su documentación distingue expresamente el acceso de uso interno del acceso de display externo.
Para una aplicación comercial donde los clientes vean las cotizaciones hay que contratar un plan/licencia
que lo permita.

CoinGecko dispone de un plan Demo gratuito para prototipos de cripto, con límites de uso y atribución;
sus planes con licencia comercial son de pago.

IMPORTANTE: no ocultes una clave API en el frontend. Las claves se mantienen en `.env` del servidor.

## 4. Noticias

La app tiene un adaptador para Alpha Vantage `NEWS_SENTIMENT`.
Devuelve título, fuente, URL, fecha de publicación y resumen breve cuando el proveedor lo entrega.
La app no copia el artículo completo.

Antes de comercializar el producto, revisa los términos y derechos de redistribución/display del proveedor
de noticias elegido.

## 5. Stripe Premium

Define:
- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `STRIPE_PRICE_ID`
- `APP_BASE_URL`

Luego usa el botón Premium de la interfaz. El servidor crea el Checkout Session y el webhook activa
Premium en la cuenta. Para producción debes usar HTTPS y configurar el endpoint webhook de Stripe.

## 6. Datos gratuitos: qué sí y qué no

Hay fuentes gratuitas para desarrollo, uso personal o prototipos:
- Twelve Data Basic: créditos diarios y acceso a determinados datos; su plan gratuito no concede external display.
- CoinGecko Demo: gratuita, con 10.000 créditos/mes y frescura publicada "desde 60 s"; la licencia comercial aparece en planes de pago.

Por tanto, para una beta privada de pocos usuarios puedes desarrollar sin pagar mucho, pero para mostrar datos
financieros licenciados públicamente a clientes necesitas comprobar y contratar los derechos correspondientes.

## 7. Próximos pasos de producción

- Migrar SQLite a PostgreSQL.
- HTTPS + dominio.
- Sistema de recuperación de contraseña y verificación de email.
- Rate limiting.
- 2FA.
- Logs/monitorización.
- Backups.
- Política de privacidad/RGPD y términos.
- Revisión legal sobre datos de mercado, noticias y recomendaciones de inversión.
- Sustituir los adaptadores de ejemplo por un proveedor con derechos comerciales adecuados.
- App móvil (React Native/Expo).
- Mejorar el motor de análisis, histórico, alertas y educación.


## v0.4 — PWA / móvil / despliegue

- PWA instalable: manifest + service worker + icono.
- `render.yaml` para despliegue rápido.
- `DEPLOYMENT.md` con pasos de publicación y acceso móvil.
- La app web sigue usando el backend FastAPI.
