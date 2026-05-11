# Market History and Graphs Plan

Durable planning notes for Idle Hacking Market Companion history, charting, and public data trust work.

This document supersedes scattered chat notes where they conflict with the decisions below. Older prototype reports remain useful evidence, but some observations were made against stale local data or before the manual pipeline run on 2026-05-11.

## Current State

Done:

- The live GitHub Pages public data already supports 7d history from our own collector.
- After manual workflow run `25661855677`, live public data was fresh:
  - latest timestamp: `2026-05-11T09:13:30.049Z`
  - snapshots: `791`
  - ranges: `1d`, `7d`, `all`
- The local checkout can be stale and should not be treated as representative without fetching or pulling origin.
- Do not trust localhost as live unless the local timestamp is fresh or intentionally testing old bundled data.
- The market data pipeline is capable: rsync, import, commit, and Pages deploy succeeded in the manual run.
- The remaining trust issue is monitoring and schedule visibility, not the importer or Pages deploy path.
- A freshness/status line was added so users can see whether the displayed market data is current.
- The table range selector is wired into the table sparkline data path.
- Compact public history generation was added to `tools/import_public_market_data.py`.
- Local compact history files were generated under `site/public/data/history/` from the local public snapshot set.
- A canonical local refresh command was added at `tools/update_local_market_site.py`.
- A frontend compact-history helper was added at `site/src/prototype/historyData.js`.
- A commodity detail drawer MVP was added. Clicking a row, commodity name, or sparkline opens a larger history surface.
- A SVG `HistoryChart` MVP was added at `site/src/prototype/HistoryChart.jsx`; price mode renders bid/ask lines with a shaded spread band.
- A public-safe maintainer health checker was added at `tools/check_public_market_health.py`.
- An operator pipeline checker was added at `tools/check_market_pipeline_health.py`.
- The operator checker supports machine-readable dashboard/watchdog output with `python3 tools/check_market_pipeline_health.py --json`.
- 2026-05-11 trust checkpoint: after SSH key setup, `tools/check_market_pipeline_health.py` reached `TRUSTED`; VPS, GitHub Actions, live Pages, and local bundled data were aligned.
- The site warns on localhost when bundled local data is stale: `Local bundled data · stale`.

Not done:

- The current frontend still has a scaling issue because it loads raw snapshot files for history on initial page load.
- The commodity detail drawer is still MVP-level; it intentionally shows only the price chart for now.
- Mobile chart tap/drag behavior is basic and still needs polish.
- Helper-script history support is not implemented yet.
- Alerts/watchdog monitoring is not implemented yet.
- Browser extension packaging is not implemented yet.

Current decisions:

- Do not artificially limit the table to 1d only. The table should support `1d`, `7d`, and month/all ranges when available.
- Update: the table selector should show only exact, understandable windows for now: `1d` and `7d`.
- Do not label the full range as `All`; use a concrete label such as `Since May 3` so the visible window is clear.
- `28d` is the preferred next longer window once enough data exists; prefer `28d` over `1mo` because it is exact.
- Table sparklines should remain visually simple, probably a single mid-price series for now.
- Expanded commodity detail graphs should use richer supported data.

## Data Boundaries

- This repo and site must contain public-safe market data only.
- Do not include private chat, Discord data, player data, cookies, tokens, credentials, holdings, personal orders, or KB artifacts.
- Do not expose SSH private key material.
- Do not restore the Recent Volume Changes section.
- Volume fields are allowed only when sourced from our own public snapshots.
- Nevamoen data, if used later, is optional public bid/ask backfill only.
- Do not write Nevamoen data into `site/public/data/snapshots/recent/*.json`.
- Anything committed to this public repo or deployed to GitHub Pages must be assumed fetchable, copyable, and scrapable by anyone.

## Pipeline Trust and Monitoring

The site should make stale data visible to public users and should give maintainers enough diagnostics to identify which layer failed. GitHub Pages itself should not be treated as a reliable private alerting channel; it can display public status, but maintainer alerts need a separate script, workflow, issue, email, or notification path.

Monitor these layers:

| Layer | What to check | Failure signal |
| --- | --- | --- |
| VPS collector/source | `/home/scraper/data/market/latest.json`, snapshot count/newest snapshot, helper health when SSH is available | Collector browser, userscript, helper, or VPS disk stopped advancing. |
| GitHub scheduled workflow | Recent `update-market-data.yml` runs and schedule cadence | Scheduled runs delayed, skipped, disabled, or not started. |
| GitHub Actions execution | Run conclusion and logs | rsync, import, validation, commit, or deploy step failed. |
| Pages deploy | `pages.yml` run and deployed artifact freshness | Data was committed but not deployed. |
| Pages JSON serving | Live `latest.json` and `index.json` parse and timestamps advance | Pages is serving stale or invalid JSON. |
| Frontend/browser display | UI timestamp, range list, snapshot count, cache behavior | Browser shows older data than live JSON or hides available ranges. |

