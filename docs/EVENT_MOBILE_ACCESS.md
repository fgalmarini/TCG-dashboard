# Event Mobile Access

Event Mode permite usar TCG Dashboard desde un celular durante un evento. La Mac
ejecuta el frontend, la API y SQLite localmente; Cloudflare aporta el transporte
HTTPS y la autenticación externa.

## One-time setup

1. Instalar `cloudflared` en la Mac.
2. Crear un Cloudflare Named Tunnel administrado localmente y autenticarse con
   `cloudflared login`. Sus credenciales quedan fuera del repositorio, normalmente
   bajo `~/.cloudflared/`.
3. Configurar el túnel con una única Published Application Route:
   `https://tcg.example.com` -> `http://127.0.0.1:3000`.
4. Asociar el hostname al túnel, por ejemplo:

   ```bash
   cloudflared tunnel route dns tcg-dashboard tcg.example.com
   ```

5. Crear una aplicación de Cloudflare Access para ese hostname y restringirla al
   email autorizado del propietario.
6. Copiar `.env.event.example` a `.env.event.local` y completar:

   ```text
   TCG_CF_TUNNEL_NAME=tcg-dashboard
   TCG_EVENT_URL=https://tcg.example.com
   TCG_EVENT_HOST=tcg.example.com
   ```

No guardar tokens, credenciales ni secrets en Git. `.env.event.local` está ignorado.

## Event usage

1. Encender la Mac.
2. Conectarla a Internet.
3. Abrir Terminal.
4. Ir al repositorio.
5. Ejecutar `./event-mobile`.
6. Abrir la URL desde el celular.
7. Autenticarse mediante Cloudflare Access.
8. Al terminar, usar `Ctrl+C` en Terminal.

El navegador usa la misma URL para la aplicación y `/api/*`. FastAPI no se publica
directamente.

## Troubleshooting

- `cloudflared` no instalado: instalarlo y confirmar que `cloudflared --version`
  funciona desde la misma Terminal.
- Backend no arranca: comprobar las dependencias de
  `backend/api/requirements.txt` y que el puerto `8000` esté libre.
- Frontend no arranca: ejecutar `npm install` dentro de `frontend/` y comprobar que
  el puerto `3000` esté libre.
- Tunnel no configurado: comprobar `TCG_CF_TUNNEL_NAME`, el login local de
  `cloudflared` y que el Named Tunnel exista.
- La URL carga pero la API falla: confirmar que la Published Application Route apunta
  a `http://127.0.0.1:3000`, que FastAPI responde en `/health` y que no se configuró
  un `VITE_API_BASE_URL` público o incorrecto.
