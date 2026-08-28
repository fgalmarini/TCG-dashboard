"""Safe remote card image resolution.

This module stores only provider metadata and remote URLs. It does not fetch image
files, store blobs, or participate in market-value calculations.
"""

from __future__ import annotations

import ipaddress
import json
from dataclasses import dataclass, field
from urllib.parse import urlparse

SCRYFALL_IMAGE_HOSTS = {"cards.scryfall.io"}


@dataclass(frozen=True)
class ImageFace:
    face_index: int
    small_url: str | None
    large_url: str | None


@dataclass(frozen=True)
class ImageResolution:
    source: str
    source_card_id: str | None
    language: str
    match_quality: str
    status: str
    faces: list[ImageFace] = field(default_factory=list)
    reason: str | None = None
    source_variant: str | None = None
    source_collector_number: str | None = None
    actual_image_language: str | None = None
    requested_language: str | None = None
    is_language_fallback: bool = False


def validate_remote_image_url(url: str | None, allowed_hosts: set[str] | None = None) -> str | None:
    """Return a normalized URL if it is safe to persist, otherwise None."""
    if not url or not isinstance(url, str):
        return None

    allowed = allowed_hosts or SCRYFALL_IMAGE_HOSTS
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return None
    if not parsed.hostname:
        return None

    host = parsed.hostname.lower()
    if host not in allowed:
        return None

    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip and (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved):
        return None

    return url


def _pick_small(image_uris: dict) -> str | None:
    return image_uris.get("small") or image_uris.get("normal")


def _pick_large(image_uris: dict) -> str | None:
    return image_uris.get("large") or image_uris.get("normal") or image_uris.get("small")


def _face_from_image_uris(face_index: int, image_uris: dict) -> ImageFace | None:
    small_url = validate_remote_image_url(_pick_small(image_uris))
    large_url = validate_remote_image_url(_pick_large(image_uris))
    if small_url is None and large_url is None:
        return None
    return ImageFace(face_index=face_index, small_url=small_url, large_url=large_url)


def resolve_cardtrader_blueprint(
    blueprint: dict,
    allowed_hosts: set[str] | frozenset[str],
) -> ImageResolution:
    """Resolve one CardTrader Blueprint without downloading its image."""
    blueprint_id = blueprint.get("id")
    if blueprint_id is None:
        return ImageResolution(
            source="cardtrader",
            source_card_id=None,
            language="unknown",
            match_quality="exact",
            status="ambiguous",
            reason="CardTrader Blueprint id missing",
        )

    language = "unknown"
    for prop in blueprint.get("editable_properties") or []:
        if isinstance(prop, dict) and prop.get("name") == "mtg_language":
            language = str(prop.get("default_value") or "unknown")
            break

    image_url = validate_remote_image_url(blueprint.get("image_url"), set(allowed_hosts))
    if image_url is None:
        return ImageResolution(
            source="cardtrader",
            source_card_id=str(blueprint_id),
            language=language,
            match_quality="exact",
            status="error",
            reason="CardTrader image_url failed validation",
            source_variant=blueprint.get("version") or None,
            source_collector_number=(blueprint.get("fixed_properties") or {}).get("collector_number"),
        )

    return ImageResolution(
        source="cardtrader",
        source_card_id=str(blueprint_id),
        language=language,
        match_quality="exact",
        status="resolved",
        faces=[ImageFace(face_index=0, small_url=None, large_url=image_url)],
        source_variant=blueprint.get("version") or None,
        source_collector_number=(blueprint.get("fixed_properties") or {}).get("collector_number"),
    )


def resolve_scryfall_raw(raw_json: str | None) -> ImageResolution:
    if not raw_json:
        return ImageResolution(
            source="scryfall",
            source_card_id=None,
            language="unknown",
            match_quality="exact",
            status="missing",
            reason="missing scryfall_raw",
        )

    try:
        data = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        return ImageResolution(
            source="scryfall",
            source_card_id=None,
            language="unknown",
            match_quality="exact",
            status="error",
            reason=f"invalid scryfall_raw JSON: {exc}",
        )

    return resolve_scryfall_card(data)


def resolve_scryfall_card(data: dict) -> ImageResolution:
    source_card_id = data.get("id")
    language = data.get("lang") or "unknown"
    if not source_card_id:
        return ImageResolution(
            source="scryfall",
            source_card_id=None,
            language=language,
            match_quality="exact",
            status="ambiguous",
            reason="Scryfall card id missing",
        )

    root_images = data.get("image_uris")
    if isinstance(root_images, dict):
        face = _face_from_image_uris(0, root_images)
        if face:
            return ImageResolution(
                source="scryfall",
                source_card_id=source_card_id,
                language=language,
                match_quality="exact",
                status="resolved",
                faces=[face],
            )
        return ImageResolution(
            source="scryfall",
            source_card_id=source_card_id,
            language=language,
            match_quality="exact",
            status="error",
            reason="Scryfall image URLs failed validation",
        )

    faces: list[ImageFace] = []
    for index, face_data in enumerate(data.get("card_faces") or []):
        if not isinstance(face_data, dict):
            continue
        face_images = face_data.get("image_uris")
        if not isinstance(face_images, dict):
            continue
        face = _face_from_image_uris(index, face_images)
        if face is None:
            return ImageResolution(
                source="scryfall",
                source_card_id=source_card_id,
                language=language,
                match_quality="exact",
                status="error",
                reason=f"Scryfall image URLs failed validation for face {index}",
            )
        faces.append(face)

    if faces:
        return ImageResolution(
            source="scryfall",
            source_card_id=source_card_id,
            language=language,
            match_quality="exact",
            status="resolved",
            faces=faces,
        )

    return ImageResolution(
        source="scryfall",
        source_card_id=source_card_id,
        language=language,
        match_quality="exact",
        status="missing",
        reason="Scryfall card has no image_uris",
    )
