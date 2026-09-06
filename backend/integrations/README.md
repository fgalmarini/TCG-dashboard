# External Integrations

This directory is the code-local source of truth for external API integrations.

Global provider roles and fallback policy live in `docs/DATA_SOURCES.md`. Before
changing any integration, read that file and the provider-local `README.md`.

Rules:

- Authentication policy lives with the provider code in `auth.py`.
- Real secrets live only in environment variables / `.env`; never commit them.
- `client.py` owns the provider base URL and endpoint construction.
- External IDs never replace internal `cards.id` / canonical identity.
- Provider calls belong in maintenance/sync workflows, not normal FastAPI reads.
- Any behavior change to a provider integration must update its local README in the
  same commit.
- Do not silently fall back from an identity ambiguity to another product.
- Do not add undocumented endpoints, scrapers or access-control workarounds.

Provider map:

| Package | Role |
|---|---|
| `cardmarket_primary` | PRIMARY current EUR price |
| `tcg_cardmarket` | FALLBACK current EUR price |
| `tcgdex` | Pokémon identity, metadata, variants and images |
| `scryfall` | Magic identity, printings, finishes, metadata and images |
| `tcgapi` | Secondary market analytics / metrics; Free tier only for now |

CardTrader is intentionally outside the new pricing architecture. Existing legacy
code must not be deleted until callers and migrations are audited.