Suggested stale thresholds:

| Age | Public UI | Maintainer action |
| --- | --- | --- |
| `<= 90m` | Normal freshness line | No action. |
| `> 90m` | Compact warning: `Data delayed` | Investigate if repeated. |
| `> 3h` | Stronger warning | Trigger manual workflow and inspect logs. |
| `> 6h` | Critical stale/down state | Check VPS collector/helper, workflow permissions, Pages deploy, and live JSON. |

Different stale modes:

- VPS collector/source stale: GitHub Actions may run successfully but pull the same old `latest.json` and no newer snapshots.
- GitHub scheduled workflow delayed: VPS data may be fresh, but scheduled runs are missing, delayed, disabled, or skipped.
- GitHub Actions failure: a run exists but fails during rsync, import, validation, commit, build, or deploy.
- Pages deploy failure: update workflow produced data or a commit, but the Pages deployment did not publish it.
- Pages serving stale JSON: deploy appears successful, but `latest.json` or `index.json` from the live URL still has old timestamps.
- Frontend/browser cache/display issue: live JSON is fresh, but the browser UI shows stale timestamp, old snapshot count, or unavailable ranges.

Manual runbook:

```bash
python3 tools/update_local_market_site.py
python3 tools/check_market_pipeline_health.py
python3 tools/check_public_market_health.py
gh workflow run update-market-data.yml --repo SwampDad/idle-hacking-companion
gh run list --repo SwampDad/idle-hacking-companion --workflow update-market-data.yml --limit 10
gh run view <run-id> --repo SwampDad/idle-hacking-companion --log
curl -sL https://swampdad.github.io/idle-hacking-companion/data/latest.json
curl -sL https://swampdad.github.io/idle-hacking-companion/data/index.json
```

When VPS SSH is available, also check:

```bash
ssh scraper@46.224.146.164 "python3 -c \"import json; print(json.load(open('/home/scraper/data/market/latest.json')).get('generated_at'))\""
ssh scraper@46.224.146.164 "find /home/scraper/data/market/snapshots/recent -type f | wc -l"
```

Future internal alert options:

- A local maintainer script that checks live Pages JSON, GitHub Actions status, and optionally VPS health.
- A GitHub scheduled watchdog workflow that checks the public site and opens an issue on repeated stale/down states.
- GitHub issue creation for persistent failures with the exact failed layer in the title/body.
- Email or notification delivery only after credentials and routing are configured deliberately outside public docs.

Checker split:

- `tools/check_public_market_health.py` checks live GitHub Pages public JSON only.
- `tools/check_market_pipeline_health.py` is the operator checker: live Pages, local bundled data, GitHub Actions via `gh` when available, and VPS/source via SSH when available.
- `tools/check_market_pipeline_health.py --json` emits a dashboard-ready status model with `live_pages`, `local_data`, `github_actions`, `vps`, `cross_layer`, `verdict`, and `next_action`.
- `tools/update_local_market_site.py` is the canonical local update command: pull current public VPS market data, import public snapshots, regenerate compact history, build the site, and require the operator checker to pass.
- The operator checker expects a local SSH config alias named `ih-market-vps`.
- Password/key setup happens outside this repo. No passwords, private keys, tokens, or other secrets belong here.
- The VPS SSH target can be overridden with `IH_MARKET_VPS_SSH_HOST=...`.
- If VPS SSH is unavailable, the operator checker reports `INCONCLUSIVE` and prints exact manual commands.
- Trust decisions use timestamps, workflow status, schema validity, and commodity counts. Commodity price differences are not a fail rule.

Current publishing architecture:

- Keep GitHub Actions pulling public market data from the VPS.
- Do not switch to VPS pushing GitHub data yet.
- Future option: VPS-triggered `workflow_dispatch`, but only after credential-risk review.
- Avoid storing GitHub write credentials on the VPS unless explicitly approved.
- GitHub Actions schedule timing is best-effort; manual `workflow_dispatch`, watchdog checks, and the future dashboard should not rely only on cron timing.

## Site and Data Down Alerting

Outage checks should distinguish “site is down” from “site is up but data is stale.”

Public checks:

- Pages root loads with a successful HTTP status.
- `data/latest.json` loads and parses as JSON.
- `data/index.json` loads and parses as JSON.
- `latest.generated_at`, `index.generated_at`, and newest snapshot timestamp are parseable.
- Newest timestamp age is within threshold.
- Expected commodity count is present, currently 16.
- Expected ranges are present for available coverage, currently at least `1d`, and `7d` when live coverage supports it.

Alert wording should identify the failed layer:

- `Site down`: root page cannot be fetched.
- `Latest JSON invalid`: `latest.json` fetch or parse failed.
- `Index JSON invalid`: `index.json` fetch or parse failed.
- `Data delayed`: JSON is valid but newest timestamp is stale.
- `Partial feed`: JSON is valid but commodity/book count is lower than expected.
- `Range mismatch`: JSON is valid but expected history ranges are absent.

Public users only need a compact stale/down message. Maintainer diagnostics can include run IDs, timestamps, HTTP status codes, workflow conclusions, snapshot counts, and VPS health results.

## Future Operator Dashboard

The future Operator Dashboard, also called the Pipeline Trust Dashboard, is for maintainer trust rather than public user trust. It should be a visual version of `tools/check_market_pipeline_health.py`, expanded with VPS runtime checks and optional Nevamoen comparison. Its job is to show the whole data chain and identify the failing layer.

This dashboard should not make commodity price differences a fail rule. Trust decisions should be based primarily on timestamp freshness, source alignment, workflow status, schema validity, and expected commodity/book counts.

Dashboard data source:

- The dashboard should consume `python3 tools/check_market_pipeline_health.py --json` or share its underlying status model.
- JSON sections are `live_pages`, `local_data`, `github_actions`, `vps`, `cross_layer`, `verdict`, and `next_action`.
- Each section should carry a status, evidence fields, timestamps, age in minutes where available, and messages.
- The dashboard can add Nevamoen comparison as a diagnostic stage, but that comparison should not become the authority for trust.

Stages to show:

| Stage | Checks | Failure modes |
| --- | --- | --- |
| VPS Chrome collector/runtime | Chrome alive, memory, swap, disk, helper service, helper `/health`, market books/commodities `16/16`, latest VPS market timestamp. Current CLI uses SSH alias `ih-market-vps` by default. | Chrome crash, OOM, disk full, helper down, helper stale, partial market feed, SSH inconclusive |
| VPS market files | `latest.json` timestamp, snapshot count, newest/oldest snapshot, recent cadence/gaps, receipts if useful | latest stale, snapshots not advancing, cadence gaps, receipt/snapshot mismatch |
| GitHub Actions update workflow | Latest run status/conclusion, event (`schedule` or manual), run age, rsync/import/build/deploy success, data commit vs no-op | schedule delayed, run failed, import rejected data, build/deploy failed, no-op while VPS has newer data |
| GitHub Pages public JSON | Root loads, `latest.json` valid, `index.json` valid, latest/index timestamp alignment, commodity count, ranges, public data age | site down, invalid JSON, timestamp drift, partial feed, stale Pages artifact |
| Local repo / localhost | Local latest timestamp, local index timestamp, branch behind origin, uncommitted changes, localhost stale warning | stale bundled data, local checkout behind live, localhost mistaken for live |
| External comparison: Nevamoen | Reachable, latest chart timestamp, commodity coverage, bid/ask comparison at nearest timestamp, coverage gaps | comparator stale/down, coverage gaps, external mismatch |

Nevamoen comparison rules:

- Nevamoen can be used as an external public comparator/source-of-truth check, but not as proof that our data is wrong.
- If our site and Nevamoen disagree, flag `EXTERNAL MISMATCH` with both timestamps and nearest points.
- Price differences alone are not a fail rule.
- If either site is stale/dead and the other is fresh, the dashboard should say which source is stale/dead.
- Nevamoen remains diagnostic only unless a separate backfill/import task is explicitly approved.

Dashboard verdicts:

| Verdict | Meaning |
| --- | --- |
| `TRUSTED` | Live data is fresh, internally consistent, expected commodity count is present, GitHub update path is recent/successful, and VPS is fresh if available. |
| `LIVE DATA STALE` | Public JSON is valid but too old. |
| `VPS SOURCE STALE` | VPS collector/source timestamp is stale or helper reports unhealthy market state. |
| `GITHUB UPDATE DELAYED` | VPS may be fresh, but scheduled/manual update runs are delayed. |
| `GITHUB ACTIONS FAILED` | Latest relevant workflow completed with failure. |
| `PAGES STALE` | Data was committed or workflow succeeded, but GitHub Pages still serves old JSON. |
| `LOCALHOST STALE ONLY` | Live pipeline is trusted, but local bundled data is stale. |
| `EXTERNAL MISMATCH` | Our data and Nevamoen differ at nearest comparable timestamps; diagnostic only. |
| `INCONCLUSIVE` | A layer cannot be verified, such as VPS SSH unavailable from the current shell. |

Current operator state:

- 2026-05-11: `tools/check_market_pipeline_health.py` reached `TRUSTED` after SSH key setup.
- VPS, GitHub Actions, live Pages JSON, and local bundled data were aligned.
- If this regresses later and VPS is fresh but live is stale, trigger `update-market-data.yml`.
- If VPS is stale too, inspect Chrome/helper on the VPS.

