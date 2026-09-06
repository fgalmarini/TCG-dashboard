# TCG API — secondary analytics

## Purpose

Secondary, TCGplayer-oriented market analytics.

Use for:

- market metrics that are not TCG Dashboard `current_price`;
- price movement / momentum;
- top movers;
- secondary USD context;
- historical charts only where the active plan actually permits history.

Do not use it to set the official EUR `current_price`.

## Plan policy

Use **Free tier only** for now.

The current public documentation agrees on 100 requests/day for Free, but its pages
have shown inconsistent statements about history availability (some current docs gate
history above Free while an SDK README has described a short Free window).

Therefore:

- never make core functionality depend on `/history` while we remain Free;
- verify the live tier response before enabling any history endpoint;
- build our own long-term chart history from stored snapshots where needed;
- no paid-tier feature may be required by the application without a new decision.

## Authentication

Code: `auth.py`

Environment variable:

`TCGAPI_KEY`

Header:

`X-API-Key`

The official Python SDK also reads `TCGAPI_KEY`; wrap it behind this integration if we
adopt it rather than exposing SDK calls across the application.

## Downloadable/installable upstream material

Official SDKs are available and MIT licensed:

- Python SDK: https://github.com/gordy-ftw/tcgapi-python
- JS/TS SDK: https://github.com/gordy-ftw/tcgapi-js
- Python package: `pip install tcgapi`
- API explorer: https://tcgapi.dev/api-explorer/
- Authentication: https://tcgapi.dev/authentication/
- Rate limits: https://tcgapi.dev/guides/rate-limits/

Do not vendor the SDK source into this repository. If adopted, pin a package version in
project dependencies and keep our provider wrapper as the application boundary.

No official OpenAPI/Swagger download was found during the 2026-09-06 review.
