#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_VPS_SOURCE = "ih-market-vps:/home/scraper/data/market/"
DEV_URL = "http://127.0.0.1:5173/"


def run_streamed(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> None:
    print()
    print(f"== {' '.join(cmd)} ==")
    proc = subprocess.run(cmd, cwd=cwd, env=env)
    if proc.returncode != 0:
        raise SystemExit(f"command failed with exit {proc.returncode}: {' '.join(cmd)}")


def run_captured(cmd: list[str], *, cwd: Path, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, env=env, text=True, capture_output=True)


def checker_summary(payload: dict[str, Any]) -> str:
    live = payload.get("live_pages") if isinstance(payload.get("live_pages"), dict) else {}
    local = payload.get("local_data") if isinstance(payload.get("local_data"), dict) else {}
    vps = payload.get("vps") if isinstance(payload.get("vps"), dict) else {}
    github = payload.get("github_actions") if isinstance(payload.get("github_actions"), dict) else {}

    lines = [
        f"verdict: {payload.get('verdict')}",
        f"live: {live.get('status')} age={live.get('age_minutes')}m latest={live.get('latest_generated_at')}",
        f"local: {local.get('status')} age={local.get('age_minutes')}m latest={local.get('latest_generated_at')}",
        f"github: {github.get('status')}",
        f"vps: {vps.get('status')} age={vps.get('age_minutes')}m latest={vps.get('latest_generated_at')}",
        f"next action: {payload.get('next_action')}",
    ]

    return "\n".join(lines)


def run_checker(env: dict[str, str]) -> dict[str, Any]:
    print()
    print("== python3 tools/check_market_pipeline_health.py --json ==")
    proc = run_captured(
        ["python3", "tools/check_market_pipeline_health.py", "--json"],
        cwd=ROOT,
        env=env,
    )

    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)

    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout.strip())
        raise SystemExit(f"operator checker failed with exit {proc.returncode}")

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(proc.stdout)
        raise SystemExit(f"operator checker did not return valid JSON: {exc}") from exc

    print(checker_summary(payload))

    verdict = payload.get("verdict")
    local = payload.get("local_data") if isinstance(payload.get("local_data"), dict) else {}
    local_status = local.get("status")
    localhost_trustworthy = local.get("localhost_trustworthy_as_live")

    if verdict != "TRUSTED":
        raise SystemExit("operator checker did not return TRUSTED; localhost is not ready")

    if local_status != "OK" or localhost_trustworthy is not True:
        raise SystemExit("local bundled data is not trusted as live; localhost is not ready")

    return payload


def run_import(env: dict[str, str]) -> dict[str, Any]:
    print()
    print("== python3 tools/import_public_market_data.py --json ==")
    proc = run_captured(
        ["python3", "tools/import_public_market_data.py", "--json"],
        cwd=ROOT,
        env=env,
    )

    if proc.stderr.strip():
        print(proc.stderr.strip(), file=sys.stderr)

    if proc.returncode != 0:
        if proc.stdout.strip():
            print(proc.stdout.strip())
        raise SystemExit(f"market import failed with exit {proc.returncode}")

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        print(proc.stdout)
        raise SystemExit(f"market import did not return valid JSON: {exc}") from exc

    pull = payload.get("cloud_pull") if isinstance(payload.get("cloud_pull"), dict) else {}
    files_written = payload.get("files_written") if isinstance(payload.get("files_written"), list) else []
    history_files = [path for path in files_written if str(path).startswith("site/public/data/history/")]

    print(f"cloud pull: {pull.get('success')} ({pull.get('method')})")
    print(f"valid snapshots: {payload.get('valid')}")
    print(f"rejected snapshots: {payload.get('rejected')}")
    print(f"skipped metadata: {payload.get('skipped')}")
    print(f"newest generated_at: {payload.get('newest_generated_at')}")
    print(f"available ranges: {', '.join(payload.get('available_ranges') or [])}")
    print(f"files written: {len(files_written)}")
    print(f"compact history files written: {len(history_files)}")

    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Refresh public market data, regenerate compact history, build the site, and verify localhost trust."
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start the Vite dev server after refresh/build/check passes.",
    )
    args = parser.parse_args()

    env = os.environ.copy()
    env.setdefault("MARKET_CLOUD_SOURCE", DEFAULT_VPS_SOURCE)

    print("Idle Hacking local market site update")
    print(f"repo: {ROOT}")
    print(f"market source: {env['MARKET_CLOUD_SOURCE']}")

    run_import(env)
    run_streamed(["npm", "run", "build"], cwd=ROOT / "site", env=env)
    run_checker(env)

    print()
    print("Local market site is refreshed and trusted.")
    print(f"Preview command: cd site && npm run dev -- --host 127.0.0.1")
    print(f"Preview URL: {DEV_URL}")

    if args.serve:
        print()
        print("== npm run dev -- --host 127.0.0.1 ==")
        subprocess.run(["npm", "run", "dev", "--", "--host", "127.0.0.1"], cwd=ROOT / "site", env=env)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