Runtime reliability note:

- Chrome previously crashed because the VPS had 4 GB RAM and no swap; the Linux OOM killer killed Chrome.
- A 4 GB swapfile was added.
- The dashboard should monitor memory and swap so the next memory-pressure event is visible before it stops the collector.

## Graph Capabilities

Supported by our public snapshots:

| Graph or metric | Status | Notes |
| --- | --- | --- |
| Mid price over time | Supported | Good for table sparklines and simple price views. |
| Bid line | Supported | Good for detail graph. |
| Ask line | Supported | Good for detail graph. |
| Bid/ask spread band | Supported | Recommended default detail view. |
| Spread over time | Supported | Useful as a mode or subplot. |
| Spread percentage over time | Supported | Useful for comparing commodities with different price scales. |
| Bid volume over time | Supported from own snapshots | Use wording that reflects visible book volume. |
| Ask volume over time | Supported from own snapshots | Use wording that reflects visible book volume. |
| Total visible volume over time | Supported from own snapshots | Bid volume plus ask volume. |
| Best bid quantity over time | Supported from own snapshots | Useful in tooltip and stats. |
| Best ask quantity over time | Supported from own snapshots | Useful in tooltip and stats. |
| Bid level count over time | Supported from own snapshots | Useful as liquidity context. |
| Ask level count over time | Supported from own snapshots | Useful as liquidity context. |

Not currently supported or misleading:

| Graph or metric | Status | Reason |
| --- | --- | --- |
| Order-book ladder | Not recommended now | Current public history should not imply full historical ladder depth unless the exact ladder is stored and loaded deliberately. |
| Depth chart | Not recommended now | Historical depth is not available in compact form yet and would be expensive if derived from raw snapshots. |
| OHLC/candlesticks | Misleading | We do not have interval open/high/low/close trade prices. |
| Executed-order record chart | Not supported | Current data is public market book state and websocket order-book deltas, not a ledger of player-to-player executions. |

Use `Bid`, `Ask`, `Volume filled`, `Volume canceled`, and `Volume added` where appropriate. Keep websocket order-book deltas separate from visible book volume.

## Desired UX

- The market table remains compact and fast to scan.
- The table range selector should work for `1d`, `7d`, and full history when the full history option is labeled with its start date.
- Add `28d` later when enough public history exists.
- Do not show a vague `All` label in the compact table selector.
- The table sparkline uses mid-price by default.
- Do not add bid/ask mini sparklines unless later testing shows they are readable at table size.
- Clicking a commodity row, commodity name, or sparkline opens a detail drawer or modal.
- The detail graph defaults to bid and ask lines with a shaded spread band.
- Detail graph range buttons: show `1d` and `7d` for now; add `28d` later when enough history exists.
- Detail graph mode buttons are deferred. Keep the MVP focused on the price chart.
- Tooltip/crosshair contents:
  - timestamp
  - bid
  - ask
  - mid
  - spread
- Keep volume and source details out of the price tooltip for now; add them later in dedicated detail sections.
- Mobile behavior:
  - tap or drag shows the nearest-point tooltip
  - tap outside or close clears the tooltip/detail surface
- Show stale status, coverage gaps, and mixed provenance honestly.
- Avoid clutter by keeping advanced metrics in the detail surface rather than the table.

## Data Architecture

The current raw snapshot loading path is interim and does not scale. Long-range charting should use compact public history files generated from public snapshots.

Recommended public paths:

```text
site/public/data/history/index.json
site/public/data/history/commodities/{commodity}.json
```

Implemented importer path:

```bash
python3 tools/update_local_market_site.py
```

The canonical command pulls current public market data before import. It writes:

- `site/public/data/history/index.json`
- one file per commodity under `site/public/data/history/commodities/`

After the 2026-05-11 trust check, local bundled data was fresh and aligned with live Pages, GitHub Actions, and the VPS. Generated compact history currently has `1d`, `7d`, and since-start coverage when local data is fresh.

Do not trust local generated history by assumption. Run `python3 tools/update_local_market_site.py` first and confirm it passes before treating localhost/history files as representative of live coverage.

`python3 tools/import_public_market_data.py --no-pull` is offline/regression-only. It can regenerate compact history from stale local staged/public data and should not be the normal local refresh path.

The per-commodity history files should support both:

- the companion site detail charts
- existing Tampermonkey or market helper scripts for in-game history overlays

Extend existing helper scripts with history support later. Do not invent a separate helper system unless there is a concrete reason.

Schema requirements for multiple consumers:

