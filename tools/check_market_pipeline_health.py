#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
BASE_URL = "https://swampdad.github.io/idle-hacking-companion/"
REPO = "SwampDad/idle-hacking-companion"
UPDATE_WORKFLOW = "update-market-data.yml"
EXPECTED_COMMODITIES = 16
OK_AFTER_MINUTES = 90
STALE_AFTER_MINUTES = 180
CRITICAL_AFTER_MINUTES = 360
HTTP_TIMEOUT_SECONDS = 20
COMMAND_TIMEOUT_SECONDS = 20
TIMESTAMP_ALIGNMENT_SECONDS = 5 * 60
DEFAULT_VPS_SSH_HOST = "ih-market-vps"


def vps_ssh_host() -> str:
    return os.environ.get("IH_MARKET_VPS_SSH_HOST", DEFAULT_VPS_SSH_HOST).strip() or DEFAULT_VPS_SSH_HOST


def manual_ssh_command(host: str, remote_command: str) -> str:
    return f"ssh {host} {json.dumps(remote_command)}"


def parse_dt(value: Any) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("missing/non-string datetime")

    text = value.strip()
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    dt = datetime.fromisoformat(normalized)

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.astimezone(timezone.utc)


def iso_or_unknown(value: datetime | None) -> str:
    return value.isoformat() if value else "unknown"


def age_minutes(dt: datetime | None) -> float | None:
    if not dt:
        return None
    return max(0, (datetime.now(timezone.utc) - dt).total_seconds() / 60)


