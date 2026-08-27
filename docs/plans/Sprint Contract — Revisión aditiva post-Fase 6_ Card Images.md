# Sprint Contract — Revisión aditiva post-Fase 6: Card Images

## 1. Objetivo

Agregar imágenes remotas de cartas al TCG Dashboard de forma segura, extensible y desacoplada del sistema de precios.

El resultado debe permitir:

- mostrar thumbnails en Collection;
- mostrar imagen grande en el detalle de una carta;
- disponer de una Grid View visual además de la tabla actual;
- soportar cartas Magic de varias caras;
- degradar correctamente cuando una carta no tenga imagen;
- mantener abierta la arquitectura para Pokémon y One Piece;
- no guardar archivos de imagen localmente todavía.

Esta tarea es una **revisión aditiva post-Fase 6**.

NO renumerar el roadmap.

La Fase 7 continúa siendo historical market data.

---

# 2. Contexto existente

Antes de modificar código, inspeccionar el estado real del repo.

El proyecto actualmente usa:

- React;
- TypeScript;
- Vite;
- Tailwind;
- shadcn/ui;
- FastAPI;
- SQLite.

Cardmarket sigue siendo la fuente de precios.

Scryfall ya está integrado como fuente autoritativa de metadata de catálogo para Magic cuando existe lookup directo por Cardmarket Product ID.

Ya existen:

- `cards.data_source`;
- `cards.scryfall_raw`;
- `backend/scripts/scryfall_backfill.py`;
- `backend/importer/images.py`.

NO crear un segundo sistema paralelo sin inspeccionar estos componentes.

La colección real actual debe verificarse contra la DB antes de implementar.

No asumir métricas históricas del sprint contract como verdaderas si la DB actual dice otra cosa.

---

# 3. Regla arquitectónica principal

Separar completamente:

    Cardmarket
        ↓
    precios

de:

    image providers
        ↓
    imágenes

La relación conceptual debe ser:

    canonical card / printing
            │
       ┌────┴────┐
       ▼         ▼
     prices     images
    Cardmarket  provider

Una imagen nunca debe ser necesaria para calcular:

- market value;
- P/L;
- ROI;
- historical prices;
- portfolio totals.

Un error de imágenes nunca debe romper información financiera.

---

# 4. Estrategia remote-first

En este sprint:

- NO descargar imágenes localmente;
- NO crear carpeta masiva de imágenes;
- NO usar S3;
- NO usar Cloudflare R2;
- NO crear CDN propio;
- NO almacenar blobs;
- NO almacenar base64.

Guardar solamente metadata y URLs remotas.

Local caching / object storage queda explícitamente diferido.

La arquitectura debe permitir agregarlo posteriormente sin cambiar el contrato de frontend.

---

# 5. Scope de providers

## Magic

Implementar soporte real utilizando Scryfall.

Prioridad de resolución:

1. reutilizar `cards.scryfall_raw` existente;
2. reutilizar helpers existentes en `backend/importer/images.py` si son correctos;
3. solo realizar una consulta Scryfall adicional si no existe información local suficiente y existe un identificador directo y no ambiguo.

NO realizar fuzzy matching automático por nombre para decidir una impresión.

NO reinterpretar ni modificar las decisiones existentes del catálogo Magic.

## Pokémon

NO implementar todavía una integración activa si no existe una necesidad real en la colección actual.

Diseñar el contrato interno para permitir un futuro `PokemonImageProvider`.

No introducir una API key de Pokémon en este sprint.

## One Piece

NO implementar scraping.

NO utilizar endpoints no documentados.

NO asumir que el card number identifica un artwork único.

Diseñar solamente el punto de extensión para un futuro provider.

La integración One Piece se hará en un sprint propio una vez validada:

- fuente;
- términos de uso;
- identidad de impresión;
- idioma;
- variantes;
- artwork exacto.

---

# 6. Inspección obligatoria antes de implementar

Ejecutar primero:

    pwd
    git status --short
    find . -maxdepth 4 -type f | sort | sed 's#^\./##'

Leer como mínimo:

- `AGENTS.md`;
- `docs/PRODUCT.md`, si existe;
- `docs/ARCHITECTURE.md`, si existe;
- `docs/CURRENT_STATE.md`, si existe;
- `docs/decisions/`;
- sprint de Fase 6;
- decisiones de Scryfall;
- `backend/importer/images.py`;
- `backend/scripts/scryfall_backfill.py`;
- `backend/db/`;
- `backend/api/queries.py`;
- `backend/api/schemas.py`;
- router de Collection;
- componentes frontend de Collection;
- componente actual de detalle;
- tipos TypeScript asociados.

Si ya existe una estructura normalizada para imágenes, extenderla.

NO crear `card_images` si el repo ya tiene una solución equivalente y funcional.

---

# 7. Modelo de datos

Si después de inspeccionar el schema no existe una representación normalizada equivalente, crear una tabla aditiva `card_images`.

Diseño recomendado:

    card_images
    ─────────────────────────
    id
    card_id
    source
    source_card_id
    language
    face_index
    image_url_small
    image_url_large
    match_quality
    status
    last_checked_at
    created_at
    updated_at

Relación:

    card_images.card_id
        → cards.id

Valores conceptuales:

`source`:

- `scryfall`
- futuros providers;
- `manual` reservado para futuro.

`match_quality`:

- `exact`
- `representative`
- `manual`

`status`:

- `resolved`
- `ambiguous`
- `missing`
- `error`

`face_index`:

- `0` para la cara principal;
- `1+` para cartas de varias caras.

Crear constraint/índice equivalente a:

    UNIQUE(card_id, source, language, face_index)

No duplicar imágenes por cada copia de `collection_items`.

La imagen pertenece a la impresión/carta, no a cada copia física.

---

# 8. Regla de exactitud

La imagen de una carta es información coleccionable.

Por lo tanto:

**imagen incorrecta es peor que imagen ausente.**

No elegir automáticamente un artwork cuando:

- existen varias impresiones candidatas;
- existen varias ilustraciones;
- set/collector number no coinciden;
- language no coincide cuando afecta a la impresión;
- variant/printing no puede determinarse;
- el identificador externo no es inequívoco.

En estos casos:

    status = ambiguous

o:

    status = missing

y el frontend muestra placeholder.

No adivinar.

---

# 9. Exact vs representative

Preparar la arquitectura para distinguir:

    exact
    representative

`exact` significa que existe evidencia suficiente de que la imagen corresponde a esa impresión concreta.

`representative` significa que corresponde al mismo artwork/card pero no necesariamente a la variante visual exacta.

Ejemplos posibles:

- stamped vs non-stamped;
- diferencias menores de treatment;
- imágenes genéricas de una variante.

En este sprint, preferir `exact`.

No mostrar automáticamente imágenes `representative` como si fueran exactas.

Si se decide utilizar una imagen representative:

- conservar `match_quality=representative`;
- exponerlo en API;
- mostrarlo en el detalle de la carta.

---

# 10. Magic / Scryfall image extraction

Soportar los dos casos principales de Scryfall.

Caso normal:

    image_uris.small
    image_uris.normal / large

Caso multi-face:

    card_faces[0].image_uris
    card_faces[1].image_uris

No asumir que `image_uris` siempre existe en el objeto raíz.

Para Collection thumbnail:

usar una imagen pequeña/normal apropiada.

Para detail:

usar una resolución mayor.

No utilizar PNG de máxima resolución en la tabla.

---

# 11. Resolver / backfill

Crear o adaptar un módulo pequeño y explícito.

Nombre orientativo:

    backend/images/

o reutilizar la ubicación existente si `backend/importer/images.py` ya representa correctamente esta responsabilidad.

Evitar duplicar lógica.

Interfaz conceptual:

    resolve_images(card) -> ImageResolution

No es necesario construir una jerarquía compleja de clases si una solución funcional/simple es suficiente.

Sí debe quedar una separación clara entre:

- lógica común;
- lógica específica de Scryfall.

---

# 12. No external lookup durante requests del dashboard

`GET /api/collection`

y:

`GET /api/collection/{id}`

NO deben llamar a:

- Scryfall;
- Pokémon TCG API;
- Bandai;
- Cardmarket;
- ningún proveedor externo.

Las requests del dashboard solo leen la DB.

Flujo correcto:

    provider
       ↓
    backfill/sync
       ↓
    SQLite
       ↓
    FastAPI
       ↓
    frontend

---

# 13. Script de backfill

Crear o adaptar un script idempotente para resolver imágenes.

Nombre orientativo:

    backend/scripts/backfill_card_images.py

