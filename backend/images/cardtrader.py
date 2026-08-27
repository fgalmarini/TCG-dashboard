"""CardTrader catalog access for backend-only exact image resolution."""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Callable
from urllib.parse import urlparse

from .resolver import ImageResolution, resolve_cardtrader_blueprint

REPO_ROOT = Path(__file__).resolve().parents[2]
CARDTRADER_BASE_URL = "https://api.cardtrader.com/api/v2"
CARDTRADER_EXPANSION_ID = 3395
CARDTRADER_EXPANSION_NAME = "The Lord of the Rings Art Series"
CARDTRADER_TIMEOUT_SECONDS = 30


class CardTraderConfigurationError(RuntimeError):
    """Raised when the backend cannot obtain a CardTrader token."""


def _load_simple_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key.strip() == "CARDTRADER_API_TOKEN" and "CARDTRADER_API_TOKEN" not in os.environ:
            os.environ[key.strip()] = value.strip().strip("'\"")


def load_cardtrader_token(env_path: Path = REPO_ROOT / ".env") -> str:
    """Load the token into this process only, without logging its value."""
    try:
        from dotenv import load_dotenv
    except ImportError:
        _load_simple_dotenv(env_path)
    else:
        load_dotenv(dotenv_path=env_path, override=False)

    token = os.environ.get("CARDTRADER_API_TOKEN")
    if not token:
        raise CardTraderConfigurationError(
            "CARDTRADER_API_TOKEN no existe o está vacío en el .env backend"
        )
    return token


@dataclass(frozen=True)
class CardTraderCatalog:
    blueprints: tuple[dict, ...]
    by_cardmarket_id: dict[int, tuple[dict, ...]]
    image_hosts: frozenset[str]

    @classmethod
    def from_blueprints(cls, blueprints: list[dict]) -> "CardTraderCatalog":
        by_cardmarket_id: dict[int, list[dict]] = defaultdict(list)
        image_hosts: set[str] = set()
        for blueprint in blueprints:
            for value in blueprint.get("card_market_ids") or []:
                by_cardmarket_id[int(value)].append(blueprint)
            parsed = urlparse(blueprint.get("image_url") or "")
            if parsed.hostname:
                image_hosts.add(parsed.hostname.lower())
        return cls(
            blueprints=tuple(blueprints),
            by_cardmarket_id={key: tuple(value) for key, value in by_cardmarket_id.items()},
            image_hosts=frozenset(image_hosts),
        )

    def resolve_product_id(self, cardmarket_product_id: int) -> ImageResolution:
        matches = self.by_cardmarket_id.get(cardmarket_product_id, ())
        unique_blueprint_ids = {blueprint.get("id") for blueprint in matches}
        if not matches:
            return ImageResolution(
                source="cardtrader",
                source_card_id=None,
                language="unknown",
                match_quality="exact",
                status="missing",
                reason=f"no CardTrader Blueprint for cardmarket_id_product={cardmarket_product_id}",
            )
        if len(unique_blueprint_ids) != 1:
            return ImageResolution(
                source="cardtrader",
                source_card_id=None,
                language="unknown",
                match_quality="exact",
                status="ambiguous",
                reason=(
                    f"multiple CardTrader Blueprints for cardmarket_id_product={cardmarket_product_id}: "
                    f"{sorted(unique_blueprint_ids)}"
                ),
            )
        return resolve_cardtrader_blueprint(matches[0], self.image_hosts)


class CardTraderClient:
    def __init__(
        self,
        token: str | None = None,
        opener: Callable[[urllib.request.Request], object] | None = None,
    ) -> None:
        self.token = token or load_cardtrader_token()
        self.opener = opener or urllib.request.urlopen

    def fetch_blueprints(self, expansion_id: int = CARDTRADER_EXPANSION_ID) -> CardTraderCatalog:
        url = f"{CARDTRADER_BASE_URL}/blueprints/export?{urllib.parse.urlencode({'expansion_id': expansion_id})}"
        request = urllib.request.Request(
            url,
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "TCGDashboard/1.0 (backend card image backfill)",
            },
            method="GET",
        )
        try:
            response = self.opener(request, timeout=CARDTRADER_TIMEOUT_SECONDS)
            with response as opened:
                payload = json.loads(opened.read())
        except urllib.error.HTTPError as exc:
            if exc.code in {401, 403}:
                raise CardTraderConfigurationError(
                    f"CardTrader rechazó la autenticación con HTTP {exc.code}"
                ) from exc
            raise RuntimeError(f"CardTrader Blueprint export HTTP {exc.code}") from exc
        except (OSError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"CardTrader Blueprint export failed: {exc}") from exc

        if not isinstance(payload, list):
            raise RuntimeError("CardTrader Blueprint export devolvió un payload inesperado")
        return CardTraderCatalog.from_blueprints(payload)
