# IdleHacker Ecosystem

## Purpose

This file is the cross-repo map and index for the IdleHacker project. It is the polished companion to [discovery_report.md](/Users/buddy/projects/ih_market_companion/discovery_report.md), which remains the raw factual inventory for now.

## Repository Map

| Repo | Role | Canonical domains | Important paths | Status / confidence |
|---|---|---|---|---|
| `idle-hacker` | Game-facing tools, userscripts, site snapshot diff, and current market strategy/trading work | Game-facing userscripts; equipment market viewer; site snapshot diff; market strategy/trading; trade recording | `scripts/IH_scripts/`; `scripts/site_snapshots/`; `market_strategy/`; `research/` | Appears canonical / high |
| `idlehacking_kb` | KB, data, research, and deterministic ingest/normalization pipeline | Discord ingest; VPS chat ingest; KB registry/normalization; KB topic packets; KB guide source; LLM benchmarks; experiments | `scripts/discord/`; `scripts/chat/`; `docs/kb/`; `docs/working/`; `data/registry/`; `bench_llm/`; `experiments/` | Appears canonical / high |
| `ih_market_companion` | Public site, VPS/cloud collector, market publishing, GitHub Pages/Actions, health checks, ecosystem docs | Public market site; VPS collector; market publishing; health checks; VPS/docs/runbooks; ecosystem docs | `site/`; `tools/`; `_internal/`; `.github/workflows/`; `discovery_report.md`; `ECOSYSTEM.md` | Appears canonical / high |

## Current Canonical Map

The labels below are intentionally cautious and reflect the discovery report rather than a hard migration plan.

| Domain | Appears canonical path / repo | Status / confidence |
|---|---|---|
| Game-facing userscripts | `idle-hacker/scripts/IH_scripts/` | Appears canonical / high |
| Equipment market viewer | `idle-hacker/scripts/IH_scripts/equipment_market_viewer/` | Appears active and canonical / high |
| Site snapshot diff | `idle-hacker/scripts/site_snapshots/` | Appears canonical / high |
| Market strategy / trading | `idle-hacker/market_strategy/` | Appears canonical and active / high |
| Trade recording | `idle-hacker/market_strategy/scripts/record_market_events.user.js` | Appears canonical and critical / high |
| Discord ingest | `idlehacking_kb/scripts/discord/` | Appears canonical / high |
| VPS chat ingest | `idlehacking_kb/scripts/chat/ingest_collector_chat.py` | Appears canonical / high |
| KB registry / normalization | `idlehacking_kb/scripts/` and `data/registry/` | Appears canonical / high |
| KB topic packets | `idlehacking_kb/docs/kb/topics/` | Appears active / high |
| KB guide source | `idlehacking_kb/docs/working/` | Appears canonical / high |
| Public market site | `ih_market_companion/site/` | Appears canonical / high |
| VPS collector | `ih_market_companion/_internal/scripts/idle_hacking_collector.js` | Appears canonical / high |
| Market publishing | `ih_market_companion/.github/workflows/update-market-data.yml` | Appears canonical / high |
| Health checks | `ih_market_companion/tools/` | Appears active / high |
| LLM benchmarks | `idlehacking_kb/bench_llm/` | Appears active / high |
| Experiments | `idlehacking_kb/experiments/` | Appears stale / medium |
| VPS docs / runbooks | `idlehacking_kb/docs/infrastructure/` and `idlehacking_kb/docs/workflows/` | Appears out of place / high |

## Refresh / Ingest Workflows