pero reutilizar scripts existentes si hacerlo evita duplicación.

Debe soportar como mínimo:

    --dry-run

y:

    --apply

`--dry-run`:

- no modifica DB;
- muestra estadísticas.

`--apply`:

- realiza upsert idempotente;
- no crea duplicados.

Reportar:

- total inspeccionado;
- resolved exact;
- representative;
- multi-face;
- ambiguous;
- missing;
- errors;
- invalid URLs;
- cuántos se resolvieron sin hacer network request;
- cuántos requirieron consulta externa.

Preferir obtener imágenes desde `cards.scryfall_raw` existente antes de llamar a Scryfall.

---

# 14. Rate limiting

Si el backfill necesita llamar a Scryfall:

- utilizar HTTPS;
- enviar `User-Agent` identificable;
- enviar `Accept` apropiado;
- respetar throttling;
- manejar HTTP 429;
- NO hacer retries agresivos;
- utilizar backoff limitado;
- no superar las recomendaciones actuales de Scryfall.

No hacer N llamadas repetidas para cartas cuya resolución ya está almacenada.

---

# 15. Seguridad de URLs

No confiar automáticamente en URLs obtenidas de cualquier origen.

Para el provider Scryfall:

- aceptar únicamente `https`;
- validar host contra una allowlist explícita de hosts oficiales de imágenes Scryfall;
- rechazar `http`;
- rechazar `file:`;
- rechazar `javascript:`;
- rechazar `data:` como URL persistida;
- rechazar localhost;
- rechazar IPs privadas;
- rechazar URLs vacías o malformadas.

No implementar un endpoint como:

    /api/image-proxy?url=<anything>

No hacer backend fetch de URLs provistas por el usuario.

Esto evita introducir SSRF.

---

# 16. Secrets

Este sprint no requiere secrets nuevos para Scryfall.

No poner credenciales en:

- frontend;
- TypeScript;
- Vite env públicos;
- Git;
- SQLite;
- fixtures.

Cualquier provider futuro que requiera API key debe ejecutarse backend-only y leer secretos mediante variables de entorno no versionadas.

---

# 17. API

Extender la respuesta de Collection sin romper clientes actuales.

Conceptualmente cada item puede devolver:

    image: null

o:

    image:
      source
      match_quality
      faces:
        - face_index
          small_url
          large_url

No exponer `scryfall_raw` completo al frontend.

No exponer metadata externa innecesaria.

Para una carta normal:

    faces.length = 1

Para double-faced:

    faces.length >= 2

Frontend usa:

    faces[0]

como thumbnail principal.

---

# 18. Collection Table

Agregar thumbnail pequeño al listado actual.

Requisitos:

- mantener densidad razonable;
- mantener columnas financieras legibles;
- no hacer la fila excesivamente alta;
- mantener responsive;
- placeholder cuando no existe imagen;
- fallback automático si la URL falla.

Usar:

    loading="lazy"
    decoding="async"
    referrerPolicy="no-referrer"

No bloquear rendering de la tabla esperando imágenes.

---

# 19. Card Detail

Mostrar una imagen de mayor tamaño.

Para cartas multi-face:

- permitir ver ambas caras;
- implementación simple: selector / botones frente-reverso.

Mostrar junto a la imagen:

- nombre;
- set;
- collector number;
- variant;
- language;
- condition;
- quantity;
- purchase price;
- market value;
- P/L;
- ROI cuando corresponda.

No recalcular lógica financiera en frontend si ya proviene del backend.

Si `match_quality=representative`, indicarlo discretamente.

---

# 20. Grid View

Agregar un selector:

    Table | Grid

La vista existente Table sigue siendo la default salvo evidencia fuerte para cambiarla.

Grid debe mostrar tarjetas visuales con:

- imagen;
- card name;
- set / collector number;
- variant cuando sea útil;
- market value;
- status o información esencial.

No intentar poner toda la información de la tabla dentro de cada tarjeta.

Click en card:

    abre el detail existente.

Reutilizar el mismo dataset y filtros de Collection.

No crear un segundo endpoint solamente para Grid.

---

# 21. Rendimiento

Objetivo:

cargar Collection sin descargar todas las imágenes grandes.

Table/Grid:

    small image

Detail:

    large image

Usar lazy loading.

Evitar:

- preload masivo;
- base64;
- blobs en API;
- consulta provider por render;
- consulta DB individual por cada card (N+1).

La query de Collection debe recuperar la metadata de imágenes eficientemente.

Añadir índices necesarios si el query plan lo justifica.

No agregar índices por intuición sin verificar.

---

# 22. Error handling

Una imagen rota no debe generar un error de página.

Frontend:

    image load failure
        ↓
    placeholder

Backend:

si no existe una imagen:

    image = null

No responder `500` porque una carta no tenga imagen.

No confundir:

    missing image

con:

    missing market value

Son estados totalmente independientes.

---

# 23. Manual entries

Actualmente puede haber `collection_items` sin `card_id`.

No inventar un canonical card solamente para darles una imagen.

En este sprint:

    card_id = NULL
        ↓
    image = null
        ↓
    placeholder

Una futura funcionalidad podrá permitir:

- manual image URL;
- manual card mapping;
- local image;
- user-uploaded image.

Eso queda fuera de scope.

---

# 24. Privacidad

Las imágenes remote-first implican que el navegador del usuario contactará al proveedor de imágenes.

No implementar proxy backend en este sprint.

Usar:

    referrerPolicy="no-referrer"

para minimizar metadata enviada en el Referer.

Documentar esta característica.

Local image caching futuro podría eliminar esta dependencia si alguna vez fuese necesario.

---

# 25. No scraping

No introducir scraping de:

- Cardmarket;
- Bandai;
- Pokémon;
- marketplaces;
- Google Images;
- tiendas;
- otros dashboards.

No descargar imágenes de resultados de buscador.

No implementar mecanismos que evadan rate limits, autenticación o controles de acceso.

---

# 26. Database safety

Este proyecto ya tuvo problemas de SQLite sobre FUSE/bridge.

Antes de cualquier escritura contra la DB real:

1. crear copia local;
2. operar sobre la copia;
3. correr:

    PRAGMA integrity_check;
    PRAGMA foreign_key_check;

4. verificar resultados;
5. sincronizar de vuelta el archivo completo solamente siguiendo la política actual del proyecto.

No hacer migraciones directamente sobre el SQLite montado si sigue aplicando la restricción FUSE.

Antes del apply registrar counts de:

- cards;
- collection_items;
- cardmarket_products;
- cardmarket_product_mappings;
- market_price_history.

Después del apply verificar que este sprint no haya alterado accidentalmente esos counts, salvo tablas nuevas específicamente previstas.

---

# 27. Migración

La migración debe ser:

- aditiva;
- idempotente;
- reversible conceptualmente;
- compatible con SQLite actual;
- compatible con una futura migración a PostgreSQL.

No modificar destructivamente:

- cards;
- collection_items;
- prices;
- mappings.

No borrar `scryfall_raw`.

No modificar IDs existentes.

---

# 28. Tests backend

Agregar tests como mínimo para:

### Normal Scryfall card

`image_uris` root:

- small;
- large;
- exact.

### Multi-face card

sin `image_uris` root:

- `card_faces[0]`;
- `card_faces[1]`.

### Missing image

- devuelve `image=null`;
- no genera exception.

### Ambiguous

- no asigna artwork automáticamente.

### URL validation

rechaza al menos:

- http;
- javascript;
- localhost/private target;
- host no permitido.

### Idempotency

dos ejecuciones del backfill:

- no duplican filas;
- no alteran unrelated data.

### API

Collection devuelve correctamente:

- `image=null`;
- imagen de una cara;
- imagen multi-face.

Ningún test de API debe necesitar Internet.

Mockear provider calls cuando corresponda.

---

# 29. Tests frontend

Verificar:

- Table con thumbnail;
- placeholder;
- broken remote image;
- Detail con imagen;
- multi-face si existe fixture;
- Grid View;
- cambio Grid/Table;
- dark mode;
- responsive.

Probar como mínimo ancho:

    375px

No debe aparecer horizontal overflow global.

---

# 30. Regresión

Verificar que sigan funcionando:

- Overview;
- Collection filters;
- search;
- sorting;
- pagination;
- card detail;
- MarketPrice;
- manual-entry badge;
- missing-price state;
- dark mode.

Especialmente:

**imagen ausente no puede transformarse en precio ausente.**

Y viceversa.

---

# 31. Documentación

