# ih_market_companion — AGENTS

> AGENTS.md is a router, not durable memory. Keep facts in `README_INTERNAL.md`.

## Role

Public market site, VPS/cloud collector, market publishing, and health checks for IdleHacker. Workers may do bounded docs, status checks, and validation only. Public/site-facing changes need Buddy approval.

## Read First

1. `README_INTERNAL.md`
2. `README.md`
3. `ivy-control/docs/project-context/idlehacker-ecosystem.md`
4. `ECOSYSTEM.md`

## Allowed Work

- Read-only inspection and git status checks
- Compact documentation updates within explicit scope
- Safe checks listed in `README_INTERNAL.md`
- Source-backed reports and migration notes

## Forbidden Work

- Add private chat, player data, holdings, credentials, orders, or KB artifacts
- Read `.env`, credentials, private keys, raw private exports, raw transcripts, email bodies, DB rows, or large generated dumps
- Run collectors, scrapers, deployment, sync, SSH, VPS, GitHub Actions trigger, package install, app code, model jobs, or long pipelines unless explicitly approved
- Run `tools/ensure_market_pipeline_health.py` without explicit approval
- Edit public/site-facing output without Buddy approval
- Stage, commit, push, checkout, reset, merge, rebase, clean, or use broad git staging

## Safety Boundaries

- Git Steward owns commits; workers use read-only git only.
- This repo is public-facing; keep public market data separate from private chat/KB material.
- Root anchors are untracked until Buddy approves a durability package.

## Related Context

1. `ivy-control/docs/project-context/idlehacker-ecosystem.md`
2. `ECOSYSTEM.md`

## Logging / Closeout

After meaningful work, append the worker log in `ivy-control/runtime/logs/workers/YYYY-MM-DD/ih_market_companion.md`, update `README_INTERNAL.md` only if repo state changed, and report changed files plus next action.

## Stop Conditions

Stop if work needs forbidden sources, public/site edits, VPS/sync/deploy commands, package installs, app code, model jobs, git writes, or an unclear approval boundary.
