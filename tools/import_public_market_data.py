#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]

CLOUD_SOURCE = os.environ.get("MARKET_CLOUD_SOURCE", "scraper@46.224.146.164:/home/scraper/data/market/")
STAGING_DIR = ROOT / "_internal" / "data" / "market" / "cloud"
PUBLIC_DATA_DIR = ROOT / "site" / "public" / "data"
PUBLIC_RECENT_DIR = PUBLIC_DATA_DIR / "snapshots" / "recent"
PUBLIC_HISTORY_DIR = PUBLIC_DATA_DIR / "history"
PUBLIC_HISTORY_COMMODITIES_DIR = PUBLIC_HISTORY_DIR / "commodities"

HISTORY_FIELDS = [
    "bestBidCents",
    "bestAskCents",
    "midPriceCents",
    "spreadCents",
    "spreadPct",
    "bidVolumeQty",
    "askVolumeQty",
    "volumeQty",
    "bestBidQty",
    "bestAskQty",
    "bidLevelCount",
    "askLevelCount",
]

HISTORY_RANGE_CONFIG = {
    "1d": {"span_seconds": 24 * 60 * 60, "bucket_seconds": None, "bucket": "15m"},
    "7d": {"span_seconds": 7 * 24 * 60 * 60, "bucket_seconds": 60 * 60, "bucket": "1h"},
    "30d": {"span_seconds": 30 * 24 * 60 * 60, "bucket_seconds": 6 * 60 * 60, "bucket": "6h"},
    "all": {"span_seconds": None, "bucket_seconds": 24 * 60 * 60, "bucket": "1d"},
}

FORBIDDEN_EXACT_KEYS = {
    "chat",
    "chat_message",
    "discord_message",
    "message_text",
    "content",
    "body",
    "username",
    "player",
    "current_player",
    "top_entries",
    "credits",
    "holdings",
    "holdingsQty",
    "holdingsValueCents",
    "orders",
    "buyAllBest",
    "sellAllBest",
    "cookie",
    "token",
    "secret",
    "authorization",
    "session",
    "profile",
}

HIGH_RISK_KEY_SUBSTRINGS = (
    "cookie",
    "token",
    "secret",
    "authorization",
    "bearer",
    "session",
)