- The schema must be versioned with `schema_version`.
- The schema should be stable enough for the companion site, Tampermonkey helper, and a future browser extension.
- Avoid frontend-only assumptions in the data shape. Files should describe data availability directly, not only how the current React UI happens to render it.
- Include `generated_at`, source/provenance, available ranges, fields available, point counts, earliest/latest timestamps, and gaps.
- Include per-range metadata so consumers can decide whether a control should be enabled.
- Include per-point provenance where mixed collector/backfill data is possible.
- Include volume fields only where our own public snapshots provide them.
- Allow fields to be absent or null when a source cannot honestly provide them.
- Keep commodity slugs stable and document additions/renames in `history/index.json`.
- Prefer additive schema changes; breaking changes should bump `schema_version`.

Recommended `history/index.json` shape:

```json
{
  "schema_version": 1,
  "generated_at": "2026-05-11T09:20:00Z",
  "source": "idle-hacking-companion-public-snapshots",
  "ranges": ["1d", "7d", "30d", "all"],
  "fields": ["bid", "ask", "mid", "spread", "spread_pct", "bid_volume", "ask_volume"],
  "commodities": {
    "chips": {
      "path": "commodities/chips.json",
      "ranges": ["1d", "7d", "30d", "all"],
      "earliest": "2026-05-03T04:31:42Z",
      "latest": "2026-05-11T09:13:30Z",
      "points": 192,
      "largest_gap_seconds": 3600
    }
  }
}
```

Recommended per-commodity shape:

```json
{
  "schema_version": 1,
  "commodity": "chips",
  "generated_at": "2026-05-11T09:20:00Z",
  "ranges": {
    "1d": {
      "bucket": "15m",
      "points": [
        {
          "t": "2026-05-11T09:13:30Z",
          "bid": 123,
          "ask": 128,
          "mid": 125.5,
          "spread": 5,
          "spread_pct": 3.98,
          "bid_volume": 1000,
          "ask_volume": 1200,
          "total_visible_volume": 2200,
          "best_bid_qty": 100,
          "best_ask_qty": 90,
          "bid_level_count": 4,
          "ask_level_count": 5,
          "source": "collector_snapshot",
          "source_snapshot": "snapshots/recent/2026-05-11T09-13-30Z.json"
        }
      ]
    }
  }
}
```

Downsampling targets:

| Range | Target point density |
| --- | --- |
| `1d` | 15-minute points |
| `7d` | hourly points |
| `28d` or `30d` | 4-6 hour points |
| `all` | daily points |

Provenance rules:

- Our VPS/public snapshots win when available because they come from our own pipeline and include richer public data.
- Third-party public backfill, if approved later, fills only missing bid/ask graph history.
- If two sources disagree at the same timestamp, flag the mismatch instead of silently overwriting.
- Volume-like fields must be omitted or null for third-party backfill unless sourced from our own public snapshots.

Cache strategy:

- The public site and helper scripts can cache history briefly to reduce repeated GitHub Pages requests.
- Consumers must always show `generated_at` or derived age when displaying history.
- Consumers should avoid caching stale data invisibly; a manual refresh action can be added later.
- Frontend cache behavior should never hide live JSON that is newer than the cached state.
- GitHub Pages cache behavior should be treated as an external variable and checked by freshness diagnostics.

## Volume Terminology and Data Support

There are two different public volume concepts and the UI should keep them separate.

Visible book volume comes from public market snapshots:

- `bidVolumeQty`
- `askVolumeQty`
- `volumeQty`
- `bestBidQty`
- `bestAskQty`
- `bidLevelCount`
- `askLevelCount`

These fields describe currently visible order-book liquidity in the snapshot. They are available in `site/public/data/latest.json` and compact history points under `site/public/data/history/commodities/*.json`.

Observed order-book changes come from public websocket deltas:

- `filled_qty` / `filledQty` -> `Volume filled`
- `canceled_qty` / `canceledQty` -> `Volume canceled`
- `added_qty` / `addedQty` -> `Volume added`

Use section title:

```text
Observed order-book changes
```

Use subtext:

```text
From public market websocket deltas.
```

`Volume filled` is the primary actual market activity/volume signal. `Volume added` and `Volume canceled` are liquidity and order-book movement signals.

Current data support:

- `site/public/data/latest.json` includes top-level `volume_changes` with websocket delta entries.
- Compact history currently includes visible book volume fields.
- Compact history does not yet include websocket delta history fields.

Observed websocket order-book changes are a differentiator versus Nevamoen, which was observed as public bid/ask chart history only. The old Recent Volume Changes section remains removed unless explicitly requested again.

Do not use these terms unless a future source explicitly supports them:

- `likely volume fill`
- `sales`
- `trades`
- `transactions`
- `confirmed sale`
- `confirmed trade`

## Existing Helper and Tampermonkey Integration

Read-only review of `/Users/buddy/projects/idle-hacker/scripts/IH_scripts/market_helper_v3.js` shows the current helper:

