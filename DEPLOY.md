# Desplegar INDU-TWIN (gratis): Vercel + Render

Mismo patrón que usa OLEAMIND: **frontend en Vercel** (estático, gratis sin
condiciones) + **backend en Render** (gratis, pero se duerme tras ~15 min de
inactividad — la primera petición después de dormir tarda 30-60s en
responder, luego va normal).

Aviso honesto sobre los datos: el plan gratuito de Render no incluye disco
persistente, así que `indu_twin.db` vive en el contenedor y se resetea a los
datos de `seed.py` en cada redeploy (no en cada "despertar", solo cuando subes
código nuevo). Para una demo comercial esto no es necesariamente malo — cada
redeploy deja datos de demo limpios — pero si más adelante quieres datos que
persistan de verdad entre despliegues, hace falta pasar a un disco de pago en
Render o a una base de datos gestionada (Postgres).

## 0. Sube el código a GitHub

Esto lo tienes que hacer tú (no puedo crear ni conectar cuentas en tu
nombre):

```bash
# Si no tienes ya un repo en GitHub, créalo vacío en github.com/new
# (sin README/gitignore, para no chocar con lo que ya hay aquí)
git remote add origin https://github.com/<tu-usuario>/indu-twin.git
git branch -M main
git push -u origin main
```

## 1. Backend en Render

1. Entra en [render.com](https://render.com) con tu cuenta de GitHub.
2. **New +** → **Blueprint** → selecciona el repo `indu-twin`. Render leerá
   [`render.yaml`](render.yaml) automáticamente y propondrá el servicio
   `indu-twin-backend` (Docker, plan free, healthcheck en `/api/health`).
3. Si prefieres configurarlo a mano en vez de con el Blueprint: **New +** →
   **Web Service** → conecta el repo → *Root Directory* `backend` →
   *Runtime* Docker → *Plan* Free → *Health Check Path* `/api/health`.
4. Añade las variables de entorno (o revísalas si vinieron del Blueprint):
   - `JWT_SECRET_KEY` — genera una aleatoria (Render puede hacerlo por ti).
   - `PLAN` — `free`, `pro` o `business` según lo que quieras mostrar.
   - `CORS_ORIGINS` — de momento pon cualquier valor, lo actualizas en el
     paso 3 con la URL real de Vercel.
   - `APP_BASE_URL` — igual, se actualiza en el paso 3.
5. Deploy. Cuando termine, copia la URL pública
   (`https://indu-twin-backend.onrender.com` o la que te asigne Render).

## 2. Frontend en Vercel

1. Entra en [vercel.com](https://vercel.com) con tu cuenta de GitHub.
2. **Add New** → **Project** → selecciona el repo `indu-twin`.
3. *Root Directory*: `frontend` (Vercel detecta Vite automáticamente, no
   hace falta tocar el build command).
4. Variable de entorno: `VITE_API_URL` = la URL de Render del paso 1
   (sin `/` al final).
5. Deploy. Vercel te da una URL tipo `https://indu-twin.vercel.app`.

## 3. Cierra el círculo: CORS

Vuelve a Render → tu servicio → **Environment** y actualiza:

- `CORS_ORIGINS` = la URL de Vercel del paso 2
- `APP_BASE_URL` = la misma URL (se usa en los enlaces de los emails de
  recuperación de contraseña, si activas `SMTP_HOST`)

Guarda — Render redeploya solo con las nuevas variables.

## 4. Comprueba

Abre la URL de Vercel, entra con `admin@indutwin.com` / `admin123` (o crea tu
propia cuenta si `/login` te ofrece "Configura tu cuenta" porque la base de
datos está recién sembrada). Si el login tarda mucho la primera vez, es el
backend de Render despertándose — normal, espera y reintenta.

## Antes de enseñárselo a alguien de verdad

Cambia (o borra) las contraseñas demo desde **Usuarios** — en una URL
pública cualquiera puede entrar con `admin123` si no las cambias.
