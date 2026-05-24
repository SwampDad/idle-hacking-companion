> **Cross-Reference:** VPS chat incident documentation is in `idlehacking_kb/docs/infrastructure/2026-05-22_vps_chat_body_too_large_incident.md`.

# VPS Data Flow Analysis — Chat and Market

## Overview

The Hetzner VPS (`ubuntu-4gb-nbg1-1`, IP `46.224.146.164`) runs a persistent browser-based Idle Hacking collector via Tampermonkey inside Google Chrome (XFCE desktop, XRDP). The collector captures two independent data streams: **private chat** (for KB ingestion) and **public market** (for the market companion site). These flows diverge at the collector helper and follow separate downstream pipelines.

---

## 1. Collector Layer (on VPS)

### Browser Userscript (Tampermonkey)

The userscript (`hackbot.user.js`) runs in the browser tab pointed at `https://www.idlehacking.com`. It collects:

| Stream | What | Method |
|--------|------|--------|
| Chat capture | Private in-game chat messages (main, help, trade channels) | DOM + WebSocket capture |
| Market feed | Public stackables/commodities market state (16 commodities, 16 books) | WebSocket + DOM |
| Volume changes | Market volume (filled, canceled, added qty) | WebSocket `MARKET_STACKABLES_DELTA` |
| Health heartbeat | Collector health state | Periodic POST |

The userscript POSTs JSON payloads to the local helper service at `http://127.0.0.1:8765`.

### Collector Helper (`collector_helper.py`)

**Path:** `/home/scraper/vps_helper/collector_helper.py`  
**Service:** `ih-collector-helper.service` (systemd --user)  
**Endpoint:** `http://127.0.0.1:8765`

Routes:

| Route | Source | Writes to |
|-------|--------|-----------|
| `POST /chat-export` | Browser userscript | `/home/scraper/data/private/chat/` |
| `POST /market-feed` | Browser userscript | `/home/scraper/data/market/` |
| `POST /health` | Browser userscript | (health check) |
| `GET /health` | External polling | Returns health status |

CORS origin: `https://www.idlehacking.com`

The helper separates the two lanes by writing to different directory trees. It survives SSH disconnects via systemd, restarts on failure, and advances archives on each write.

---

## 2. Private Chat Data Flow (VPS → KB Repo)

### VPS Directory Layout

```
/home/scraper/data/private/chat/
    latest.json              ← most recent full chat export, overwritten each cycle
    archive/
        *.json               ← time-stamped archive files, appended every ~15 min
    manifests/
        chat_manifest.jsonl   ← append-only manifest tracking each archive write
```

### Flow Steps

```
Tampermonkey userscript
    │ POST /chat-export (JSON payload)
    ▼
collector_helper.py
    │ writes latest.json (overwrite)
    │ writes archive/{timestamp}.json (append-only)
    │ writes chat_manifest.jsonl entry
    ▼
VPS disk: /home/scraper/data/private/chat/
    │
    │ rsync (SSH) — pull from VPS to local KB repo
    │   source: scraper@46.224.146.164:/home/scraper/data/private/chat/archive/
    │   dest:   data/imports/chat/vps/
    │   key:    ~/.ssh/id_ed25519_swampdad
    │   flag:   --ignore-existing (idempotent)
    ▼
Local KB repo: data/imports/chat/vps/
    │
    │ ingest_collector_chat.py (or daily_runner.py)
    │   - reads VPS archive files from data/imports/chat/vps/
    │   - deduplicates via message_id / canonical_fingerprint
    │   - writes canonical archive: data/chat/archive/channels/{main,help,trade}.jsonl
    │   - updates index: data/chat/archive/index/{main,help,trade}.json
    │   - writes observations: data/chat/archive/observations/{main,help,trade}.jsonl
    │   - records ingest runs: data/chat/ledger/ingest_runs/*.json
    ▼
Canonical chat archives (local KB repo)

    │ downstream consumers:
    │   → deterministic normalization (scripts/normalize_initial_corpus.py)
    │   → flagged/unflagged filter exports
    │   → Stage 1 term usage manifest scan
    │   → daily runner reports (docs/reports/daily_runner/)
    │   → chat UI v0 build (data/registry/reviews/chat_ui_v0/)
    │   → candidate evidence packets (corruption_build, etc.)
```

