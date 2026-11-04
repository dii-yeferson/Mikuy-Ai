# Mikuy

App web instalable (PWA) para **planificar, comprar y cocinar** comida peruana según tu presupuesto, con **Mikuy AI**, una asistente que cambia tu menú por texto o por voz.

- **Planificar:** menú semanal (desayuno, almuerzo, cena y snack opcional) ajustado a tu meta, dieta, alergias, condiciones y presupuesto.
- **Comprar:** lista consolidada con **precios aproximados por ciudad** (18 ciudades del Perú), lo que compras frente a lo que cocinas, y opción de compartir por WhatsApp.
- **Mikuy AI:** cambia platos, abarata el menú, ajusta el presupuesto, personas o dieta, da recetas y calcula tus calorías. Funciona con Groq y, sin clave, con un intérprete local.
- **313 recetas** peruanas con ingredientes, pasos, nutrientes, costo por porción y portada animada (las fotos reales se agregan después).
- **Cuenta y Premium:** registro, sesión segura y planes Gratis, Premium y Familia. El pago está **simulado**: la app genera un código de activación.

## Estructura

```text
backend/            API FastAPI + SQLAlchemy
  app/catalog/      ingredientes, precios por ciudad, recetas y fuentes
  app/services/     nutrición, planificador, compras, Mikuy AI, Premium
  app/routes/       endpoints /api/...
  tests/            pruebas (pytest)
frontend/           React + Vite + TypeScript (sin frameworks de UI)
  src/lib/          API, estado, sonidos y vibración (feel.ts)
  src/components/   hojas de vidrio, portadas animadas, recetas, Premium
  src/pages/        Hoy, Menú, Mikuy AI, Compras, Recetas, Ajustes
  public/           logo, fuente Nunito, manifest, service worker
assets/brand/       logos originales
```

## Ejecutar en tu computadora

Necesitas **Python 3.12+** y **Node 20+**. No hace falta instalar una base de datos: en local se usa SQLite.

**1. API (terminal 1)**

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate          # Windows  (en Mac/Linux: source .venv/bin/activate)
pip install -r requirements.txt -r requirements-dev.txt
copy .env.example .env          # Windows  (en Mac/Linux: cp .env.example .env)
uvicorn app.main:app --reload --port 8000
```

**2. App (terminal 2)**

```bash
cd frontend
npm install
npm run dev
```

Abre http://127.0.0.1:5173.

**Pruebas:** `cd backend` y luego `pytest`. **Compilar la app:** `cd frontend` y luego `npm run build`.

## Variables (backend/.env)

| Variable | Para qué |
|---|---|
| `DATABASE_URL` | `sqlite:///./mikuy.db` en local; `postgresql+psycopg://...` en producción (Neon). |
| `GROQ_API_KEY` | Activa Mikuy AI con Groq. Sin clave funciona el intérprete local. |
| `GROQ_MODEL` | Modelo de Groq (por defecto `openai/gpt-oss-120b`). |
| `CORS_ORIGINS` | Dominios del frontend, en formato JSON. |
| `COOKIE_SECURE` / `COOKIE_SAMESITE` | En producción con dominios distintos: `true` / `none`. |
| `PAYMENTS_SIMULATED` | `true` mientras no haya pasarela de pago real. |

En el frontend, `VITE_API_URL` apunta a la API cuando están en dominios distintos.

## Publicar en internet (Render)

La app y la API van juntas en un solo servicio (`Dockerfile`), con una base Postgres. Todo está definido en `render.yaml`.

1. Entra a https://dashboard.render.com e inicia sesión con GitHub.
2. **New → Blueprint** → elige el repo **Mikuy-Ai** y la rama **reconstruccion-premium**.
3. Render muestra el servicio `mikuy` y la base `mikuy-db`. Pulsa **Apply**. El primer despliegue tarda de 5 a 10 minutos.
4. (Opcional) Para Mikuy AI con Groq: servicio `mikuy` → **Environment** → `GROQ_API_KEY`.
5. Abre la dirección `https://mikuy-xxxx.onrender.com` que te da Render.

En el plan gratuito, el servicio se duerme tras 15 minutos sin uso (la primera visita tarda alrededor de 1 minuto en despertar), y la base Postgres gratuita de Render vence a los 30 días. Para algo permanente, usa una base en Neon y pega su URL en `DATABASE_URL`.

## Planes

| | Gratis | Premium | Familia |
|---|---|---|---|
| Mikuy AI | 5 mensajes al día | sin límite + voz | sin límite + voz |
| Menús nuevos | 3 por semana | ilimitados | ilimitados |
| Personas por hogar | hasta 2 | hasta 4 | hasta 12 |
| Precio | S/ 0 | S/ 14,90 al mes · S/ 119 al año | S/ 24,90 al mes · S/ 199 al año |

**Pago simulado:** al pagar, la app genera un código `MIKUY-XXXX-XXXX` (válido 30 minutos) que activa el plan. **Falta conectar la pasarela real** (por ejemplo Mercado Pago, con tarjeta y Yape).

## Fuentes

Los nutrientes salen de las **Tablas Peruanas de Composición de Alimentos (INS-CENAN, 2017)** y de **USDA FoodData Central**. Las metas se calculan con **Mifflin-St Jeor** y los factores de actividad de **FAO/OMS/UNU**. Los precios son estimaciones a partir de reportes del **Midagri**, el **INEI** y medios peruanos (noviembre de 2026). Todos los enlaces están en `backend/app/catalog/sources.py` y en la app (Ajustes → Fuentes).

## Fotos de recetas

Ver `frontend/public/recetas/LEEME.txt`. Sin foto, cada receta muestra una portada ilustrada y animada.

## Pendiente

- Pasarela de pago real.
- Fotos reales de las recetas.
- Despliegue: API en Render, base de datos en Neon y app en Vercel.
- Recuperar contraseña por correo.
- Más adelante: comunidad, fotos de progreso, rachas, reportes y comer fuera.
