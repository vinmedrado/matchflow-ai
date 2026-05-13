from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from typing import Any

FLASH_RELEVANT_TOKENS = (
    "flashscore", "flashscore.ninja", "event", "match", "fixture", "odds", "statistics", "stats", "standing"
)

@dataclass
class CapturedResponse:
    url: str
    status: int
    content_type: str
    response_type: str
    body_sample: str
    parsed_items_count: int = 0

    def sanitized(self) -> dict[str, Any]:
        data = asdict(self)
        # Keep reports useful while avoiding huge payloads/cookies/tokens.
        data["body_sample"] = re.sub(r"(?i)(token|key|secret|session)[=:][^&\s]+", r"\1=<redacted>", data["body_sample"][:1800])
        return data


def is_relevant_response(url: str, resource_type: str | None = None, status: int | None = None) -> bool:
    low = str(url or "").lower()
    if resource_type and resource_type not in {"xhr", "fetch", "document"}:
        return False
    if status is not None and int(status) >= 500:
        return False
    return any(token in low for token in FLASH_RELEVANT_TOKENS)


def classify_response(url: str, payload: Any | None = None, body_sample: str = "") -> str:
    low = f"{url} {body_sample[:500]}".lower()
    if any(token in low for token in ("odds", "prematch", "bookmaker")):
        return "odds"
    if any(token in low for token in ("statistic", "statistics", "stats", "xg", "corner", "shot")):
        return "stats"
    if any(token in low for token in ("incident", "event", "goal", "card", "substitution")):
        return "events"
    if any(token in low for token in ("standings", "table")):
        return "standings"
    if any(token in low for token in ("fixture", "fixtures", "match", "event")):
        return "fixtures"
    if isinstance(payload, dict):
        keys = {str(k).lower() for k in payload.keys()}
        if keys & {"odds", "markets", "bookmakers"}:
            return "odds"
        if keys & {"stats", "statistics"}:
            return "stats"
        if keys & {"incidents", "events"}:
            return "events"
    return "unknown"


def try_load_payload(body: str) -> Any | None:
    text = str(body or "").strip()
    if not text:
        return None
    try:
        return json.loads(text)
    except Exception:
        pass
    # FlashScore sometimes returns compact JS-like payloads. Do not attempt unsafe eval;
    # return None and let text fallback parsers handle conservative extraction.
    return None


def flatten_dicts(obj: Any) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    if isinstance(obj, dict):
        found.append(obj)
        for value in obj.values():
            found.extend(flatten_dicts(value))
    elif isinstance(obj, list):
        for value in obj:
            found.extend(flatten_dicts(value))
    return found


def build_capture_record(url: str, status: int, content_type: str, body: str, parsed_items_count: int = 0) -> CapturedResponse:
    payload = try_load_payload(body)
    rtype = classify_response(url, payload, body[:1000])
    return CapturedResponse(
        url=url,
        status=int(status),
        content_type=content_type or "",
        response_type=rtype,
        body_sample=str(body or "")[:1800],
        parsed_items_count=parsed_items_count,
    )
