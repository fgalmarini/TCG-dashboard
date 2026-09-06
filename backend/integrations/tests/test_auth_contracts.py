"""Credential-location contract for external provider integrations."""

from __future__ import annotations

import pytest

from backend.integrations.cardmarket_primary import auth as cardmarket_primary_auth
from backend.integrations.scryfall import auth as scryfall_auth
from backend.integrations.tcg_cardmarket import auth as tcg_cardmarket_auth
from backend.integrations.tcgapi import auth as tcgapi_auth
from backend.integrations.tcgdex import auth as tcgdex_auth


@pytest.mark.parametrize(
    ("module", "env_name"),
    [
        (cardmarket_primary_auth, "CARDMARKET_PRIMARY_API_KEY"),
        (tcg_cardmarket_auth, "TCG_CARDMARKET_API_KEY"),
        (tcgapi_auth, "TCGAPI_KEY"),
    ],
)
def test_keyed_provider_reads_only_its_declared_env(module, env_name):
    headers = module.build_headers(environ={env_name: "test-secret"})
    assert headers["X-API-Key"] == "test-secret"


@pytest.mark.parametrize(
    "module",
    [cardmarket_primary_auth, tcg_cardmarket_auth, tcgapi_auth],
)
def test_keyed_provider_fails_closed_when_secret_missing(module):
    with pytest.raises(module.MissingCredentialError):
        module.build_headers(environ={})


def test_public_providers_explicitly_require_no_secret():
    assert tcgdex_auth.AUTH_REQUIRED is False
    assert "X-API-Key" not in tcgdex_auth.build_headers()

    assert scryfall_auth.AUTH_REQUIRED is False
    assert "X-API-Key" not in scryfall_auth.build_headers()
    assert "User-Agent" in scryfall_auth.build_headers()