def parse_dt(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing/non-string datetime")

    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    dt = datetime.fromisoformat(normalized)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def iso_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def compact_z(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def dump_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def finite_number(value: Any) -> int | float | None:
    if isinstance(value, bool):
        return None

    try:
        number = float(value)
    except (TypeError, ValueError):
        return None

    if not math.isfinite(number):
        return None

    return int(number) if number.is_integer() else number


def pull_cloud() -> dict[str, Any]:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)

    rsync = shutil.which("rsync")
    scp = shutil.which("scp")

    if rsync:
        cmd = [rsync, "-az", CLOUD_SOURCE, str(STAGING_DIR) + "/"]
        method = "rsync"
    elif scp:
        cmd = [scp, "-r", CLOUD_SOURCE, str(STAGING_DIR)]
        method = "scp"
    else:
        return {
            "success": False,
            "method": None,
            "returncode": 127,
            "stdout": "",
            "stderr": "neither rsync nor scp available",
        }

    proc = subprocess.run(cmd, cwd=ROOT, text=True, capture_output=True)

    return {
        "success": proc.returncode == 0,
        "method": method,
        "returncode": proc.returncode,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
    }


def get_candidate_files() -> list[Path]:
    files: list[Path] = []
    seen: set[Path] = set()

    def add(path: Path) -> None:
        if path.exists() and path not in seen:
            seen.add(path)
            files.append(path)

    add(STAGING_DIR / "latest.json")

    for pattern in (
        "snapshots/recent/*.json",
        "archive/*.json",
        "receipts/*.json",
    ):
        for path in sorted(STAGING_DIR.glob(pattern)):
            add(path)

    for path in sorted(PUBLIC_RECENT_DIR.glob("*.json")):
        add(path)

    return files


def safety_scan(value: Any, path: str = "$") -> list[str]:
    errors: list[str] = []

    if isinstance(value, dict):
        for key, child in value.items():
            here = f"{path}.{key}"

            if key == "rankings":
                if child is not None:
                    errors.append(f"{here}: rankings must be null")
                continue

            if key in FORBIDDEN_EXACT_KEYS:
                errors.append(f"{here}: forbidden key {key!r}")

            lower = key.lower()
            for needle in HIGH_RISK_KEY_SUBSTRINGS:
                if needle in lower:
                    errors.append(f"{here}: high-risk key substring {needle!r}")

            errors.extend(safety_scan(child, here))

    elif isinstance(value, list):
        for i, child in enumerate(value):
            errors.extend(safety_scan(child, f"{path}[{i}]"))

    return errors


def validate_feed(path: Path) -> tuple[dict[str, Any] | None, datetime | None, list[str]]:
    errors: list[str] = []

    try:
        feed = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, None, [f"invalid json: {exc}"]

    if not isinstance(feed, dict):
        return None, None, ["top-level value is not object"]

    if feed.get("type") != "idlehacking_public_market_feed":
        errors.append("type is not idlehacking_public_market_feed")

    if feed.get("schema_version") != 1:
        errors.append("schema_version is not 1")

    generated_dt = None
    try:
        generated_dt = parse_dt(feed.get("generated_at"))
    except Exception as exc:
        errors.append(f"generated_at invalid: {exc}")

    market = feed.get("market")
    if not isinstance(market, dict):
        errors.append("market missing/not object")
    else:
        if market.get("type") != "market_public_snapshot":
            errors.append("market.type is not market_public_snapshot")

        if market.get("scope") != "stackables_commodities_only":
            errors.append("market.scope is not stackables_commodities_only")

        if not isinstance(market.get("commodities"), list):
            errors.append("market.commodities is not list")

    if not isinstance(feed.get("health"), dict):
        errors.append("health missing/not object")

    snapshots = feed.get("snapshots")
    if isinstance(snapshots, dict) and "rankings" in snapshots and snapshots.get("rankings") is not None:
        errors.append("snapshots.rankings must be null when present")

    errors.extend(safety_scan(feed))

    return (feed if not errors else None), (generated_dt if not errors else None), errors


def commodity_count(feed: dict[str, Any]) -> int:
    commodities = feed.get("market", {}).get("commodities", [])
    return len(commodities) if isinstance(commodities, list) else 0


def commodities_with_books(feed: dict[str, Any]) -> int:
    commodities = feed.get("market", {}).get("commodities", [])
    if not isinstance(commodities, list):
        return 0
    return sum(1 for row in commodities if isinstance(row, dict) and row.get("hasBook") is True)


def index_row(feed: dict[str, Any], generated_dt: datetime) -> dict[str, Any]:
    health = feed.get("health") if isinstance(feed.get("health"), dict) else {}
    market = feed.get("market") if isinstance(feed.get("market"), dict) else {}

    return {
        "path": f"snapshots/recent/{compact_z(generated_dt)}.json",
        "generated_at": iso_z(generated_dt),
        "market_captured_at": market.get("captured_at") or health.get("last_market_capture_at") or None,
        "commodity_count": commodity_count(feed),
        "commodities_with_books": commodities_with_books(feed),
        "pricing_status": health.get("pricing_status", "missing"),
        "volume_status": health.get("volume_status", "missing"),
    }


def build_ranges(valid_items: list[tuple[Path, dict[str, Any], datetime]]) -> dict[str, Any]:
    available: list[str] = []

    if valid_items:
        dts = sorted(dt for _, _, dt in valid_items)
        span_seconds = (dts[-1] - dts[0]).total_seconds()

        available.append("1d")
        if span_seconds >= 7 * 24 * 60 * 60:
            available.append("7d")
        if span_seconds >= 30 * 24 * 60 * 60:
            available.append("30d")
        available.append("all")

    return {
        "available": available,
        "default": "1d" if valid_items else None,
        "has_1d": bool(valid_items),
        "has_7d": "7d" in available,
        "has_30d": "30d" in available,
        "has_all": "all" in available,
    }


def largest_gap_seconds(points: list[dict[str, Any]]) -> int | None:
    stamps: list[datetime] = []

    for point in points:
        try:
            stamps.append(parse_dt(point.get("t")))
        except Exception:
            continue

    stamps.sort()
    if len(stamps) < 2:
        return None

    return int(max((right - left).total_seconds() for left, right in zip(stamps, stamps[1:])))


def recompute_spread_pct(best_bid: int | float | None, best_ask: int | float | None) -> float | None:
    if best_bid is None or best_ask is None:
        return None
    if best_ask <= 0 or best_ask < best_bid:
        return None
    return ((best_ask - best_bid) / best_ask) * 100


def build_history_point(row: dict[str, Any], generated_dt: datetime, source_snapshot: str) -> dict[str, Any] | None:
    best_bid = finite_number(row.get("bestBidCents"))
    best_ask = finite_number(row.get("bestAskCents"))
    mid_price = finite_number(row.get("midPriceCents"))

    if mid_price is None and best_bid is not None and best_ask is not None:
        mid_price = (best_bid + best_ask) / 2

    if mid_price is None and best_bid is not None:
        mid_price = best_bid

    if mid_price is None and best_ask is not None:
        mid_price = best_ask

    if mid_price is None:
        return None

    spread_cents = None
    if best_bid is not None and best_ask is not None and best_ask >= best_bid:
        spread_cents = best_ask - best_bid

    point: dict[str, Any] = {
        "t": iso_z(generated_dt),
        "bestBidCents": best_bid,
        "bestAskCents": best_ask,
        "midPriceCents": mid_price,
        "spreadCents": spread_cents,
        "spreadPct": recompute_spread_pct(best_bid, best_ask),
        "bidVolumeQty": finite_number(row.get("bidVolumeQty")),
        "askVolumeQty": finite_number(row.get("askVolumeQty")),
        "volumeQty": finite_number(row.get("volumeQty")),
        "bestBidQty": finite_number(row.get("bestBidQty")),
        "bestAskQty": finite_number(row.get("bestAskQty")),
        "bidLevelCount": finite_number(row.get("bidLevelCount")),
        "askLevelCount": finite_number(row.get("askLevelCount")),
        "source": "collector_snapshot",
        "sourceSnapshot": source_snapshot,
    }

    return point


def downsample_points(points: list[dict[str, Any]], bucket_seconds: int | None) -> list[dict[str, Any]]:
    if not bucket_seconds:
        return points

    buckets: dict[int, dict[str, Any]] = {}

    for point in points:
        try:
            stamp = parse_dt(point.get("t")).timestamp()
        except Exception:
            continue

        bucket = int(stamp // bucket_seconds)
        buckets[bucket] = point

    return [buckets[key] for key in sorted(buckets)]


def filter_range_points(
    points: list[dict[str, Any]],
    newest_dt: datetime,
    range_name: str,
    config: dict[str, Any],
) -> list[dict[str, Any]]:
    span_seconds = config.get("span_seconds")
    filtered = points

    if span_seconds is not None:
        cutoff = newest_dt.timestamp() - int(span_seconds)
        filtered = [
            point for point in points
            if parse_dt(point.get("t")).timestamp() >= cutoff
        ]

    return downsample_points(filtered, config.get("bucket_seconds"))


def build_compact_history(valid_items: list[tuple[Path, dict[str, Any], datetime]]) -> tuple[list[str], dict[str, Any] | None]:
    if not valid_items:
        return [], None

    valid_items = sorted(valid_items, key=lambda item: item[2])
    ranges = build_ranges(valid_items).get("available", [])
    newest_dt = valid_items[-1][2]
    generated_at = iso_z(datetime.now(timezone.utc))
    by_commodity: dict[str, dict[str, Any]] = {}
    written: list[str] = []

    for _, feed, generated_dt in valid_items:
        source_snapshot = f"snapshots/recent/{compact_z(generated_dt)}.json"
        commodities = feed.get("market", {}).get("commodities", [])
        if not isinstance(commodities, list):
            continue

        for row in commodities:
            if not isinstance(row, dict):
                continue

            commodity_id = str(row.get("id") or "").strip()
            if not commodity_id:
                continue

            point = build_history_point(row, generated_dt, source_snapshot)
            if point is None:
                continue

            commodity = by_commodity.setdefault(commodity_id, {
                "id": commodity_id,
                "label": row.get("label") or commodity_id,
                "isEssence": bool(row.get("isEssence")),
                "points": [],
            })

            commodity["label"] = row.get("label") or commodity["label"]
            commodity["isEssence"] = bool(row.get("isEssence"))
            commodity["points"].append(point)

    if PUBLIC_HISTORY_DIR.exists():
        shutil.rmtree(PUBLIC_HISTORY_DIR)

    history_index: dict[str, Any] = {
        "type": "idlehacking_market_history_index",
        "schema_version": 1,
        "generated_at": generated_at,
        "source": "collector_snapshot",
        "ranges": ranges,
        "fields": HISTORY_FIELDS,
        "commodities": {},
    }

    for commodity_id in sorted(by_commodity):
        commodity = by_commodity[commodity_id]
        points = sorted(commodity["points"], key=lambda point: point["t"])
        if not points:
            continue

        commodity_ranges: dict[str, Any] = {}

        for range_name in ranges:
            config = HISTORY_RANGE_CONFIG.get(range_name)
            if not config:
                continue

            range_points = filter_range_points(points, newest_dt, range_name, config)
            if not range_points:
                continue

            commodity_ranges[range_name] = {
                "bucket": config["bucket"],
                "earliest": range_points[0]["t"],
                "latest": range_points[-1]["t"],
                "point_count": len(range_points),
                "largest_gap_seconds": largest_gap_seconds(range_points),
                "points": range_points,
            }

        if not commodity_ranges:
            continue

        commodity_doc = {
            "type": "idlehacking_market_commodity_history",
            "schema_version": 1,
            "generated_at": generated_at,
            "source": "collector_snapshot",
            "commodity": {
                "id": commodity_id,
                "label": commodity["label"],
                "isEssence": commodity["isEssence"],
            },
            "fields": HISTORY_FIELDS,
            "ranges": commodity_ranges,
        }

        commodity_path = PUBLIC_HISTORY_COMMODITIES_DIR / f"{commodity_id}.json"
        dump_json(commodity_path, commodity_doc)
        written.append(str(commodity_path.relative_to(ROOT)))

        all_points = commodity_ranges.get("all", {}).get("points") or points
        history_index["commodities"][commodity_id] = {
            "id": commodity_id,
            "label": commodity["label"],
            "isEssence": commodity["isEssence"],
            "path": f"commodities/{commodity_id}.json",
            "ranges": list(commodity_ranges.keys()),
            "fields": HISTORY_FIELDS,
            "earliest": all_points[0]["t"],
            "latest": all_points[-1]["t"],
            "point_count": len(points),
            "largest_gap_seconds": largest_gap_seconds(points),
        }

    index_path = PUBLIC_HISTORY_DIR / "index.json"
    dump_json(index_path, history_index)
    written.append(str(index_path.relative_to(ROOT)))

    return written, history_index


def write_public_data(valid_items: list[tuple[Path, dict[str, Any], datetime]]) -> tuple[list[str], dict[str, Any] | None]:
    if not valid_items:
        return [], None

    valid_items = sorted(valid_items, key=lambda item: item[2])
    newest_path, newest_feed, newest_dt = valid_items[-1]

    written: list[str] = []

    latest_path = PUBLIC_DATA_DIR / "latest.json"
    dump_json(latest_path, newest_feed)
    written.append(str(latest_path.relative_to(ROOT)))

    recent_rows = []
    for _, feed, generated_dt in valid_items:
        snap_path = PUBLIC_RECENT_DIR / f"{compact_z(generated_dt)}.json"
        dump_json(snap_path, feed)
        written.append(str(snap_path.relative_to(ROOT)))
        recent_rows.append(index_row(feed, generated_dt))

    recent_rows.sort(key=lambda row: row["generated_at"], reverse=True)

    index = {
        "type": "idlehacking_market_data_index",
        "schema_version": 1,
        "generated_at": iso_z(datetime.now(timezone.utc)),
        "latest": "latest.json",
        "recent": recent_rows,
        "ranges": build_ranges(valid_items),
    }

    index_path = PUBLIC_DATA_DIR / "index.json"
    dump_json(index_path, index)
    written.append(str(index_path.relative_to(ROOT)))

    history_written, _ = build_compact_history(valid_items)
    written.extend(history_written)

    return written, index


def run(no_pull: bool) -> tuple[dict[str, Any], int]:
    pull = {
        "success": True,
        "method": "skipped",
        "returncode": 0,
        "stdout": "",
        "stderr": "",
    } if no_pull else pull_cloud()

    candidates = get_candidate_files()
    valid_by_key: dict[str, tuple[Path, dict[str, Any], datetime]] = {}
    rejected: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for path in candidates:
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            raw = None

        if (
            isinstance(raw, dict)
            and set(raw.keys()).issubset({"created_at", "file", "message_count", "sha256"})
            and "sha256" in raw
            and "file" in raw
        ):
            skipped.append({
                "path": str(path.relative_to(ROOT)),
                "reason": "receipt metadata, not a feed snapshot",
            })
            continue

        feed, generated_dt, errors = validate_feed(path)
        if feed is not None and generated_dt is not None:
            dedupe_key = iso_z(generated_dt)
            if dedupe_key not in valid_by_key:
                valid_by_key[dedupe_key] = (path, feed, generated_dt)
        else:
            rejected.append({
                "path": str(path.relative_to(ROOT)),
                "reasons": errors,
            })

    valid = sorted(valid_by_key.values(), key=lambda item: item[2])
    written: list[str] = []
    index: dict[str, Any] | None = None

    if pull["success"] and valid:
        written, index = write_public_data(valid)

    newest = max((dt for _, _, dt in valid), default=None)
    ranges = index["ranges"] if index else build_ranges(valid)

    summary = {
        "cloud_pull": pull,
        "candidate_files": len(candidates),
        "valid": len(valid),
        "rejected": len(rejected),
        "skipped": len(skipped),
        "newest_generated_at": iso_z(newest) if newest else None,
        "files_written": written,
        "available_ranges": ranges.get("available", []),
        "ranges": ranges,
        "rejected_files": rejected,
        "skipped_files": skipped,
    }

    exit_code = 0
    if not pull["success"]:
        exit_code = 2
    elif not valid:
        exit_code = 3
    elif rejected:
        exit_code = 1

    return summary, exit_code


def print_human(summary: dict[str, Any]) -> None:
    pull = summary["cloud_pull"]

    print(f"cloud pull success: {pull['success']} ({pull['method']})")
    if pull.get("stderr"):
        print(f"cloud pull stderr: {pull['stderr']}")

    print(f"candidate files: {summary['candidate_files']}")
    print(f"valid: {summary['valid']}")
    print(f"rejected: {summary['rejected']}")
    print(f"skipped metadata: {summary['skipped']}")
    print(f"newest generated_at: {summary['newest_generated_at']}")
    print(f"available ranges: {', '.join(summary['available_ranges']) or 'none'}")

    print("files written:")
    for path in summary["files_written"]:
        print(f"  - {path}")

    if summary["skipped_files"]:
        print("skipped files:")
        for item in summary["skipped_files"]:
            print(f"  - {item['path']}: {item['reason']}")

    if summary["rejected_files"]:
        print("rejected files:")
        for item in summary["rejected_files"]:
            print(f"  - {item['path']}")
            for reason in item["reasons"]:
                print(f"      {reason}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Import cloud Idle Hacking public market data into site/public/data.")
    parser.add_argument("--no-pull", action="store_true", help="Use local staged files only. Offline/regression use only; normal local refresh should use tools/update_local_market_site.py.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON summary.")
    args = parser.parse_args()

    summary, exit_code = run(no_pull=args.no_pull)

    if args.json:
        print(json.dumps(summary, indent=2, ensure_ascii=False))
    else:
        print_human(summary)

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