def format_age(minutes: float | None) -> str:
    if minutes is None:
        return "unknown"
    if minutes < 60:
        return f"{minutes:.0f}m"
    hours = int(minutes // 60)
    rem = int(minutes % 60)
    return f"{hours}h {rem}m" if rem else f"{hours}h"


def freshness_level(minutes: float | None) -> str:
    if minutes is None:
        return "BROKEN"
    if minutes > CRITICAL_AFTER_MINUTES:
        return "CRITICAL"
    if minutes > STALE_AFTER_MINUTES:
        return "STALE"
    if minutes > OK_AFTER_MINUTES:
        return "WARN"
    return "OK"


def fetch_text(url: str) -> tuple[str | None, str | None, int | None]:
    request = urllib.request.Request(url, headers={"User-Agent": "ih-market-pipeline-health/1.0"})

    try:
        with urllib.request.urlopen(request, timeout=HTTP_TIMEOUT_SECONDS) as response:
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


def load_local_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, str(exc)

    if not isinstance(data, dict):
        return None, "top-level value is not an object"

    return data, None


def index_summary(index: dict[str, Any] | None) -> dict[str, Any]:
    if not index:
        return {
            "generated_at": None,
            "newest_recent": None,
            "oldest_recent": None,
            "snapshot_count": 0,
            "ranges": [],
        }

    generated_at = None
    try:
        generated_at = parse_dt(index.get("generated_at"))
    except Exception:
        pass

    parsed_recent: list[datetime] = []
    recent = index.get("recent", [])
    if isinstance(recent, list):
        for row in recent:
            if not isinstance(row, dict):
                continue
            try:
                parsed_recent.append(parse_dt(row.get("generated_at")))
            except Exception:
                continue

    ranges = index.get("ranges", {}).get("available", [])
    if not isinstance(ranges, list):
        ranges = []

    return {
        "generated_at": generated_at,
        "newest_recent": max(parsed_recent) if parsed_recent else None,
        "oldest_recent": min(parsed_recent) if parsed_recent else None,
        "snapshot_count": len(recent) if isinstance(recent, list) else 0,
        "ranges": [str(item) for item in ranges],
    }


def commodity_count(feed: dict[str, Any] | None) -> int:
    commodities = feed.get("market", {}).get("commodities", []) if feed else []
    return len(commodities) if isinstance(commodities, list) else 0


def validate_feed_schema(feed: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not feed:
        return ["missing feed"]
    if feed.get("type") != "idlehacking_public_market_feed":
        errors.append("type is not idlehacking_public_market_feed")
    if feed.get("schema_version") != 1:
        errors.append("schema_version is not 1")
    if not isinstance(feed.get("market"), dict):
        errors.append("market missing/not object")
    elif not isinstance(feed.get("market", {}).get("commodities"), list):
        errors.append("market.commodities missing/not list")
    return errors


def validate_index_schema(index: dict[str, Any] | None) -> list[str]:
    errors: list[str] = []
    if not index:
        return ["missing index"]
    if index.get("type") != "idlehacking_market_data_index":
        errors.append("type is not idlehacking_market_data_index")
    if index.get("schema_version") != 1:
        errors.append("schema_version is not 1")
    if not isinstance(index.get("recent"), list):
        errors.append("recent missing/not list")
    if not isinstance(index.get("ranges"), dict):
        errors.append("ranges missing/not object")
    return errors


def run_command(cmd: list[str], timeout: int = COMMAND_TIMEOUT_SECONDS) -> tuple[int | None, str, str]:
    try:
        proc = subprocess.run(cmd, text=True, capture_output=True, timeout=timeout, cwd=ROOT)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired as exc:
        return None, exc.stdout or "", f"timed out after {timeout}s"
    except Exception as exc:
        return None, "", str(exc)


def ssh_command(host: str, remote_command: str) -> list[str]:
    return [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=8",
        host,
        remote_command,
    ]


def check_live() -> dict[str, Any]:
    result: dict[str, Any] = {
        "status": "OK",
        "problems": [],
        "warnings": [],
    }

    _, root_error, root_status = fetch_text(BASE_URL)
    latest, latest_error, latest_status = fetch_json("data/latest.json")
    index, index_error, index_status = fetch_json("data/index.json")

    result.update({
        "root_status": root_status,
        "latest_status": latest_status,
        "index_status": index_status,
        "latest": latest,
        "index": index,
    })

    if root_error or not root_status or root_status >= 400:
        result["problems"].append(f"site down: {root_error or f'HTTP {root_status}'}")
    if latest_error:
        result["problems"].append(f"latest JSON invalid: {latest_error}")
    if index_error:
        result["problems"].append(f"index JSON invalid: {index_error}")

    result["problems"].extend(f"latest schema: {error}" for error in validate_feed_schema(latest))
    result["problems"].extend(f"index schema: {error}" for error in validate_index_schema(index))

    latest_dt = None
    try:
        latest_dt = parse_dt(latest.get("generated_at") if latest else None)
    except Exception as exc:
        result["problems"].append(f"latest.generated_at invalid: {exc}")

    summary = index_summary(index)
    index_dt = summary["generated_at"]
    newest_recent = summary["newest_recent"]
    count = commodity_count(latest)
    if count != EXPECTED_COMMODITIES:
        result["problems"].append(f"commodity count {count}/{EXPECTED_COMMODITIES}")

    if latest_dt and newest_recent:
        drift = abs((latest_dt - newest_recent).total_seconds())
        if drift > TIMESTAMP_ALIGNMENT_SECONDS:
            result["problems"].append(
                f"latest/index newest timestamp drift {int(drift)}s exceeds {TIMESTAMP_ALIGNMENT_SECONDS}s"
            )

    latest_age = age_minutes(latest_dt or newest_recent)
    level = freshness_level(latest_age)
    if level in {"STALE", "CRITICAL"}:
        result["warnings"].append(f"live data {level.lower()}: {format_age(latest_age)} old")
    elif level == "WARN":
        result["warnings"].append(f"live data delayed: {format_age(latest_age)} old")
    elif level == "BROKEN":
        result["problems"].append("could not determine live data age")

    if result["problems"]:
        result["status"] = "BROKEN"
    elif level in {"STALE", "CRITICAL"}:
        result["status"] = "STALE"
    elif result["warnings"]:
        result["status"] = "WARN"

    result.update({
        "latest_generated_at": latest_dt,
        "index_generated_at": index_dt,
        "newest_recent": newest_recent,
        "age_minutes": latest_age,
        "snapshot_count": summary["snapshot_count"],
        "ranges": summary["ranges"],
        "commodity_count": count,
    })
    return result


def check_local(live: dict[str, Any]) -> dict[str, Any]:
    latest_path = ROOT / "site" / "public" / "data" / "latest.json"
    index_path = ROOT / "site" / "public" / "data" / "index.json"
    latest, latest_error = load_local_json(latest_path)
    index, index_error = load_local_json(index_path)
    result: dict[str, Any] = {
        "status": "OK",
        "problems": [],
        "warnings": [],
    }

    if latest_error:
        result["problems"].append(f"local latest invalid: {latest_error}")
    if index_error:
        result["problems"].append(f"local index invalid: {index_error}")

    result["problems"].extend(f"local latest schema: {error}" for error in validate_feed_schema(latest))
    result["problems"].extend(f"local index schema: {error}" for error in validate_index_schema(index))

    latest_dt = None
    try:
        latest_dt = parse_dt(latest.get("generated_at") if latest else None)
    except Exception as exc:
        result["problems"].append(f"local latest.generated_at invalid: {exc}")

    summary = index_summary(index)
    local_age = age_minutes(latest_dt or summary["newest_recent"])
    live_dt = live.get("latest_generated_at") or live.get("newest_recent")
    older_than_live = bool(latest_dt and live_dt and latest_dt < live_dt)
    if older_than_live:
        result["warnings"].append("local bundled data is older than live Pages data")

    if local_age is not None and local_age > OK_AFTER_MINUTES:
        result["warnings"].append("Local bundled data is stale and localhost should not be trusted as live.")

    count = commodity_count(latest)
    if count != EXPECTED_COMMODITIES:
        result["warnings"].append(f"local commodity count {count}/{EXPECTED_COMMODITIES}")

    if result["problems"]:
        result["status"] = "BROKEN"
    elif result["warnings"]:
        result["status"] = "WARN"

    result.update({
        "latest_generated_at": latest_dt,
        "index_generated_at": summary["generated_at"],
        "newest_recent": summary["newest_recent"],
        "age_minutes": local_age,
        "snapshot_count": summary["snapshot_count"],
        "ranges": summary["ranges"],
        "commodity_count": count,
        "older_than_live": older_than_live,
    })
    return result


def check_github_actions() -> dict[str, Any]:
    if not shutil.which("gh"):
        return {
            "status": "SKIP",
            "problems": [],
            "warnings": ["gh unavailable"],
        }

    cmd = [
        "gh",
        "run",
        "list",
        "--repo",
        REPO,
        "--workflow",
        UPDATE_WORKFLOW,
        "--limit",
        "10",
        "--json",
        "databaseId,status,conclusion,event,createdAt,updatedAt,displayTitle",
    ]
    code, stdout, stderr = run_command(cmd)
    result: dict[str, Any] = {
        "status": "OK",
        "problems": [],
        "warnings": [],
        "command": " ".join(cmd),
    }

    if code != 0:
        result["status"] = "INCONCLUSIVE"
        result["warnings"].append(f"gh run list failed: {stderr or stdout or code}")
        return result

    try:
        runs = json.loads(stdout)
    except Exception as exc:
        result["status"] = "INCONCLUSIVE"
        result["warnings"].append(f"gh JSON parse failed: {exc}")
        return result

    if not isinstance(runs, list) or not runs:
        result["status"] = "INCONCLUSIVE"
        result["warnings"].append("no update workflow runs returned")
        return result

    latest = runs[0]
    completed = [run for run in runs if run.get("status") == "completed"]
    latest_completed = completed[0] if completed else None

    latest_created = None
    try:
        latest_created = parse_dt(latest.get("createdAt"))
    except Exception:
        pass
    latest_age = age_minutes(latest_created)

    result.update({
        "latest": latest,
        "latest_completed": latest_completed,
        "latest_age_minutes": latest_age,
    })

    if latest_completed and latest_completed.get("conclusion") != "success":
        result["status"] = "BROKEN"
        result["problems"].append(
            f"latest completed run failed: conclusion={latest_completed.get('conclusion')} "
            f"id={latest_completed.get('databaseId')}"
        )
        return result

    success_run = next(
        (run for run in runs if run.get("status") == "completed" and run.get("conclusion") == "success"),
        None,
    )
    if not success_run:
        result["status"] = "INCONCLUSIVE"
        result["warnings"].append("no recent successful completed update run found")
        return result

    try:
        success_dt = parse_dt(success_run.get("createdAt"))
    except Exception:
        success_dt = None

    success_age = age_minutes(success_dt)
    result["success_age_minutes"] = success_age
    if success_age is not None and success_age > STALE_AFTER_MINUTES:
        result["status"] = "STALE"
        result["warnings"].append(f"latest successful update run is {format_age(success_age)} old")
    elif success_age is not None and success_age > OK_AFTER_MINUTES:
        result["status"] = "WARN"
        result["warnings"].append(f"latest successful update run delayed: {format_age(success_age)} old")

    return result


def check_vps() -> dict[str, Any]:
    host = vps_ssh_host()
    latest_remote = "python3 -c \"import json; print(json.load(open('/home/scraper/data/market/latest.json')).get('generated_at'))\""
    health_remote = "curl -s http://127.0.0.1:8765/health"
    runtime_remote = (
        "python3 - <<'PY'\n"
        "import json, os, shutil, subprocess\n"
        "mem = {}\n"
        "with open('/proc/meminfo') as f:\n"
        "    for line in f:\n"
        "        k, v = line.split(':', 1)\n"
        "        mem[k] = int(v.strip().split()[0])\n"
        "disk = shutil.disk_usage('/home/scraper/data/market')\n"
        "chrome = subprocess.run(['pgrep', '-fa', 'chrome'], text=True, capture_output=True)\n"
        "helper = subprocess.run(['pgrep', '-fa', 'collector_helper.py'], text=True, capture_output=True)\n"
        "print(json.dumps({\n"
        "    'mem_total_mb': round(mem.get('MemTotal', 0) / 1024, 1),\n"
        "    'mem_available_mb': round(mem.get('MemAvailable', 0) / 1024, 1),\n"
        "    'swap_total_mb': round(mem.get('SwapTotal', 0) / 1024, 1),\n"
        "    'swap_free_mb': round(mem.get('SwapFree', 0) / 1024, 1),\n"
        "    'disk_total_gb': round(disk.total / (1024 ** 3), 2),\n"
        "    'disk_free_gb': round(disk.free / (1024 ** 3), 2),\n"
        "    'disk_used_pct': round((disk.used / disk.total) * 100, 1) if disk.total else None,\n"
        "    'chrome_process_count': len([line for line in chrome.stdout.splitlines() if line.strip()]),\n"
        "    'helper_process_count': len([line for line in helper.stdout.splitlines() if line.strip()]),\n"
        "}))\n"
        "PY"
    )
    result: dict[str, Any] = {
        "status": "INCONCLUSIVE",
        "problems": [],
        "warnings": [],
        "ssh_host": host,
        "manual_commands": [
            manual_ssh_command(host, latest_remote),
            manual_ssh_command(host, health_remote),
            manual_ssh_command(host, runtime_remote),
        ],
    }

    code, stdout, stderr = run_command(ssh_command(host, latest_remote))
    if code != 0:
        result["warnings"].append(f"VPS SSH unavailable: {stderr or stdout or code}")
        return result

    vps_dt = None
    try:
        vps_dt = parse_dt(stdout.strip())
    except Exception as exc:
        result["status"] = "BROKEN"
        result["problems"].append(f"VPS latest timestamp invalid: {exc}")
        return result

    health_code, health_stdout, health_stderr = run_command(ssh_command(host, health_remote))
    helper = None
    if health_code == 0 and health_stdout:
        try:
            helper = json.loads(health_stdout)
        except Exception as exc:
            result["warnings"].append(f"VPS helper health JSON invalid: {exc}")
    else:
        result["warnings"].append(f"VPS helper health unavailable: {health_stderr or health_stdout or health_code}")

    runtime_code, runtime_stdout, runtime_stderr = run_command(ssh_command(host, runtime_remote))
    runtime = None
    if runtime_code == 0 and runtime_stdout:
        try:
            runtime = json.loads(runtime_stdout)
        except Exception as exc:
            result["warnings"].append(f"VPS runtime JSON invalid: {exc}")
    else:
        result["warnings"].append(f"VPS runtime checks unavailable: {runtime_stderr or runtime_stdout or runtime_code}")

    vps_age = age_minutes(vps_dt)
    result.update({
        "status": "OK",
        "latest_generated_at": vps_dt,
        "age_minutes": vps_age,
        "helper": helper,
        "runtime": runtime,
    })

    if isinstance(runtime, dict):
        if runtime.get("chrome_process_count", 0) < 1:
            result["status"] = "WARN"
            result["warnings"].append("Chrome process not detected")
        if runtime.get("helper_process_count", 0) < 1:
            result["status"] = "WARN"
            result["warnings"].append("collector_helper.py process not detected")
        if runtime.get("swap_total_mb", 0) < 1:
            result["status"] = "WARN"
            result["warnings"].append("swap is not enabled")
        disk_used = runtime.get("disk_used_pct")
        if isinstance(disk_used, (int, float)) and disk_used >= 90:
            result["status"] = "WARN"
            result["warnings"].append(f"disk usage high: {disk_used}%")

    level = freshness_level(vps_age)
    if level in {"STALE", "CRITICAL"}:
        result["status"] = "STALE"
        result["warnings"].append(f"VPS source data {level.lower()}: {format_age(vps_age)} old")
    elif level == "WARN":
        result["status"] = "WARN"
        result["warnings"].append(f"VPS source data delayed: {format_age(vps_age)} old")

    return result


def print_section(title: str) -> None:
    print(f"\n== {title} ==")


def print_messages(result: dict[str, Any]) -> None:
    for problem in result.get("problems", []):
        print(f"FAIL: {problem}")
    for warning in result.get("warnings", []):
        print(f"WARN: {warning}")


def helper_summary(helper: Any) -> str:
    if not isinstance(helper, dict):
        return "unavailable"

    parts = []
    for key in ("status", "market", "pricing_status", "books", "commodities", "volume"):
        value = helper.get(key)
        if isinstance(value, dict):
            if "status" in value:
                parts.append(f"{key}.status={value.get('status')}")
            continue
        if value is not None:
            parts.append(f"{key}={value}")
    return ", ".join(parts) or "available"


def runtime_summary(runtime: Any) -> str:
    if not isinstance(runtime, dict):
        return "unavailable"

    return (
        f"mem_available={runtime.get('mem_available_mb', 'unknown')}MB/"
        f"{runtime.get('mem_total_mb', 'unknown')}MB, "
        f"swap_free={runtime.get('swap_free_mb', 'unknown')}MB/"
        f"{runtime.get('swap_total_mb', 'unknown')}MB, "
        f"disk_used={runtime.get('disk_used_pct', 'unknown')}%, "
        f"chrome_processes={runtime.get('chrome_process_count', 'unknown')}, "
        f"helper_processes={runtime.get('helper_process_count', 'unknown')}"
    )


def final_verdict(live: dict[str, Any], local: dict[str, Any], gha: dict[str, Any], vps: dict[str, Any]) -> tuple[str, str]:
    if live["status"] == "BROKEN" or gha["status"] == "BROKEN" or vps["status"] == "BROKEN":
        return "BROKEN", "Inspect the failed layer above before trusting market data."

    if live["status"] == "STALE":
        if vps["status"] == "INCONCLUSIVE":
            manual = (vps.get("manual_commands") or ["ssh ih-market-vps <check command>"])[0]
            return "STALE", f"Live data is stale and VPS is unknown. Run manually: {manual}"
        if vps["status"] in {"OK", "WARN"}:
            live_dt = live.get("latest_generated_at") or live.get("newest_recent")
            vps_dt = vps.get("latest_generated_at")
            if live_dt and vps_dt and vps_dt > live_dt:
                return "STALE", "VPS is fresher than live; trigger update workflow and inspect deploy."
            return "STALE", "Live and VPS/source data are stale; inspect collector browser/helper."
        return "STALE", "Live data is stale; inspect VPS and update workflow."

    if gha["status"] in {"STALE", "WARN"}:
        return "INCONCLUSIVE", "GitHub update cadence is delayed; inspect recent workflow runs."

    if gha["status"] in {"SKIP", "INCONCLUSIVE"}:
        return "INCONCLUSIVE", "GitHub Actions could not be verified enough; run gh workflow checks manually."

    if vps["status"] == "INCONCLUSIVE":
        manual = (vps.get("manual_commands") or ["ssh ih-market-vps <check command>"])[0]
        action = f"VPS could not be verified. Run manually: {manual}"
        if local.get("older_than_live"):
            action += " Local bundled data is stale; do not trust localhost as live."
        return "INCONCLUSIVE", action

    if vps["status"] in {"STALE", "WARN"}:
        return "STALE", "VPS/source data is delayed; inspect collector browser/helper."

    if live["status"] == "WARN":
        return "STALE", "Live data is valid but delayed; watch schedule or trigger workflow if it crosses 3h."

    if local.get("older_than_live"):
        return "TRUSTED", "Live pipeline looks trusted. Local bundled data is stale; pull origin or do not trust localhost."

    return "TRUSTED", "Live, GitHub Actions, VPS, and local bundled data are aligned enough to trust."


def json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: json_value(child) for key, child in value.items()}
    if isinstance(value, list):
        return [json_value(child) for child in value]
    return value


def section_status(value: str) -> str:
    if value == "BROKEN":
        return "FAIL"
    if value in {"STALE", "WARN"}:
        return "WARN"
    if value in {"OK", "SKIP", "INCONCLUSIVE"}:
        return value
    return "INCONCLUSIVE"


def messages(result: dict[str, Any]) -> list[str]:
    output: list[str] = []
    output.extend(f"FAIL: {item}" for item in result.get("problems", []))
    output.extend(f"WARN: {item}" for item in result.get("warnings", []))
    return output


def rounded_age(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return round(float(value), 2)
    except (TypeError, ValueError):
        return None


def verdict_status(verdict: str) -> str:
    if verdict == "TRUSTED":
        return "OK"
    if verdict == "BROKEN":
        return "FAIL"
    if verdict == "INCONCLUSIVE":
        return "INCONCLUSIVE"
    return "WARN"


def build_status_model(
    live: dict[str, Any],
    local: dict[str, Any],
    gha: dict[str, Any],
    vps: dict[str, Any],
    verdict: str,
    action: str,
) -> dict[str, Any]:
    live_dt = live.get("latest_generated_at")
    live_newest = live.get("newest_recent")
    vps_dt = vps.get("latest_generated_at")
    timestamp_drift_seconds = None
    if live_dt and live_newest:
        timestamp_drift_seconds = abs((live_dt - live_newest).total_seconds())

    latest_run = gha.get("latest") or {}
    latest_completed = gha.get("latest_completed") or {}

    model = {
        "live_pages": {
            "status": section_status(live["status"]),
            "root_http_status": live.get("root_status"),
            "latest_http_status": live.get("latest_status"),
            "index_http_status": live.get("index_status"),
            "latest_generated_at": live_dt,
            "index_generated_at": live.get("index_generated_at"),
            "newest_recent_at": live_newest,
            "age_minutes": rounded_age(live.get("age_minutes")),
            "snapshot_count": live.get("snapshot_count"),
            "ranges": live.get("ranges") or [],
            "commodity_count": live.get("commodity_count"),
            "expected_commodity_count": EXPECTED_COMMODITIES,
            "latest_index_drift_seconds": timestamp_drift_seconds,
            "messages": messages(live),
        },
        "local_data": {
            "status": section_status(local["status"]),
            "latest_generated_at": local.get("latest_generated_at"),
            "index_generated_at": local.get("index_generated_at"),
            "newest_recent_at": local.get("newest_recent"),
            "age_minutes": rounded_age(local.get("age_minutes")),
            "snapshot_count": local.get("snapshot_count"),
            "ranges": local.get("ranges") or [],
            "commodity_count": local.get("commodity_count"),
            "expected_commodity_count": EXPECTED_COMMODITIES,
            "older_than_live": local.get("older_than_live"),
            "localhost_trustworthy_as_live": not bool(local.get("older_than_live")),
            "messages": messages(local),
        },
        "github_actions": {
            "status": section_status(gha["status"]),
            "workflow": UPDATE_WORKFLOW,
            "latest_run": {
                "id": latest_run.get("databaseId"),
                "status": latest_run.get("status"),
                "conclusion": latest_run.get("conclusion"),
                "event": latest_run.get("event"),
                "created_at": latest_run.get("createdAt"),
                "updated_at": latest_run.get("updatedAt"),
                "age_minutes": rounded_age(gha.get("latest_age_minutes")),
            } if latest_run else None,
            "latest_completed_run": {
                "id": latest_completed.get("databaseId"),
                "status": latest_completed.get("status"),
                "conclusion": latest_completed.get("conclusion"),
                "event": latest_completed.get("event"),
                "created_at": latest_completed.get("createdAt"),
                "updated_at": latest_completed.get("updatedAt"),
            } if latest_completed else None,
            "latest_success_age_minutes": rounded_age(gha.get("success_age_minutes")),
            "command": gha.get("command"),
            "messages": messages(gha),
        },
        "vps": {
            "status": section_status(vps["status"]),
            "ssh_host": vps.get("ssh_host") or vps_ssh_host(),
            "latest_generated_at": vps_dt,
            "age_minutes": rounded_age(vps.get("age_minutes")),
            "helper": vps.get("helper"),
            "runtime": vps.get("runtime"),
            "manual_commands": vps.get("manual_commands") or [],
            "messages": messages(vps),
        },
        "cross_layer": {
            "status": verdict_status(verdict),
            "live_latest_matches_index_newest": timestamp_drift_seconds is not None
            and timestamp_drift_seconds <= TIMESTAMP_ALIGNMENT_SECONDS,
            "timestamp_alignment_threshold_seconds": TIMESTAMP_ALIGNMENT_SECONDS,
            "local_older_than_live": local.get("older_than_live"),
            "github_actions_checked": gha["status"] not in {"SKIP", "INCONCLUSIVE"},
            "vps_checked": vps["status"] != "INCONCLUSIVE",
            "price_differences_used_for_verdict": False,
            "messages": [action],
        },
        "verdict": verdict,
        "next_action": action,
    }

    return json_value(model)


def print_human(live: dict[str, Any], local: dict[str, Any], gha: dict[str, Any], vps: dict[str, Any], verdict: str, action: str) -> None:
    print("Idle Hacking market pipeline health")

    print_section("Live GitHub Pages")
    print(f"status: {live['status']}")
    print(f"root HTTP: {live.get('root_status') or 'n/a'}")
    print(f"latest HTTP: {live.get('latest_status') or 'n/a'} generated_at={iso_or_unknown(live.get('latest_generated_at'))}")
    print(f"index HTTP: {live.get('index_status') or 'n/a'} generated_at={iso_or_unknown(live.get('index_generated_at'))}")
    print(f"newest index recent: {iso_or_unknown(live.get('newest_recent'))}")
    print(f"age: {format_age(live.get('age_minutes'))}")
    print(f"snapshots: {live.get('snapshot_count')}")
    print(f"ranges: {', '.join(live.get('ranges') or []) or 'none'}")
    print(f"commodities: {live.get('commodity_count')}/{EXPECTED_COMMODITIES}")
    print_messages(live)

    print_section("Local Bundled Data")
    print(f"status: {local['status']}")
    print(f"latest generated_at: {iso_or_unknown(local.get('latest_generated_at'))}")
    print(f"index generated_at: {iso_or_unknown(local.get('index_generated_at'))}")
    print(f"newest index recent: {iso_or_unknown(local.get('newest_recent'))}")
    print(f"age: {format_age(local.get('age_minutes'))}")
    print(f"snapshots: {local.get('snapshot_count')}")
    print(f"ranges: {', '.join(local.get('ranges') or []) or 'none'}")
    print(f"commodities: {local.get('commodity_count')}/{EXPECTED_COMMODITIES}")
    print(f"older than live: {local.get('older_than_live')}")
    print_messages(local)

    print_section("GitHub Actions")
    print(f"status: {gha['status']}")
    latest = gha.get("latest") or {}
    if latest:
        print(
            "latest run: "
            f"id={latest.get('databaseId')} status={latest.get('status')} "
            f"conclusion={latest.get('conclusion')} event={latest.get('event')} "
            f"createdAt={latest.get('createdAt')} age={format_age(gha.get('latest_age_minutes'))}"
        )
    if gha.get("success_age_minutes") is not None:
        print(f"latest successful run age: {format_age(gha.get('success_age_minutes'))}")
    print_messages(gha)

    print_section("VPS Source")
    print(f"status: {vps['status']}")
    print(f"ssh host: {vps.get('ssh_host') or vps_ssh_host()}")
    print(f"latest generated_at: {iso_or_unknown(vps.get('latest_generated_at'))}")
    print(f"age: {format_age(vps.get('age_minutes'))}")
    print(f"helper health: {helper_summary(vps.get('helper'))}")
    print(f"runtime: {runtime_summary(vps.get('runtime'))}")
    print_messages(vps)
    if vps["status"] == "INCONCLUSIVE":
        print("manual commands:")
        for command in vps.get("manual_commands", []):
            print(f"  {command}")

    print_section("Final Verdict")
    print(f"verdict: {verdict}")
    print(f"next action: {action}")


def exit_code_for(verdict: str) -> int:
    if verdict == "BROKEN":
        return 2
    if verdict in {"STALE", "INCONCLUSIVE"}:
        return 1
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Check Idle Hacking market pipeline health.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON status.")
    args = parser.parse_args()

    live = check_live()
    local = check_local(live)
    gha = check_github_actions()
    vps = check_vps()
    verdict, action = final_verdict(live, local, gha, vps)

    if args.json:
        print(json.dumps(build_status_model(live, local, gha, vps, verdict, action), indent=2, ensure_ascii=False))
    else:
        print_human(live, local, gha, vps, verdict, action)

    return exit_code_for(verdict)


if __name__ == "__main__":
    sys.exit(main())
