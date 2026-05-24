# README_INTERNAL — ih_market_companion

```yaml
repo: ih_market_companion
purpose: "Public market site, VPS/cloud collector, market publishing, and health checks for IdleHacker"
status: active
ecosystem: idlehacker
home: /Users/buddy/projects/ih_market_companion
git:
  branch: main
  policy: no direct git writes by workers
```

## IVY Summary

`ih_market_companion` owns the public market lane for IdleHacker: GitHub Pages site, public market data publishing, VPS/cloud collector code, pipeline health checks, and ecosystem docs. It must stay public-only. It does not own private chat/Discord KB artifacts or game-facing market strategy/trade records.

## Current Work

- **Public market freshness** — Keep live Pages, local bundled data, GitHub Actions, and VPS/source freshness aligned.
- **Market pipeline health** — Preserve public checker, operator checker, and repair-loop boundaries.
- **Public history/site work** — Maintain `site/public/data/` and compact public history for chart/detail views.
- **Ecosystem docs** — Keep `ECOSYSTEM.md` aligned with ivy-control project-context docs.
- **WGU-Reddit shadow-run lane** — Idle Hacking Companion now provides VPS host/runtime paths for a WGU-Reddit shadow run. WGU-Reddit owns runtime behavior; this repo documents host layout and boundaries.

## Open Loops

1. **Anchor durability** — Root `README_INTERNAL.md`, `AGENTS.md`, and `ECOSYSTEM.md` are untracked. They are useful locally but not durable until Buddy approves tracking/package decisions.
2. **VPS helper sync unknown** — Local canonical helper source is `_internal/vps_helper/collector_helper.py`; no documented sync mechanism to the running VPS helper exists.
3. **Chat export monitoring gap** — Market pipeline has health checks; VPS chat export freshness is not reliably monitored and belongs to the documented ecosystem gaps.
4. **Public/private boundary risk** — Site/public data must remain public market-only; private chat, player data, holdings, credentials, and KB artifacts do not belong here.

## Durable Decisions

1. Public-only boundary: no private chat, player data, credentials, holdings, orders, or KB artifacts in this repo.
2. Ingestion and publishing stay decoupled; viewer/publish failures must not interrupt data collection.
3. VPS publishes static artifacts only; the public site must not depend on a live VPS runtime.
4. `tools/ensure_market_pipeline_health.py` is operator-only unless Buddy explicitly approves running it.
5. `ECOSYSTEM.md` is the repo-local cross-repo map; ivy-control project-context is the control-plane cross-repo authority.
6. WGU-Reddit VPS exports/imports are validation snapshots, not automatic promotion or blind overwrite of the Mac live DB.

## Related Repos / Ecosystem Context

Ecosystem context: `ivy-control/docs/project-context/idlehacker-ecosystem.md`

This repo's role: Public market site, VPS/cloud collector, market publishing, GitHub Pages/Actions, health checks, and ecosystem docs.

Related repos:
- `/Users/buddy/projects/idle-hacker` — Game-facing userscripts, market strategy, trade recording, Discord intake workspace.
- `/Users/buddy/projects/idlehacking_kb` — KB/data/research repo; owns chat/Discord ingest, reports, review surfaces, and incident docs.
- `/Users/buddy/projects/ih_market_companion/ECOSYSTEM.md` — Repo-local ecosystem map and supporting ownership index.

## Important Files

| File | Why It Matters |
|------|---------------|
| `README.md` | Public entrypoint and navigation |
| `AGENTS.md` | Worker routing/safety card |
| `TODO.txt` | Active working list |
| `ECOSYSTEM.md` | Repo-local cross-repo map |
| `site/public/data/latest.json` | Public market latest feed |
| `site/public/data/index.json` | Public market data index |
| `site/public/data/history/` | Compact public history data |
| `tools/check_public_market_health.py` | Public-only freshness checker |
| `tools/check_market_pipeline_health.py` | Operator pipeline checker |
| `tools/ensure_market_pipeline_health.py` | Operator-only repair loop |
| `_internal/vps_helper/collector_helper.py` | Canonical local VPS helper source |
| `_internal/scripts/idle_hacking_collector.js` | VPS/headless collector script |

## VPS Host Lanes

Idle Hacking Companion provides the host/runtime substrate for multiple lanes. Runtime logic remains owned by the source repo for that lane.

| Lane | Owner | Paths | Status |
|---|---|---|---|
| Public market collector | `ih_market_companion` | `/home/scraper/data/market/`, `/home/scraper/vps_helper/` | Active |
| WGU-Reddit shadow-run | `/Users/buddy/Desktop/WGU-Reddit` | code `/home/scraper/apps/wgu-reddit`; DB `/home/scraper/data/wgu-reddit/WGU-Reddit.db`; exports `/home/scraper/data/wgu-reddit/exports/`; logs `/home/scraper/logs/wgu-reddit/`; env `/home/scraper/config/wgu-reddit.env` | Manual ingest and export/import validation passed; user-level systemd timer installed for shadow-run only |

WGU-Reddit status as of 2026-05-24:

