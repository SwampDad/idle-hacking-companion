# Idle Hacking Market Companion

Public GitHub Pages companion site for Idle Hacking market snapshots.

This repository contains only the public-facing site, sample public market feed data, and the GitHub Pages deployment workflow.

Current status:

- Public market data only. Do not add private chat, player data, credentials, orders, holdings, or KB artifacts.
- The live site surfaces feed freshness.
- Localhost can show stale bundled data if the checkout is behind live data; the UI warns when local bundled data is stale.
- Compact public history files are generated under `site/public/data/history/` for future chart/detail views.
- Commodity rows can open an MVP detail drawer backed by compact per-commodity history.
- 2026-05-11 trust checkpoint: after SSH key setup, the operator checker reached `TRUSTED`; VPS, GitHub Actions, live Pages, and local bundled data were aligned.
- Prototype planning lives in `site/src/prototype/MARKET_HISTORY_AND_GRAPHS_PLAN.md`.

## Contents

- `site/` - Vite/React static site
- `site/public/data/latest.json` - sample public market feed
- `site/public/data/index.json` - public snapshot index and advertised ranges
- `site/public/data/history/index.json` - compact public history index
- `site/public/data/history/commodities/*.json` - compact per-commodity public history
- `tools/import_public_market_data.py` - imports validated public market snapshots into site data
- `tools/check_public_market_health.py` - checks live GitHub Pages public JSON only
- `tools/check_market_pipeline_health.py` - operator check for live Pages, local bundled data, GitHub Actions, and VPS when SSH is available
- `.github/workflows/pages.yml` - GitHub Pages build and deploy workflow

## Run Locally

Refresh local public data before trusting localhost:

```bash
python3 tools/update_local_market_site.py
```

This command pulls current public market data from the VPS, regenerates compact history, builds the site, and uses `tools/check_market_pipeline_health.py` as the final trust gate.

Then start the dev server:

```bash
cd site
npm install
npm run dev -- --host 127.0.0.1
```

Local preview URL:

```text
http://127.0.0.1:5173/
```

## Build

```bash
cd site
npm run build
```

## Public Data Health

```bash
python3 tools/check_public_market_health.py
```

The public health checker uses only public GitHub Pages URLs. It does not require SSH, secrets, or GitHub CLI.

## Operator Pipeline Health

```bash
python3 tools/check_market_pipeline_health.py
```

The operator checker compares live Pages JSON, local bundled data, recent GitHub Actions runs, and VPS/source freshness when SSH is available. It expects a local SSH config alias named `ih-market-vps`; password/key setup happens outside this repo. If VPS SSH is unavailable, it reports `INCONCLUSIVE` and prints the manual command to run.

Machine-readable output for dashboard/watchdog work:

```bash
python3 tools/check_market_pipeline_health.py --json
```

Override the SSH target when needed:

```bash
IH_MARKET_VPS_SSH_HOST=scraper@46.224.146.164 python3 tools/check_market_pipeline_health.py
```

Do not trust localhost as live unless `python3 tools/update_local_market_site.py` passes, or you are intentionally testing old bundled data.
No passwords, private keys, tokens, or other secrets belong in this repo.

The future Operator Dashboard will be a visual version of this checker, with additional VPS runtime checks and optional Nevamoen public comparison as diagnostics. Nevamoen differences are external mismatches, not proof that either source is wrong by themselves.

GitHub Actions schedules are best-effort. Manual `workflow_dispatch` and future watchdog/dashboard checks are part of the trust plan; do not rely only on cron timing.

## Import Local Public Data

Normal local refresh should use the canonical command:

```bash
python3 tools/update_local_market_site.py
```

Use `--no-pull` only for deliberate offline/regression testing against already available public snapshots:

```bash
python3 tools/import_public_market_data.py --no-pull
```

The workflow builds from `site/` and deploys `site/dist`.

Older prototype reports under `site/src/prototype/` are historical investigation artifacts. Prefer `MARKET_HISTORY_AND_GRAPHS_PLAN.md` for current graph/history direction.