Si la nueva estructura documental ya existe, actualizar:

    docs/ARCHITECTURE.md
    docs/CURRENT_STATE.md
    docs/decisions/README.md

Crear:

    docs/decisions/TCG-DEC-006-remote-card-images.md

Documentar la decisión:

> Las imágenes de cartas se almacenan inicialmente como URLs remotas y metadata. Los binarios no se almacenan localmente. Card images son independientes de market prices. Scryfall es el provider activo inicial para Magic. Providers de Pokémon y One Piece quedan diferidos hasta validar identidad y fuente.

Guardar este sprint contract en:

    docs/plans/

No inflar `AGENTS.md`.

Modificarlo solamente si hace falta una regla permanente corta sobre remote images/security.

---

# 32. Scope explícitamente excluido

NO implementar:

- image uploads;
- image editor;
- local image storage;
- R2;
- S3;
- Supabase Storage;
- CDN propio;
- service worker image caching;
- collection editing;
- card mapping UI;
- One Piece scraper;
- Pokémon provider activo salvo que el repo actual demuestre que ya existe una integración aprobada;
- trading;
- analytics;
- CARDMADNESS;
- historical price charts;
- cambios en cálculo de market value;
- cambios en Cardmarket importer.

---

# 33. Orden de implementación recomendado

1. Inspección repo.
2. Inspección de `backend/importer/images.py`.
3. Inspección de `scryfall_raw`.
4. Diseñar modelo mínimo sin duplicar estructuras.
5. Migración DB aditiva si hace falta.
6. Parser/resolver Scryfall.
7. Backfill dry-run.
8. Tests parser/resolver.
9. Integración API.
10. Tests API.
11. Thumbnail Collection.
12. Card Detail.
13. Grid View.
14. Responsive/error handling.
15. Ejecución contra copia de DB real.
16. Validaciones de integridad.
17. Documentación/ADR.
18. Reporte final.

---

# 34. Criterios de aceptación

El sprint se considera terminado únicamente si:

- las cartas Magic resolubles muestran la imagen correcta;
- no se introducen fuzzy matches inseguros;
- cartas sin imagen muestran placeholder;
- una imagen rota no rompe la UI;
- el dashboard no consulta Scryfall durante `GET /api/collection`;
- no se almacenan imágenes binarias;
- no aparecen secrets en frontend;
- no existe image proxy abierto;
- URLs externas están validadas;
- double-faced Magic está soportado;
- Table funciona;
- Grid funciona;
- Detail funciona;
- lazy loading funciona;
- mobile 375px funciona;
- dark mode funciona;
- tests backend pasan;
- frontend build pasa;
- DB integrity check pasa;
- foreign key check pasa;
- datos financieros existentes no cambian;
- importer Cardmarket no cambia;
- current phase sigue siendo Phase 7;
- ADR y CURRENT_STATE quedan actualizados.

---

# 35. Verificación final

Ejecutar los comandos reales disponibles en el repo.

Como mínimo, si aplican:

    python3 -m pytest backend/api/ backend/db backend/importer backend/scripts -q

y desde frontend:

    npm run build

Si existe lint:

    npm run lint

Además:

    git diff --check

SQLite:

    PRAGMA integrity_check;
    PRAGMA foreign_key_check;

Reportar resultados exactos.

---

# 36. Reporte final requerido a Codex

Al terminar, responder con:

1. archivos creados;
2. archivos modificados;
3. schema añadido/modificado;
4. estrategia final de resolución de imágenes;
5. cuántas cartas de la colección tienen imagen;
6. cuántas quedaron missing;
7. cuántas quedaron ambiguous;
8. cuántas son multi-face;
9. si hubo network calls durante el backfill;
10. confirmación de que Collection API no hace llamadas externas;
11. resultado de tests backend;
12. resultado del frontend build;
13. resultado de integrity check;
14. resultado de foreign key check;
15. cualquier limitación encontrada.

No ocultar cartas sin resolver.

No considerar el sprint terminado si una imagen dudosa fue asignada automáticamente.

---

# 37. Principio de cierre

Para este proyecto:

> Wrong card image is worse than no card image.

El dashboard debe priorizar identidad coleccionable correcta por encima de cobertura visual artificial.

La infraestructura queda preparada para agregar Pokémon, One Piece y almacenamiento local en futuros sprints sin reescribir Collection.