- Code is installed at `/home/scraper/apps/wgu-reddit`.
- VPS DB is installed at `/home/scraper/data/wgu-reddit/WGU-Reddit.db`; checksum and SQLite integrity passed.
- Manual WGU ingest and export/import validation passed on 2026-05-24.
- User-level systemd scheduler is installed as `wgu-reddit-shadow-run.timer`, daily `03:00 America/New_York`, for shadow-run only.
- No production cutover has happened.
- No Mac live DB overwrite has happened.
- Secrets remain outside repos. The host-local env path is `/home/scraper/config/wgu-reddit.env`; the app reads it through `/home/scraper/apps/wgu-reddit/.env` via `python-dotenv`.
- Do not shell-source the WGU env file in scheduler commands.
- Retention guardrails: root FS warning `>75%`, urgent `>85%`; exports warning `>2GB` or `>30` snapshots, urgent `>5GB` or `>60` snapshots; DB growth warning `>25MB/day`, urgent `>100MB/day`. No export pruning or Mac DB merge until WGU approves the import/merge workflow.

## Safe Commands

```bash
git status --short
python3 tools/check_public_market_health.py       # Public URLs only
python3 tools/check_market_pipeline_health.py --json  # Operator health check; may be inconclusive without SSH
```

## Agent Cautions

1. Do NOT add private chat, player data, holdings, credentials, orders, or KB artifacts to this repo.
2. Do NOT run `tools/ensure_market_pipeline_health.py`, deployment, sync, SSH, VPS, or GitHub Actions trigger commands without explicit approval.
3. Do NOT edit public/site-facing output without Buddy approval.
4. Do NOT run collectors, scrapers, app code, package installs, model jobs, or long pipelines unless explicitly approved.
5. Do NOT read `.env`, credentials, private keys, raw private exports, raw transcripts, email bodies, DB rows, or large generated dumps.
6. Live Pages can be fresher than local checkout; verify freshness before assuming the public site is stale.
7. Do NOT stage, commit, push, checkout, reset, merge, rebase, clean, or use broad git staging.
8. Do NOT install a WGU scheduler, perform WGU production cutover, or overwrite WGU Mac live DB from this repo.

## Public / Private Boundary

This repo is public-facing. `site/` and `site/public/data/` are public market surfaces. `_internal/` and `tools/` are operational tooling. Private chat/Discord, player data, holdings, orders, credentials, and KB artifacts belong outside this repo.

## Runtime Notes

- Updated: 2026-05-23 by Codex for IdleHacker memory migration.
- Working directory: `/Users/buddy/projects/ih_market_companion`
- Anchor durability: `README_INTERNAL.md`, `AGENTS.md`, and `ECOSYSTEM.md` are untracked as of this migration.
- Verified against safe docs only; no secrets, VPS commands, deployment, package install, app code, or collector execution was used.

## Source References

- `README.md`
- `README_INTERNAL.md` prior version
- `AGENTS.md`
- `README_INTERNAL.template_pilot.md`
- `AGENTS.template_pilot.md`
- `TEMPLATE_PILOT_REPORT.md`
- `ECOSYSTEM.md`
- `ivy-control/docs/project-context/idlehacker-ecosystem.md`
- `ivy-control/docs/project-context/2026-05-23-memory-ecosystem-passalong.md`

## Session Log Index

- `logs/sessions/2026-05-15_ih_market_companion.md`

## IVY Memory Export

```yaml
<!-- IVY_MEM_START -->
memories:
  - id: ih-market-companion-role
    type: repo_context
    scope: repo
    privacy: internal
    source_ref: README.md
    approval_state: approved
    content: "ih_market_companion owns the public market site, VPS/cloud collector, market publishing, GitHub Pages/Actions, health checks, and ecosystem docs."
    review_date: 2026-05-23
  - id: ih-market-companion-public-boundary
    type: boundary
    scope: repo
    privacy: internal
    source_ref: README.md
    approval_state: approved
    content: "The repo is public-facing and must remain public market-only; private chat, player data, credentials, holdings, orders, and KB artifacts do not belong here."
    review_date: 2026-05-23
  - id: ih-market-companion-helper-source
    type: architecture
    scope: ecosystem
    privacy: internal
    source_ref: _internal/vps_helper/collector_helper.py
    approval_state: needs_review
    content: "The canonical local VPS helper source is _internal/vps_helper/collector_helper.py; no sync mechanism to the running VPS helper is documented."
    review_date: 2026-05-23
  - id: ih-market-companion-anchor-durability
    type: open_loop
    scope: repo
    privacy: internal
    source_ref: git status --short
    approval_state: needs_review
    content: "Root README_INTERNAL.md, AGENTS.md, and ECOSYSTEM.md are untracked and require a human durability decision."
    review_date: 2026-05-23
<!-- IVY_MEM_END -->
```

## VPS Operational Documentation

VPS runbooks and operational docs are in `_internal/vps_helper/docs/`:

| Doc | Path |
|-----|------|
| VPS RDP Setup | `_internal/vps_helper/docs/vps_rdp_setup.md` |
| VPS Data Flow Analysis | `_internal/vps_helper/docs/vps_data_flow_analysis.md` |

**Incident docs:** VPS chat incident (`2026-05-22_vps_chat_body_too_large_incident.md`) is in `idlehacking_kb/docs/infrastructure/` as it affects KB ingest. Cross-referenced from both repos.

## Open Loops

1. **Daily runner investigation** — `idlehacking_kb/scripts/daily_runner.py` is stale since May 6, 2026. Manual verification required before launchd scheduling.
2. **README_INTERNAL/AGENTS tracking durability** — This file is currently untracked. Separate follow-up needed.
3. **Tampermonkey dedupe** — Browser audit required before deduplicating scripts across repos.
4. **Discord ingest boundary** — KB repo is canonical; idle-hacker is workspace-only pending confirmation.