- Runs as a Tampermonkey userscript on `https://www.idlehacking.com/*`.
- Enriches visible equipment market rows using Better Item Tooltips stat comparison logic.
- Mounts a `MARKET HELPER` panel into the game UI.
- Adds settings, selected comparison stats, bookmarks, hide/unhide row behavior, debug output, and optional visible-row export controls.
- Injects runtime bridges for tooltip and equipment market state access.
- Watches the equipment market table with a `MutationObserver`.
- Polls route/UI state and refreshes after market controls change.
- Exposes a `window.IHMarketHelper` API for scanning, settings, bookmarks, visible listings, and debug info.

History support should plug into the existing helper, not replace it.

Recommended helper history flow:

- Fetch `https://swampdad.github.io/idle-hacking-companion/data/history/index.json` first.
- Use `history/index.json` to discover available commodities, ranges, freshness, and field availability.
- Fetch `history/commodities/{commodity}.json` only for the selected, expanded, or visible commodity.
- Cache briefly in memory or localStorage with `generated_at` and schema version checks.
- Revalidate or refetch when the user changes range or explicitly refreshes.

Recommended helper UI:

- Add a small in-game history panel or expandable section near the existing Market Helper panel.
- Add range buttons matching available ranges: `1d`, `7d`, `28d` or `30d`, `All`.
- Use a compact mid-price line by default.
- Add bid/ask view only if it remains readable in the in-game layout.
- Add hover/tap tooltip if feasible without fighting the game UI.
- Show source freshness and stale state just like the public site.

Do not add to the helper:

- private data
- credentials, cookies, tokens, or SSH material
- raw snapshot fetching
- huge all-commodity history downloads on page load
- claims about sales, trades, transactions, confirmed sales, or confirmed trades

## Browser Extension Path

Tampermonkey remains the fastest path for in-game history overlays because the current helper script already has UI mounting, route polling, and market-table integration.

A browser extension can come later after the public history schema stabilizes.

Extension notes:

- Reuse the same compact history JSON served by GitHub Pages.
- Request permissions only for the Idle Hacking site and the GitHub Pages data host.
- Avoid bundling stale market history if live JSON can be fetched.
- Cache only briefly and show `generated_at`/age in any UI.
- Keep docs explicit that the extension consumes public market data only.
- Avoid broad host permissions, private account scraping, cookies, tokens, or credential access.

## Future Work and Implementation Plan

### Phase 0 - Trust and Watchdog Follow-Up

Keep the public freshness/status line and add maintainer-facing checks outside the UI.

- Done: add `tools/check_public_market_health.py`, a public-safe health command that checks live Pages root, `latest.json`, and `index.json`.
- Done: add `tools/check_market_pipeline_health.py`, an operator command that checks live, local, GitHub Actions, and VPS/source when available.
- Done: localhost warns when local bundled data is stale.
- Distinguish stale source data from workflow delay, workflow failure, deploy failure, Pages stale JSON, and frontend display issues.
- Use warning/alert/critical thresholds of 90 minutes, 3 hours, and 6+ hours.
- Next: add a scheduled watchdog workflow or GitHub issue creation only after the signal is reliable.

Likely files:

- `tools/check_public_market_health.py`
- future public-safe scheduled watchdog workflow, location to be decided
- documentation in this plan or a future operations doc

Risks:

- Alert noise if GitHub Actions schedule jitter is treated as failure too aggressively.
- False confidence if the check only validates one layer.
- Private notification credentials must not be committed.

Validation:

```bash
curl -sL https://swampdad.github.io/idle-hacking-companion/data/latest.json
curl -sL https://swampdad.github.io/idle-hacking-companion/data/index.json
python3 tools/check_public_market_health.py
gh run list --repo SwampDad/idle-hacking-companion --workflow update-market-data.yml --limit 10
```

Safe to deploy independently:

- Yes, if checks are read-only and public-safe.

### Phase A - Stabilize Current Visible Behavior

Make the existing range selector real for table sparklines, or replace it with the same control wired to actual data.

- Done: the range selector now controls the table sparkline source range.
- Done: the table selector shows `1d`, `7d`, and full history with a concrete `Since <date>` label when available.
- Done: `28d` is commented in code as the next exact longer window to enable once data exists.
- Done: the sparkline remains a single mid-price series.
- Done: the freshness/status line remains visible.
- Done: graph architecture and table columns were not changed.
- Remaining issue: raw snapshot fan-out still powers table history until Phase C moves consumers to compact history files.

Likely files:

- `site/src/prototype/PrototypeApp.jsx`
- `site/src/prototype/Sparkline.jsx` if needed
- `site/src/styles.css`

Risks:

- Loading every raw snapshot for wider table ranges can make initial load worse. Keep this phase bounded or pair it quickly with Phase C.

Validation:

```bash
cd site && npm run build
```

Safe to deploy independently:

- Yes, if browser load does not regress and the selector actually changes the rendered sparkline range.