| Workflow | Repo | Scripts | Manual step | Outputs | Trust level | Silent failure risk |
|---|---|---|---|---|---|---|
| Website HTML download -> site snapshot diff | `idle-hacker` | `scripts/site_snapshots/site_snapshot_workflow.py` | Download `Idle Hacking*.html` from the browser | `research/game_site/snapshots/<YYYY-MM-DD>/change_note.md` | Medium | User must remember to download the HTML file |
| Discord export -> KB ingest | `idlehacking_kb` | `scripts/discord/ingest_discord.py`, `scripts/discord/build_prepared_artifacts.py`, `scripts/daily_runner.py` | Export CSV from Discord and place it in Downloads | `data/discord/<server_name>/archive/channels/<channel_id>.csv` | Medium | No alert if the export is missing or format changes |
| VPS chat collection -> KB ingest | `idlehacking_kb` | `scripts/chat/ingest_collector_chat.py`, `scripts/chat/ingest_chat.py`, `scripts/chat/audit_vps_chat_export.py`, `scripts/daily_runner.py` | None if SSH and rsync are healthy | `data/chat/collector/archive/channels/{main,help,trade}.jsonl` plus index, observations, ledger, provenance | Medium | Chrome crash, SSH key issues, VPS disk full, rsync failures |
| VPS market collection -> GitHub Actions -> GitHub Pages | `ih_market_companion` | `_internal/scripts/idle_hacking_collector.js`, `_internal/vps_helper/collector_helper.py`, `tools/import_public_market_data.py`, `.github/workflows/update-market-data.yml`, `.github/workflows/pages.yml` | None for the automated lane | `site/public/data/latest.json`, `index.json`, `snapshots/recent/*.json`, `history/` | Medium | Chrome OOM/crash, Tampermonkey disabled, cron skipped, no alerting |
| Local market import/update | `ih_market_companion` | `tools/update_local_market_site.py`, `tools/import_public_market_data.py`, `_internal/scripts/update_market_data_local.sh` | Run the update command locally | Refreshed `site/public/data/` for the dev server | Medium | Local copy can succeed while source data is stale |
| Trade event recording/export/import | `idle-hacker` | `market_strategy/scripts/record_market_events.user.js`, `market_strategy/scripts/ingest_market_recorder_exports.py` | Export JSONL from the browser or IndexedDB | `trading_events.jsonl`, recent CSVs, `manager_packet.*`, summaries | Medium | High: if the recorder is disabled, trades are silently missed |
| Daily KB runner | `idlehacking_kb` | `scripts/daily_runner.py` | User must already have the right exports in Downloads when fallback steps are needed | Run reports under `docs/reports/daily_runner/<timestamp>/` | Medium | Any sub-step can fail without a separate alerting loop |

## Userscript Inventory Summary

- `idle-hacker/scripts/IH_scripts/` appears to be the primary userscript home.
- `idle-hacker/market_strategy/scripts/record_market_events.user.js` is critical because missing it creates a trade-data gap.
- `idlehacking_kb/scripts/tampermonkey/` contains duplicates and a few possible unique scripts, so browser-side audit is still required to confirm what is actually enabled.
- `ih_market_companion/_internal/scripts/idle_hacking_collector.js` is the VPS/headless collector and is distinct from browser userscripts.

## VPS / Cloud / GitHub Operations

- The companion repo owns most operational code for the public market lane.
- `idlehacking_kb` currently contains VPS docs and runbooks that appear out of place relative to the rest of the repo split.
- Health-check scripts exist, but most checks are still manual and there is no alerting or watchdog loop.

Key paths:

- `/Users/buddy/projects/ih_market_companion/_internal/vps_helper/collector_helper.py`
- `/Users/buddy/projects/ih_market_companion/_internal/scripts/idle_hacking_collector.js`
- `/Users/buddy/projects/ih_market_companion/tools/check_public_market_health.py`
- `/Users/buddy/projects/ih_market_companion/tools/check_market_pipeline_health.py`
- `/Users/buddy/projects/ih_market_companion/tools/ensure_market_pipeline_health.py`
- `/Users/buddy/projects/ih_market_companion/.github/workflows/update-market-data.yml`
- `/Users/buddy/projects/ih_market_companion/.github/workflows/pages.yml`
- `/Users/buddy/projects/idlehacking_kb/docs/infrastructure/vps_rdp_setup.md`
- `/Users/buddy/projects/idlehacking_kb/docs/workflows/vps_data_flow_analysis.md`

## Silent Failure Register Summary

- Trade recorder disabled.
- VPS Chrome OOM or crash.
- Tampermonkey disabled on the VPS.
- GitHub Actions stale or skipped.
- No alerting or watchdog.
- VPS disk full.
- Daily runner not run.
- SSH key issues.
- Discord export stale.

## Current To-Do Link

Use [TODO.txt](/Users/buddy/projects/ih_market_companion/TODO.txt) as the active working task list. Do not treat this file as a substitute for the live task queue.

## Source / Evidence

This file was derived from:

- [discovery_report.md](/Users/buddy/projects/ih_market_companion/discovery_report.md)
- repo READMEs
- timestamps
- version headers
- git history
- file structure

## Notes

- The companion repo is currently named `ih_market_companion`, but the ecosystem scope is broader than a market companion.
- `discovery_report.md` is kept as raw discovery evidence for now. If it is renamed later, this file should continue to point to the polished ecosystem index.
