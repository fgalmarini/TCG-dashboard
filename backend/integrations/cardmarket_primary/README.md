# cardmarketapi.com — PRIMARY current price

## Purpose

PRIMARY provider for `current_price` in EUR.

This is **not** Cardmarket's official API. It is a third-party service that reads
Cardmarket product pages and exposes filtered JSON.

## Identity

Preferred lookup: existing validated Cardmarket `idProduct`.

Search-by-name is discovery only and must not automatically resolve an ambiguous
printing.

## Pricing contract

Default request filter:

- language: `english`
- condition: `nm` (Near Mint or better)
- currency: EUR

Candidate `current_price`: `prices.from`, provided the returned product/filter matches
the expected identity and required policy.

Other fields (`avg5`, `trend`, `avg30`, availability, listings) are informational and
must not silently replace `current_price`.

## Authentication

Code: `auth.py`

Environment variable:

`CARDMARKET_PRIMARY_API_KEY`

Header:

`X-API-Key`

Never put the key in source, query strings, fixtures, logs or documentation.

## Fallback trigger

`tcg_cardmarket` may be called only when this provider:

- times out / cannot be reached;
- returns an HTTP/service error;
- returns no usable current price for a known valid product;
- cannot resolve a Cardmarket product ID already validated by our DB.

Do **not** trigger fallback because a valid price looks surprising, high or low.

## Rate-limit / freshness policy

Read live quota headers and `/usage`; do not hard-code plan limits into business logic.
Responses may be cached by the provider for about one hour. Persist provider
`fetched_at` when snapshots are implemented.

## Upstream references

- Docs: https://www.cardmarketapi.com/docs
- Dashboard/key: https://www.cardmarketapi.com/dashboard
- `llms.txt`: linked from the official docs and useful for agent-readable reference.

No official OpenAPI/Swagger download was found during the 2026-09-06 review.