### Phase B - Compact History Generation

Generate compact public history from public snapshots.

- Done: add `history/index.json`.
- Done: add `history/commodities/*.json`.
- Done: include `1d`, `7d`, `30d`, and `all` ranges when enough source coverage exists.
- Done: apply the downsampling targets above.
- Done: preserve collector provenance per point.
- Done: canonical local update command regenerates compact history from freshly pulled VPS public data.
- Remaining issue: frontend still needs to consume compact history.

Likely files:

- `tools/update_local_market_site.py`
- `tools/import_public_market_data.py`
- `site/public/data/history/*`
- existing tests, if a relevant test structure exists

Risks:

- Schema churn after helpers start consuming the files.
- Accidentally publishing derived fields that imply unsupported trade/sale semantics.
- Repository and Pages size growth if range files are not compact enough.

Validation:

```bash
cd site && npm run build
```

Safe to deploy independently:

- Yes, if the new files are additive and no frontend behavior depends on them yet.

### Phase C - Frontend History Loader

Stop using all raw snapshots for long-range charts.

- Done for the detail drawer: load compact per-commodity history on demand through `site/src/prototype/historyData.js`.
- Keep the initial page lightweight.
- Use raw recent snapshots only where they are still needed for current table stats or short-range compatibility.
- Remaining issue: table sparklines still use raw snapshot fan-out and should move to compact history next.

Likely files:

- `site/src/prototype/PrototypeApp.jsx`
- `site/src/prototype/historyData.js`
- `site/src/prototype/HistoryChart.jsx`

Risks:

- Partial history fetch failures need clean fallback states.
- Cache behavior must not make stale data look current.

Validation:

```bash
cd site && npm run build
```

Safe to deploy independently:

- Yes, if the table still renders from current public data and history fetch failures degrade gracefully.

### Phase D - Detail Drawer or Modal

Add the large commodity history view.

- Done: clicking row, name, or sparkline opens the detail surface.
- Done: add a `HistoryChart` component.
- Done: default graph renders bid and ask lines with a shaded spread band.
- Done: add range controls for `1d` and `7d`.
- Done: keep `28d` planned in code, hidden until enough data exists.
- Done: defer mode controls; the MVP renders the price chart only.
- Done: add desktop pointer tooltip/crosshair with timestamp, bid, ask, mid, and spread.
- Remaining issue: mobile interaction and a dedicated `Observed order-book changes` section/card need follow-up.

Likely files:

- `site/src/prototype/PrototypeApp.jsx`
- `site/src/prototype/HistoryChart.jsx`
- `site/src/styles.css`

Risks:

- Chart clutter on mobile.
- Tooltip and crosshair interactions can conflict with scrolling.
- Need honest empty, loading, stale, and gap states.

Validation:

```bash
cd site && npm run build
```

Safe to deploy independently:

- Yes, if the detail surface is optional and the existing table remains stable.

### Phase E - Helper and Tampermonkey Support

Document the stable public history schema and extend existing market helper scripts to consume it.

- Use the same public history files as the companion site.
- Do not implement a separate history helper system.
- Do not include private data or credentials.
- Fetch `history/index.json` first, then commodity history on demand.
- Keep all-commodity downloads off initial page load.
- Keep raw snapshot fetching out of the helper.
- Add only small, readable in-game chart UI.

Likely files:

- existing public market helper/Tampermonkey files, currently including `/Users/buddy/projects/idle-hacker/scripts/IH_scripts/market_helper_v3.js`
- schema docs under `site/src/prototype/` or a future docs location

Risks:

- Helper scripts may cache old schema assumptions.
- Public Pages caching can delay helper updates.
- In-game layout constraints may make rich charts hard to read.
- Cross-origin fetch behavior must be tested from the userscript context.

Validation:

- Build site if helper docs or served assets change.
- Manual helper smoke test when implementation is requested.

Safe to deploy independently:

- Yes, after schema is stable and helper behavior is tested.

### Phase F - Browser Extension, Optional

Package a browser extension only after Tampermonkey history support and the compact schema are stable.

- Reuse the same compact history JSON.
- Keep permissions narrow: Idle Hacking and the GitHub Pages data host only.
- Avoid bundled stale market data when live JSON is fetchable.
- Document public-data-only boundaries.

Likely files:

- extension manifest and content script files, location to be decided
- shared schema docs

Risks:

- Permission overreach can reduce trust.
- Extension release/versioning adds maintenance overhead.
- Browser store packaging can slow iteration compared with Tampermonkey.

Validation:

- Browser extension local load test.
- Same public history fetch tests as the helper.

Safe to deploy independently:

- No. Wait until schema and helper behavior are stable.

### Phase G - Optional Nevamoen Backfill

Use Nevamoen only as explicitly approved public bid/ask history backfill.

