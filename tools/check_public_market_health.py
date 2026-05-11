#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any


BASE_URL = "https://swampdad.github.io/idle-hacking-companion/"
EXPECTED_COMMODITIES = 16
WARN_AFTER_MINUTES = 90
ALERT_AFTER_MINUTES = 180
CRITICAL_AFTER_MINUTES = 360
TIMEOUT_SECONDS = 20


def parse_dt(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing/non-string datetime")

    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    dt = datetime.fromisoformat(normalized)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def fetch_text(url: str) -> tuple[str | None, str | None, int | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "ih-market-health-check/1.0"})

    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            status = getattr(response, "status", None)
            body = response.read().decode("utf-8")
            return body, None, status
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}", exc.code
    except Exception as exc:
        return None, str(exc), None


def fetch_json(path: str) -> tuple[dict[str, Any] | None, str | None, int | None]:
    body, error, status = fetch_text(BASE_URL + path)
    if error:
        return None, error, status

    try:
        data = json.loads(body or "")
    except Exception as exc:
        return None, f"invalid JSON: {exc}", status

    if not isinstance(data, dict):
        return None, "invalid JSON: top-level value is not an object", status

    return data, None, status


def format_age(minutes: float | None) -> str:
    if minutes is None:
        return "unknown"

    if minutes < 60:
        return f"{minutes:.0f}m"

    hours = int(minutes // 60)
    rem = int(minutes % 60)
    return f"{hours}h {rem}m" if rem else f"{hours}h"


def main() -> int:
    problems: list[tuple[str, str]] = []
    warnings: list[tuple[str, str]] = []

    root_body, root_error, root_status = fetch_text(BASE_URL)
    if root_error or not root_status or root_status >= 400:
        problems.append(("site down", root_error or f"HTTP {root_status}"))

    latest, latest_error, latest_status = fetch_json("data/latest.json")
    if latest_error:
        problems.append(("latest JSON invalid", latest_error))

    index, index_error, index_status = fetch_json("data/index.json")
    if index_error:
        problems.append(("index JSON invalid", index_error))

    latest_dt = None
    index_dt = None
    newest_recent_dt = None
    oldest_recent_dt = None
    age_minutes = None
    snapshot_count = 0
    ranges: list[str] = []
    commodity_count = 0

    if latest:
        try:
            latest_dt = parse_dt(latest.get("generated_at"))
        except Exception as exc:
            problems.append(("latest JSON invalid", f"generated_at invalid: {exc}"))

        commodities = latest.get("market", {}).get("commodities", [])
        commodity_count = len(commodities) if isinstance(commodities, list) else 0
        if commodity_count != EXPECTED_COMMODITIES:
            warnings.append(("partial feed", f"expected {EXPECTED_COMMODITIES} commodities, got {commodity_count}"))

    if index:
        try:
            index_dt = parse_dt(index.get("generated_at"))
        except Exception as exc:
            warnings.append(("index JSON invalid", f"generated_at invalid: {exc}"))

        recent = index.get("recent", [])
        if isinstance(recent, list):
            snapshot_count = len(recent)
            parsed_recent = []
            for row in recent:
                if not isinstance(row, dict):
                    continue
                try:
                    parsed_recent.append(parse_dt(row.get("generated_at")))
                except Exception:
                    continue

            if parsed_recent:
                newest_recent_dt = max(parsed_recent)
                oldest_recent_dt = min(parsed_recent)
        else:
            problems.append(("index JSON invalid", "recent is not a list"))

        raw_ranges = index.get("ranges", {}).get("available", [])
        ranges = [str(item) for item in raw_ranges] if isinstance(raw_ranges, list) else []
        if "1d" not in ranges:
            warnings.append(("range mismatch", "1d range is not advertised"))

        if oldest_recent_dt and newest_recent_dt:
            span_seconds = (newest_recent_dt - oldest_recent_dt).total_seconds()
            if span_seconds >= 7 * 24 * 60 * 60 and "7d" not in ranges:
                warnings.append(("range mismatch", "7d source span exists but 7d range is not advertised"))

    freshness_dt = latest_dt or newest_recent_dt
    if freshness_dt:
        age_minutes = max(0, (datetime.now(timezone.utc) - freshness_dt).total_seconds() / 60)
        if age_minutes > CRITICAL_AFTER_MINUTES:
            problems.append(("data delayed", f"critical: newest data is {format_age(age_minutes)} old"))
        elif age_minutes > ALERT_AFTER_MINUTES:
            warnings.append(("data delayed", f"alert: newest data is {format_age(age_minutes)} old"))
        elif age_minutes > WARN_AFTER_MINUTES:
            warnings.append(("data delayed", f"warning: newest data is {format_age(age_minutes)} old"))
    elif latest or index:
        problems.append(("data delayed", "could not determine newest timestamp"))

    print("Idle Hacking public market health")
    print(f"site: {BASE_URL} ({root_status or 'no status'})")
    print(f"latest.json: HTTP {latest_status or 'n/a'} generated_at={latest_dt.isoformat() if latest_dt else 'invalid'}")
    print(f"index.json: HTTP {index_status or 'n/a'} generated_at={index_dt.isoformat() if index_dt else 'invalid'}")
    print(f"newest recent snapshot: {newest_recent_dt.isoformat() if newest_recent_dt else 'unknown'}")
    print(f"age: {format_age(age_minutes)}")
    print(f"snapshots: {snapshot_count}")
    print(f"ranges: {', '.join(ranges) or 'none'}")
    print(f"commodities: {commodity_count}/{EXPECTED_COMMODITIES}")

    if problems:
        print("\nFailures:")
        for label, detail in problems:
            print(f"- {label}: {detail}")

    if warnings:
        print("\nWarnings:")
        for label, detail in warnings:
            print(f"- {label}: {detail}")

    if problems:
        return 2

    if warnings:
        return 1

    print("\nOK: live public market data is fresh enough.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