### Identity Resolution (Chat Layer)

The collector ingest uses a priority chain for deduplication:
1. `message_id` exact match
2. `canonical_fingerprint` match
3. Fallback composite identity

Archive rows carry schema_version, merge_basis, and evidence_first_source to trace lineage back to the raw VPS files.

### Reliability

- VPS private chat export confirmed reliable as "normal KB source" (audited 2026-05-04)
- Continuity gaps: 0
- Browser-downloaded chat serves as fallback/supplement only
- Channel coverage audit: help 100%, main 100%, trade 100% (measured against browser-downloaded IDs)

### Orchestration

The daily runner (`scripts/daily_runner.py`) orchestrates:
1. rsync pull from VPS → `data/imports/chat/vps/`
2. Collector chat ingest (`scripts/chat/ingest_collector_chat.py`)
3. VPS chat audit (`scripts/chat/audit_vps_chat_export.py`)
4. Optionally: Discord CSV ingest, site snapshot, browser-chat fallback
5. Report generation

---

## 3. Public Market Data Flow (VPS → Market Companion → GitHub Pages)

### VPS Directory Layout

```
/home/scraper/data/market/
    latest.json                    ← most recent full market feed, overwritten each cycle
    snapshots/recent/
        *.json                     ← full historical snapshots, archived every ~15 min
    receipts/
        *.json                     ← metadata receipts (sha256 hash, snapshot filename ref)
```

### Flow Steps

```
Tampermonkey userscript
    │ POST /market-feed (JSON payload)
    ▼
collector_helper.py
    │ writes latest.json (overwrite)
    │ writes snapshots/recent/{timestamp}.json (full snapshot, append-only history)
    │ writes receipts/{timestamp}.json (metadata with sha256 + snapshot filename)
    ▼
VPS disk: /home/scraper/data/market/
    │
    ├─── GitHub Actions pipeline (scheduled)
    │   │ cron: 7,37 * * * *
    │   │ (avoids top-of-hour/half-hour GitHub Actions congestion)
    │   │
    │   │ Action: rsync pull
    │   │   source: scraper@46.224.146.164:/home/scraper/data/market/
    │   │   dest:   (within GH Actions runner)
    │   │
    │   │ Action: process and publish
    │   │   - skips metadata-only receipts
    │   │   - validates market feed payloads
    │   │   - builds site data under site/public/data/
    │   │   - deploys to GitHub Pages
    │   │
    │   ▼
    │ GitHub Pages (public site)
    │   URL: https://{org}.github.io/ih_market_companion/
    │   Contains: market snapshots, latest state
    │
    └─── Local Mac development workflow (manual)
        │
        │ command: _internal/scripts/update_market_data_local.sh
        │
        │   rsync pull from VPS → _internal/data/market/cloud/
        │   validate → import → write site/public/data/
        │   build site
        │
        ▼
        Local site at /Users/buddy/projects/ih_market_companion/
```

### Security Boundary

- **GitHub Actions pulls ONLY public market data** from `/home/scraper/data/market/`
- Private chat data from `/home/scraper/data/private/chat/` is **never** included in the public pipeline
- The public site (`ih_market_companion`) must never reference or serve private chat content
- The previous SSH private key exposure is documented; a replacement key was generated for GitHub Actions

### Market Data Contents

| Metric | Value |
|--------|-------|
| Commodities | 16 |
| Books | 16 |
| Pricing status | ok |
| Raw source state | live |
| Snapshot cadence | ~15 minutes |
| Website update cadence | Every ~30 min (7,37 past the hour) |

### Volume Data

Volume is captured via WebSocket `MARKET_STACKABLES_DELTA`:
- `filled_qty` — likely volume fill
- `canceled_qty` — volume removed
- `added_qty` — volume added
- `price_cents` — price at time of impact

---

## 4. End-to-End Pipeline Diagrams

### Chat Pipeline (VPS → KB)