- Source: public commodity pages.
- Data shape observed: `[unix_timestamp_seconds, bid_price_cents, ask_price_cents]`.
- Available ranges observed: `24h`, `7d`, `28d`, `all`.
- Do not import into raw snapshot history.
- Do not add volume fields to backfilled points.

Likely files:

- a dedicated public backfill/import tool, if approved
- `site/public/data/history/*`
- provenance documentation

Risks:

- Third-party layout can change.
- Backfill provenance must remain visible.
- Same-timestamp disagreements with our collector should be flagged, not overwritten.

Validation:

```bash
cd site && npm run build
```

Safe to deploy independently:

- Only after explicit approval and a provenance review.

## Reliability and Risk Checklist

Before implementing or deploying major history work, check these risks:

- GitHub Pages caching could serve old JSON after a successful deploy.
- Browser cache could show stale JSON while the live URL is fresh.
- Too many raw snapshot requests can make initial page load slow or brittle.
- Raw snapshot retention can grow repo size and Pages deploy size quickly.
- GitHub Actions schedule jitter can create multi-hour gaps even when the workflow is healthy.
- GitHub Actions workflows can be disabled after inactivity or affected by permission changes.
- SSH key rotation or compromised key history can break or undermine trust in the update path.
- VPS Chrome, Tampermonkey, or helper service can stop while GitHub Actions keeps running.
- VPS disk can fill, preventing `latest.json`, snapshots, or receipts from advancing.
- A malformed snapshot can break import or silently drop history if validation is too loose.
- Partial commodity/book counts must be detected and surfaced.
- Commodities can be renamed or added; schema and UI should not assume exactly today’s list forever.
- Timezone display bugs can make fresh data look stale or vice versa.
- Mobile chart usability can fail if hover-only interactions are assumed.
- Tooltip/crosshair work can hurt performance if every pointer move rerenders too much.
- Public data can be copied by other sites; do not publish anything that should remain private.
- Third-party backfill provenance can confuse users if mixed with our collector data without labels.
- Helper scripts can drift from the public schema if schema changes are not versioned.
- Extension permissions can overreach if not kept narrow.

## Repo Hygiene Notes

Local working state can mix code, generated public data, and historical planning artifacts. Before deployment or commits, group changes deliberately.

Recommended future commit groups:

1. Docs and planning reports:
   - `site/src/prototype/MARKET_HISTORY_AND_GRAPHS_PLAN.md`
   - historical reports under `site/src/prototype/*.md`
   - README updates
2. Freshness/status UI and real table range selector:
   - `site/src/prototype/PrototypeApp.jsx`
   - `site/src/styles.css`
3. Compact history generation:
   - `tools/import_public_market_data.py`
4. Health/operator checker scripts:
   - `tools/check_public_market_health.py`
   - `tools/check_market_pipeline_health.py`
5. Generated public history/data files:
   - `site/public/data/history/index.json`
   - `site/public/data/history/commodities/*.json`
6. Stale or unrelated untracked files to review separately:
   - `site/public/guides/`
   - `site/src/prototype/mockFeed.js`

Deploy safety notes:

- Local bundled public data can be stale.
- Do not commit stale generated data accidentally.
- Check `git status -sb` before deployment; if the local branch is behind `origin/main`, reconcile with origin before publishing.
- Generated local history from stale local snapshots should not be treated as representative of live coverage.
- Do not delete ambiguous untracked files until their origin/purpose is confirmed.

## Acceptance Criteria

- `cd site && npm run build` passes for implementation phases.
- No private data fields are added.
- No Recent Volume Changes section is restored.
- The table range selector actually affects table sparkline range.
- Freshness status remains visible.
- Initial page load does not get worse long-term; compact history addresses scaling.
- Detail graph shows bid, ask, mid, and spread honestly.
- Volume context is separated into visible book volume and future observed order-book changes.
- Detail graph does not claim sales, trades, transactions, confirmed sales, or confirmed trades.
- Public schema is usable by both the companion site and existing helper scripts.
- GitHub Pages JSON is treated as public and scrapeable.
- Watchdog/alert checks identify the failed layer instead of only saying “stale.”
- Helper and extension consumers fetch compact history on demand rather than loading raw snapshots.

## Existing Docs to Clean Up Later

- `site/src/prototype/README.md` contains old local-data observations and stale pipeline conclusions that should be refreshed or marked historical.
- `site/src/prototype/GRAPH_DESIGN_AND_DATA_CAPABILITIES.md` contains useful capability analysis, but its earlier “keep table 1d only / hide selector” recommendation is superseded by this plan.
- `site/src/prototype/PIPELINE_TRUST_REPORT.md` contains an initial stale-data hypothesis and later evidence that the manual workflow succeeded; it should be condensed when the docs are reorganized.
- Root `README.md` and `site/README.md` are still minimal and could eventually link to this plan.
