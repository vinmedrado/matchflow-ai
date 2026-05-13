from __future__ import annotations
from .client import FlashScoreClient

def scrape_league_matches(league, *, headless=True, sleep_seconds=0.5, timeout_seconds=30, test_mode=True, use_demo=False):
    client = FlashScoreClient(headless=headless, sleep_seconds=sleep_seconds, timeout_seconds=timeout_seconds, use_demo=use_demo)
    rows = client.fetch_league_matches(league, test_mode=test_mode)
    meta_warnings: list[str] = []
    if client.network_samples:
        meta_warnings.append(f"network_capture_count={len(client.network_samples)}")
    if client.failed_urls:
        meta_warnings.append(f"failed_urls_count={len(client.failed_urls)}")
    for row in rows:
        existing = row.get("provider_warnings") or ""
        combined = "; ".join([x for x in [existing, *client.warnings, *meta_warnings] if x])
        row["provider_warnings"] = combined
    warnings = [*client.warnings, *meta_warnings]
    for sample in client.network_samples[:10]:
        warnings.append("network_sample:" + str({k: sample.get(k) for k in ["url", "status", "response_type", "parsed_items_count"]}))
    for url in client.failed_urls[:10]:
        warnings.append("failed_url:" + url)
    return rows, warnings