```
┌─────────────┐    POST/chat-export    ┌──────────────────────┐
│  Browser     │ ─────────────────────→ │  collector_helper.py │
│  Userscript  │                       │  (127.0.0.1:8765)    │
│  (Chrome)    │                       └──────────┬───────────┘
└─────────────┘                                  │
                                                  ▼
                                    ┌─────────────────────────────┐
                                    │  /home/scraper/data/private │
                                    │  /chat/archive/*.json       │
                                    │  /chat/manifests/*.jsonl    │
                                    └─────────────┬───────────────┘
                                                  │ rsync (SSH pull)
                                                  ▼
                                    ┌─────────────────────────────┐
                                    │  data/imports/chat/vps/     │
                                    │  (local KB repo)            │
                                    └─────────────┬───────────────┘
                                                  │ ingest_collector_chat.py
                                                  ▼
                                    ┌─────────────────────────────┐
                                    │  data/chat/archive/channels │
                                    │  /main.jsonl                │
                                    │  /help.jsonl                │
                                    │  /trade.jsonl               │
                                    └─────────────┬───────────────┘
                                                  │ downstream:
                                                  │ normalization, filtering,
                                                  │ daily reports, KB packets
                                                  ▼
                                    ┌─────────────────────────────┐
                                    │  flagged/unflagged exports  │
                                    │  review artifacts           │
                                    │  chat UI v0                 │
                                    │  candidate KB evidence      │
                                    └─────────────────────────────┘
```

### Market Pipeline (VPS → Public Site)

```
┌─────────────┐    POST/market-feed    ┌──────────────────────┐
│  Browser     │ ────────────────────→ │  collector_helper.py │
│  Userscript  │                      │  (127.0.0.1:8765)    │
│  (Chrome)    │                      └──────────┬───────────┘
└─────────────┘                                 │
                                                 ▼
                                   ┌─────────────────────────────┐
                                   │  /home/scraper/data/market/ │
                                   │  latest.json                │
                                   │  snapshots/recent/*.json    │
                                   │  receipts/*.json            │
                                   └─────────────┬──────┬────────┘
                                                 │      │
                     ┌───────────────────────────┘      └───────────────────┐
                     ▼                                                      ▼
        ┌──────────────────────┐                            ┌──────────────────────┐
        │ GitHub Actions       │                            │ Local dev workflow   │
        │ (cron 7,37 * * * *)  │                            │ (manual)             │
        │                      │                            │                      │
        │ rsync pull →         │                            │ rsync pull →         │
        │ validate →           │                            │ validate →           │
        │ build site data →    │                            │ build site data →    │
        │ deploy GH Pages      │                            │ local site preview   │
        └──────────┬───────────┘                            └──────────────────────┘
                   ▼
        ┌──────────────────────┐
        │ GitHub Pages         │
        │ (public site)        │
        │ market.ih.example    │
        └──────────────────────┘
```

---

## 5. Key Integrity Points

| Aspect | Chat Lane | Market Lane |
|--------|-----------|-------------|
| **Idempotency** | `--ignore-existing` rsync; message_id dedup in ingest | Receipt sha256 prevents duplicate processing |
| **Provenance** | `source_path`, `source_file_sha256`, `run_id` on each canonical row | Receipts map sha256 → snapshot file |
| **Append-only** | Archive files never modified after write | Snapshots never modified after write |
| **Separation** | Private lane: SSH + local KB only | Public lane: SSH key restricted to market dir |
| **Auditability** | `audit_vps_chat_export.py` compares VPS vs browser IDs | `pipeline_health.py` checks freshness end-to-end |

---

## 6. Health and Monitoring

### Chat Pipeline Health

- VPS helper: `GET http://127.0.0.1:8765/health` → `chat.status: ok`
- Last message at: tracked per channel
- Archive advancing: confirmed every ~15 min
- Continuity gaps: 0

### Market Pipeline Health

- Helper: `market.status: ok`, `market.pricing_status: ok`
- Commodities: 16/16, Books: 16/16
- Live GH Pages timestamp vs VPS timestamp: compared by `pipeline_health.py`
- VPS helper health: ok
- Volume status: ok

### Known Risks

| Risk | Impact | Lane |
|------|--------|------|
| Chrome may hang | Collector stops; no chat or market data exported | Both |
| Tampermonkey collector stops on page crash | Same as above | Both |
| GH Actions workflow delay | Site goes stale | Market |
| KB daily runner too slow for light freshness checks | Heavy runs discourage frequent sync | Chat |
| No alerting/watchdog yet | Stale data may go unnoticed | Both |