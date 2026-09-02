# TCG-MOBILE-001 — Event Mobile Access

Status: Implemented
Date: 2026-09-02

## Context

TCG Dashboard debe poder utilizarse desde un celular durante eventos sin migrar la
aplicación ni SQLite a la nube. La Mac es el servidor local y necesita una exposición
HTTPS segura con una sola URL pública.

## Decision

- Usar un Cloudflare Named Tunnel administrado localmente por `cloudflared`.
- Proteger el hostname con Cloudflare Access; no implementar autenticación propia.
- Publicar únicamente Vite en `127.0.0.1:3000`.
- Proxyar `/api/*` desde Vite hacia FastAPI en `127.0.0.1:8000`.
- Resolver la API desde `window.location.origin` cuando no exista
  `VITE_API_BASE_URL`.
- Ejecutar Event Mode con el launcher raíz `./event-mobile`.
- Mantener el estado de aplicación y SQLite exclusivamente en la Mac.

## Consequences

El navegador móvil usa un único origen y nunca necesita conocer la URL del backend.
FastAPI queda privado y la conectividad depende de que la Mac esté encendida,
conectada a Internet y con Event Mode activo. Las credenciales locales de
`cloudflared` permanecen fuera del repositorio.
