import unicodedata
from pathlib import Path

import yaml

REQUIRED_FIELDS = {"product", "quantity"}

_YAML_PATH = Path(__file__).parent / "column_map.yaml"


def _normalize(text: str) -> str:
    stripped = text.strip().lower()
    return (
        unicodedata.normalize("NFKD", stripped)
        .encode("ascii", "ignore")
        .decode()
    )


def _load_synonyms() -> list[tuple[str, str]]:
    """Return [(normalized_alias, canonical_field), ...] in YAML order."""
    with _YAML_PATH.open() as f:
        raw = yaml.safe_load(f) or {}
    pairs: list[tuple[str, str]] = []
    for canonical, aliases in raw.items():
        for alias in aliases or []:
            pairs.append((_normalize(alias), canonical))
    return pairs


_SYNONYMS = _load_synonyms()


def canonicalize_columns(headers: list[str]) -> dict[str, str]:
    """Map raw headers to canonical field names, dropping unrecognized headers."""
    result: dict[str, str] = {}
    for header in headers:
        normalized = _normalize(header)
        if not normalized:
            continue
        for alias, canonical in _SYNONYMS:
            if alias == normalized:
                result[header] = canonical
                break
    return result
