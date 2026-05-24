#!/usr/bin/env python3
"""Local cloud helper for the Idle Hacking collector.

This listens only on 127.0.0.1 and accepts JSON from the Tampermonkey
collector running in the cloud browser. It stores health, market feed, and
chat export payloads on disk under a configurable data directory.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

HOST = "127.0.0.1"
PORT = 8765
MAX_BODY_BYTES = 500 * 1024 * 1024
ALLOWED_ORIGIN = "https://www.idlehacking.com"
DEFAULT_DATA_DIR = "/home/scraper/data"
DEFAULT_HEALTH_ARCHIVE_INTERVAL_SECONDS = 300
DEFAULT_HEALTH_ARCHIVE_MAX_FILES = 288

FORBIDDEN_EXACT_KEYS = {
    "chat",
    "chat_message",
    "discord",
    "discord_message",
    "username",
    "player",
    "current_player",
    "top_entries",
    "credits",
    "holdings",
    "holdingsqty",
    "holdingsvaluecents",
    "orders",
    "buyallbest",
    "sellallbest",
    "cookie",
    "token",
    "secret",
    "authorization",
    "session",
    "profile",
}

FORBIDDEN_SUBSTRINGS = (
    "cookie",
    "token",
    "secret",
    "authorization",
    "bearer",
    "session",
)


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_timestamp_compact(dt: datetime | None = None) -> str:
    stamp = (dt or utc_now()).astimezone(timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H%M%SZ")


def utc_date_path(dt: datetime | None = None) -> str:
    stamp = (dt or utc_now()).astimezone(timezone.utc)
    return stamp.strftime("%Y-%m-%d")


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def data_dir() -> Path:
    configured = os.environ.get("IH_HELPER_DATA_DIR", DEFAULT_DATA_DIR).strip()
    return Path(configured or DEFAULT_DATA_DIR).expanduser()


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return default

    try:
        return int(raw)
    except ValueError:
        return default


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def fsync_dir(path: Path) -> None:
    try:
        fd = os.open(str(path), os.O_DIRECTORY)
    except OSError:
        return

    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def atomic_write_json(path: Path, value: Any) -> None:
    ensure_parent(path)
    tmp_path = path.with_name(f".{path.name}.tmp-{os.getpid()}-{time.time_ns()}")
    payload = (json_dumps(value) + "\n").encode("utf-8")

    with open(tmp_path, "wb") as handle:
        handle.write(payload)
        handle.flush()
        os.fsync(handle.fileno())

    os.replace(tmp_path, path)
    fsync_dir(path.parent)


def append_jsonl(path: Path, value: Any) -> None:
    ensure_parent(path)
    payload = (json_dumps(value) + "\n").encode("utf-8")
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o644)
    try:
        with os.fdopen(fd, "ab", closefd=False) as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
    fsync_dir(path.parent)


def read_json_file(path: Path) -> Any | None:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except FileNotFoundError:
        return None


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def health_archive_interval_seconds() -> int:
    value = env_int("IH_HELPER_HEALTH_ARCHIVE_INTERVAL_SECONDS", DEFAULT_HEALTH_ARCHIVE_INTERVAL_SECONDS)
    return max(0, value)


def health_archive_max_files() -> int:
    value = env_int("IH_HELPER_HEALTH_ARCHIVE_MAX_FILES", DEFAULT_HEALTH_ARCHIVE_MAX_FILES)
    return max(0, value)


def health_archive_dir() -> Path:
    return data_dir() / "health" / "archive"


def newest_health_archive_mtime(directory: Path) -> float | None:
    newest = None
    try:
        entries = list(directory.glob("*.json"))
    except OSError:
        return None

    for path in entries:
        try:
            mtime = path.stat().st_mtime
        except FileNotFoundError:
            continue

        if newest is None or mtime > newest:
            newest = mtime

    return newest


def should_write_health_archive() -> bool:
    interval = health_archive_interval_seconds()
    if interval <= 0:
        return False

    newest = newest_health_archive_mtime(health_archive_dir())
    if newest is None:
        return True

    return (time.time() - newest) >= interval


def prune_health_archives(directory: Path, max_files: int) -> None:
    if max_files <= 0:
        return

    try:
        entries = [path for path in directory.glob("*.json") if path.is_file()]
    except OSError:
        return

    if len(entries) <= max_files:
        return

    entries.sort(key=lambda path: path.stat().st_mtime if path.exists() else 0.0, reverse=True)
    for path in entries[max_files:]:
        try:
            path.unlink()
        except FileNotFoundError:
            continue
        except OSError:
            continue


def write_receipt(directory: Path, archive_rel_path: str, payload: Any, created_at: str, message_count: int) -> None:
    ensure_parent(directory)
    content = (json_dumps(payload) + "\n").encode("utf-8")
    receipt = {
        "file": archive_rel_path,
        "sha256": sha256_bytes(content),
        "created_at": created_at,
        "message_count": message_count,
    }
    atomic_write_json(directory / f"{created_at}.json", receipt)


def is_json_content_type(content_type: str | None) -> bool:
    if not content_type:
        return False
    return "application/json" in content_type.lower()


def parse_json_body(raw: bytes) -> Any:
    return json.loads(raw.decode("utf-8"))


def iter_key_paths(value: Any, path: str = ""):
    if isinstance(value, dict):
        for key, item in value.items():
            key_text = str(key)
            next_path = f"{path}.{key_text}" if path else key_text
            yield next_path, key_text, item
            yield from iter_key_paths(item, next_path)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            next_path = f"{path}[{index}]"
            yield from iter_key_paths(item, next_path)


def safety_scan_json(value: Any) -> tuple[bool, str]:
    for path, key, item in iter_key_paths(value):
        lower_key = key.lower()

        if lower_key in FORBIDDEN_EXACT_KEYS:
            return False, f"forbidden_key:{path}"

        if lower_key == "rankings" and item is not None:
            return False, f"forbidden_rankings:{path}"

        if lower_key == "top_entries":
            return False, f"forbidden_top_entries:{path}"

        for needle in FORBIDDEN_SUBSTRINGS:
            if needle in lower_key:
                return False, f"forbidden_key_fragment:{path}"

    return True, ""


def validate_health_payload(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "expected_json_object"
    if payload.get("type") != "idlehacking_collector_health":
        return False, "invalid_type"
    if payload.get("schema_version") != 1:
        return False, "invalid_schema_version"
    return True, ""


def validate_market_payload(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "expected_json_object"
    if payload.get("type") != "idlehacking_public_market_feed":
        return False, "invalid_type"
    if payload.get("schema_version") != 1:
        return False, "invalid_schema_version"

    market = payload.get("market")
    if not isinstance(market, dict):
        return False, "market_missing"
    if market.get("type") != "market_public_snapshot":
        return False, "invalid_market_type"
    if not isinstance(market.get("commodities"), list):
        return False, "market_commodities_missing"
    if not isinstance(payload.get("health"), dict):
        return False, "health_missing"

    return True, ""


def validate_chat_payload(payload: Any) -> tuple[bool, str]:
    if not isinstance(payload, dict):
        return False, "expected_json_object"
    if payload.get("type") != "idlehacking_chat_export":
        return False, "invalid_type"
    if payload.get("schema_version") != 1:
        return False, "invalid_schema_version"
    if not isinstance(payload.get("messages"), list):
        return False, "messages_missing"
    return True, ""


class CollectorHandler(BaseHTTPRequestHandler):
    server_version = "IHCollectorHelper/1.0"

    def log_message(self, fmt: str, *args: Any) -> None:
        sys.stdout.write("%s - - [%s] %s\n" % (self.address_string(), self.log_date_time_string(), fmt % args))
        sys.stdout.flush()

    def _send_json(self, status: HTTPStatus, payload: Any) -> None:
        body = (json_dumps(payload) + "\n").encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._set_cors_headers()
        self.end_headers()
        self.wfile.write(body)

    def _set_cors_headers(self) -> None:
        origin = self.headers.get("Origin")
        if origin == ALLOWED_ORIGIN:
            self.send_header("Access-Control-Allow-Origin", ALLOWED_ORIGIN)
            self.send_header("Vary", "Origin")
            self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Access-Control-Max-Age", "600")

    def _read_body(self) -> tuple[bytes | None, str | None]:
        content_length_raw = self.headers.get("Content-Length")
        if not content_length_raw:
            return None, "content_length_required"

        try:
            content_length = int(content_length_raw)
        except ValueError:
            return None, "invalid_content_length"

        if content_length < 0:
            return None, "invalid_content_length"
        if content_length > MAX_BODY_BYTES:
            return None, "body_too_large"

        body = self.rfile.read(content_length)
        if len(body) > MAX_BODY_BYTES:
            return None, "body_too_large"
        return body, None

    def _handle_not_found(self) -> None:
        self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "not_found"})

    def do_OPTIONS(self) -> None:  # noqa: N802
        if self.headers.get("Origin") == ALLOWED_ORIGIN:
            self.send_response(HTTPStatus.NO_CONTENT)
            self._set_cors_headers()
            self.end_headers()
            return
        self.send_response(HTTPStatus.NO_CONTENT)
        self.end_headers()

    def do_GET(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        if parsed.path != "/health":
            self._handle_not_found()
            return

        health_path = data_dir() / "collector_health.json"
        payload = read_json_file(health_path)
        if payload is None:
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False, "error": "health_not_found"})
            print("GET /health -> 404 health_not_found", flush=True)
            return

        self._send_json(HTTPStatus.OK, payload)
        print("GET /health -> 200", flush=True)

    def do_POST(self) -> None:  # noqa: N802
        parsed = urlparse(self.path)
        body, body_error = self._read_body()
        if body_error:
            self._send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE if body_error == "body_too_large" else HTTPStatus.LENGTH_REQUIRED, {"ok": False, "error": body_error})
            print(f"POST {parsed.path} -> {body_error}", flush=True)
            return

        if not is_json_content_type(self.headers.get("Content-Type")):
            self._send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"ok": False, "error": "json_only"})
            print(f"POST {parsed.path} -> json_only", flush=True)
            return

        try:
            payload = parse_json_body(body or b"")
        except json.JSONDecodeError:
            self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": "invalid_json"})
            print(f"POST {parsed.path} -> invalid_json", flush=True)
            return

        if parsed.path == "/health":
            ok, reason = validate_health_payload(payload)
            if not ok:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": reason})
                print(f"POST /health -> {reason}", flush=True)
                return

            latest = data_dir() / "collector_health.json"

            atomic_write_json(latest, payload)

            archive_dir = health_archive_dir()
            if should_write_health_archive():
                created_at = utc_timestamp_compact()
                atomic_write_json(archive_dir / f"{created_at}.json", payload)
                prune_health_archives(archive_dir, health_archive_max_files())

            self._send_json(HTTPStatus.OK, {"ok": True})
            print("POST /health -> 200 saved", flush=True)
            return

        if parsed.path == "/market-feed":
            ok, reason = validate_market_payload(payload)
            if not ok:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": reason})
                print(f"POST /market-feed -> {reason}", flush=True)
                return

            safe, reason = safety_scan_json(payload)
            if not safe:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": reason})
                print(f"POST /market-feed -> {reason}", flush=True)
                return

            created_at = utc_timestamp_compact()
            market_dir = data_dir() / "market"
            snapshot_dir = market_dir / "snapshots" / "recent"
            latest = market_dir / "latest.json"
            receipt_dir = market_dir / "receipts"
            snapshot_rel = f"snapshots/recent/{created_at}.json"
            snapshot_path = snapshot_dir / f"{created_at}.json"

            atomic_write_json(snapshot_path, payload)
            atomic_write_json(latest, payload)
            write_receipt(receipt_dir, snapshot_rel, payload, created_at, 0)
            self._send_json(HTTPStatus.OK, {"ok": True})
            print("POST /market-feed -> 200 saved", flush=True)
            return

        if parsed.path == "/chat-export":
            ok, reason = validate_chat_payload(payload)
            if not ok:
                self._send_json(HTTPStatus.BAD_REQUEST, {"ok": False, "error": reason})
                print(f"POST /chat-export -> {reason}", flush=True)
                return

            created_at = utc_timestamp_compact()
            chat_dir = data_dir() / "private" / "chat"
            archive_dir = chat_dir / "archive"
            manifests_dir = chat_dir / "manifests"
            archive_rel = f"archive/{created_at}.json"
            latest = chat_dir / "latest.json"
            archive_path = archive_dir / f"{created_at}.json"

            atomic_write_json(archive_path, payload)
            atomic_write_json(latest, payload)

            messages = payload.get("messages")
            message_count = len(messages) if isinstance(messages, list) else 0
            archive_payload = (json_dumps(payload) + "\n").encode("utf-8")
            manifest_line = {
                "file": archive_rel,
                "sha256": sha256_bytes(archive_payload),
                "created_at": created_at,
                "message_count": message_count,
            }
            append_jsonl(manifests_dir / "chat_manifest.jsonl", manifest_line)

            self._send_json(HTTPStatus.OK, {"ok": True})
            print("POST /chat-export -> 200 saved", flush=True)
            return

        self._handle_not_found()


def main() -> int:
    root = data_dir()
    root.mkdir(parents=True, exist_ok=True)

    server = ThreadingHTTPServer((HOST, PORT), CollectorHandler)
    print(f"IH helper listening on http://{HOST}:{PORT}", flush=True)
    print(f"Data dir: {root}", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("Shutting down", flush=True)
    finally:
        server.server_close()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
