# TCG-DEC-009 — External data provider and authentication policy

Status: Accepted — foundation implemented; runtime pricing migration pending  
Date: 2026-09-06

## Context

TCG Dashboard accumulated provider-specific logic across import scripts, pricing code
and documentation. The next pricing phase will use external APIs, so provider roles,
authentication and fallback behavior must remain discoverable and replaceable.

Cardmarket's official API is not assumed available for new credentials. The selected
PRIMARY is `cardmarketapi.com`, a third-party service exposing Cardmarket data.

## Decision

1. `cardmarketapi.com` is PRIMARY for current EUR price.
2. TCG Cardmarket API is FALLBACK for current EUR price.
3. TCGdex is Pokémon metadata/variants/images only.
4. Scryfall is Magic metadata/printings/finishes/images only.
5. TCG API is secondary analytics; Free tier only until a later decision.
6. CardTrader is outside the new current-price architecture.
7. Internal card/printing identity remains owned by TCG Dashboard.
8. Provider-specific authentication and endpoint knowledge live under
   `backend/integrations/<provider>/`.
9. Actual secrets live in environment variables and are never committed.
10. Normal dashboard API reads do not call external providers; synchronization writes
    normalized snapshots/resolutions for FastAPI to read.

## Fallback invariant

Fallback is availability/data-absence recovery, not price shopping or identity repair.

A valid PRIMARY result cannot be overwritten by FALLBACK merely because another price
looks preferable.

If neither provider returns a valid current result, current price is NULL.

## Analytics / history invariant

TCG API must not determine official current EUR value.

While the project remains on TCG API Free, history endpoints are treated as
non-guaranteed because current public provider documentation has shown inconsistent
Free-tier history statements. Long-term free charts should therefore be built from our
own stored snapshots unless live verification proves a Free history window and the
feature remains optional.

## Knowledge-with-code contract

Each provider folder must contain enough local documentation to answer:

- what the provider is used for;
- what it is explicitly not used for;
- authentication mechanism and env variable;
- authoritative endpoints/base URL;
- important limits/freshness;
- fallback behavior when applicable;
- upstream documentation/reference links.

Changes to those behaviors require the provider-local README to change with the code.

## Consequences

Positive:

- provider replacement is isolated;
- agents have a deterministic discovery path;
- credentials cannot leak through source files by design;
- source provenance remains explicit;
- future provider changes do not redefine internal card identity.

Trade-offs:

- more small provider modules/docs must be maintained;
- live provider behavior must be validated in POCs;
- current legacy pricing paths remain until explicitly migrated.

## Implementation pointers

- Global map: `docs/DATA_SOURCES.md`
- Code-local map: `backend/integrations/README.md`
- Provider packages: `backend/integrations/*`
- Secret variable names: `.env.example`
