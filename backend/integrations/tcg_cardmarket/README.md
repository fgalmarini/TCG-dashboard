# TCG Cardmarket API — FALLBACK current price

## Purpose

Secondary provider for current Cardmarket EUR pricing.

It is **not** an identity-repair engine and must never override a valid PRIMARY result.

## Activation contract

Call this provider only after `cardmarket_primary` has produced one of these states:

- timeout / network unavailability;
- HTTP/service failure;
- no usable price;
- a validated Cardmarket product ID is not resolved by the PRIMARY provider.

If PRIMARY returned a valid result, stop. Do not compare both providers and choose the
more convenient price.

If both providers fail, `current_price = NULL`. Historical data must not be promoted
to current price.

## Identity

Use the same validated Cardmarket product ID as PRIMARY. Name search may assist manual
investigation only; ambiguous identity requires review.

## Authentication

Code: `auth.py`

Environment variable:

`TCG_CARDMARKET_API_KEY`

Header:

`X-API-Key`

## Free-tier behavior

The reviewed documentation states 100 requests/day and batch size 10 for the Free
plan. Read rate-limit headers at runtime rather than hard-coding quota assumptions.

Prices are documented as refreshed daily around 04:00 UTC.

## Upstream references

- Docs: https://www.tcg-cardmarket-api.com/docs
- Cards: https://www.tcg-cardmarket-api.com/docs/cards
- Rate limits: https://www.tcg-cardmarket-api.com/docs/rate-limits
- Registration: https://www.tcg-cardmarket-api.com/register

No official OpenAPI/Swagger download was found during the 2026-09-06 review.

The API origin currently shown in official examples is isolated in `client.py`; verify
it before production activation because provider hosting may change.
