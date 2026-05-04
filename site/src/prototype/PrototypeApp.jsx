import React, { useEffect, useMemo, useState } from 'react';
import { Sparkline } from './Sparkline';

const links = {
  official: 'https://www.idlehacking.com/',
  play: 'https://www.idlehacking.com/play',
  steam: 'https://store.steampowered.com/app/4453290/Idle_Hacking_An_Inaction_RPG/',
  discord: 'https://discord.com/invite/A62Chy8FKk',
};


function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unavailable';

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date);
}

function formatRelativeAge(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'unavailable';

  const diffMs = Date.now() - date.getTime();
  const pastMs = Math.max(0, diffMs);
  const minutes = Math.floor(pastMs / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  return `${days}d ago`;
}

function formatDateTimeWithZone(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unavailable';

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
    timeZoneName: 'short',
  }).format(date);
}

function formatMarketUpdated(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Last updated unavailable';

  return `Last updated ${formatRelativeAge(value)} · ${formatDateTimeWithZone(value)}`;
}

function formatNumber(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat(undefined).format(Number(value));
}

function formatCompactQuantity(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(Number(value));
}

function formatCompactCredits(value) {
  if (!Number.isFinite(Number(value))) return '—';
  const credits = Number(value) / 100;

  if (credits < 100) {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: credits >= 10 ? 1 : 2,
      maximumFractionDigits: credits >= 10 ? 1 : 2,
    }).format(credits);
  }

  if (credits < 1000) {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: credits >= 100 ? 0 : 1,
      maximumFractionDigits: credits >= 100 ? 1 : 1,
    }).format(credits);
  }

  return new Intl.NumberFormat(undefined, {
    notation: 'compact',
    maximumFractionDigits: 1,
  }).format(credits);
}

function formatMainCredits(value) {
  if (!Number.isFinite(Number(value))) return '—';
  const credits = Number(value) / 100;

  if (Math.abs(credits) >= 1_000_000_000) {
    return new Intl.NumberFormat(undefined, {
      notation: 'compact',
      maximumFractionDigits: 1,
    }).format(credits);
  }

  if (Math.abs(credits) >= 1000) {
    return new Intl.NumberFormat(undefined, {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    }).format(credits);
  }

  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: 2,
  }).format(credits);
}

function formatRoundedCreditSubline(value) {
  if (!Number.isFinite(Number(value))) return '—';
  const credits = Number(value) / 100;
  const compacted = Math.abs(credits) >= 1000;

  const text = compacted
    ? new Intl.NumberFormat(undefined, {
        notation: 'compact',
        maximumFractionDigits: 1,
      }).format(credits)
    : new Intl.NumberFormat(undefined, {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }).format(credits);

  return compacted ? `≈${text}` : text;
}

function formatPercent(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return `${Number(value) > 0 ? '+' : ''}${Number(value).toFixed(1)}%`;
}

function getMovePct(row) {
  const first = row.history7d?.[0];
  const last = row.history7d?.[row.history7d.length - 1];
  if (!Number.isFinite(Number(first)) || !Number.isFinite(Number(last)) || first === 0) return 0;
  return ((last - first) / first) * 100;
}

function getTrend(row) {
  const move = getMovePct(row);
  if (move > 0.5) return 'up';
  if (move < -0.5) return 'down';
  return 'flat';
}

function dataUrl(path) {
  const cleanPath = path.replace(/^\/+/, '');
  const baseUrl = new URL(import.meta.env.BASE_URL, window.location.href);
  return new URL(cleanPath, baseUrl).toString();
}

async function loadJson(path) {
  const response = await fetch(dataUrl(path), { cache: 'no-store' });
  if (!response.ok) throw new Error(`${path} failed with ${response.status}`);
  return response.json();
}

function getMidPriceCents(row) {
  const bid = Number(row?.bestBidCents);
  const ask = Number(row?.bestAskCents);
  if (Number.isFinite(bid) && Number.isFinite(ask)) return Math.round((bid + ask) / 2);
  if (Number.isFinite(row?.midPriceCents)) return Number(row.midPriceCents);
  if (Number.isFinite(bid)) return bid;
  if (Number.isFinite(ask)) return ask;
  return null;
}

function getSpreadPct(row) {
  const bid = Number(row?.bestBidCents);
  const ask = Number(row?.bestAskCents);
  if (!Number.isFinite(bid) || !Number.isFinite(ask) || ask <= 0 || ask < bid) return null;
  return ((ask - bid) / ask) * 100;
}

function normalizeCommodity(row) {
  return {
    ...row,
    midPriceCents: getMidPriceCents(row),
    spreadPct: getSpreadPct(row),
  };
}

function displayCommodityName(label) {
  if (label === 'Premium Access Key (30d)' || label === 'Premium Access Keys 30d') {
    return 'Premium Key (30d)';
  }
  return label || '—';
}

function formatDelta(value) {
  if (!Number.isFinite(Number(value))) return '—';
  const n = Number(value);
  return `${n > 0 ? '+' : ''}${n.toFixed(1)}%`;
}

function SortHeader({ label, field, sortState, onSort, className = '' }) {
  const active = sortState.field === field;
  const marker = active ? (sortState.direction === 'asc' ? ' ↑' : ' ↓') : ' ↕';

  return (
    <button
      type="button"
      className={`sort-header ${active ? 'sort-header-active' : ''} ${className}`}
      onClick={() => onSort(field)}
      aria-label={`Sort by ${label}`}
      aria-sort={active ? (sortState.direction === 'asc' ? 'ascending' : 'descending') : 'none'}
    >
      <span>{label}</span><span className={active ? 'sort-marker' : 'sort-marker sort-marker-muted'}>{marker}</span>
    </button>
  );
}

function buildHistorySnapshotsMap(historySnapshots) {
  const entries = [];
  const seen = new Set();

  for (const snapshot of Array.isArray(historySnapshots) ? historySnapshots : []) {
    const generatedAt = String(snapshot?.generated_at || snapshot?.generatedAt || '').trim();
    const stamp = Date.parse(generatedAt);
    const path = String(snapshot?.path || '').trim();
    const key = generatedAt || path;

    if (!Number.isFinite(stamp) || !key || seen.has(key)) continue;
    seen.add(key);
    entries.push({
      generatedAt,
      stamp,
      feed: snapshot.feed || snapshot,
    });
  }

  entries.sort((left, right) => left.stamp - right.stamp);

  if (!entries.length) {
    return new Map();
  }

  const newestStamp = entries[entries.length - 1].stamp;
  const cutoff = newestStamp - 24 * 60 * 60 * 1000;
  const recent = entries.filter((entry) => entry.stamp >= cutoff);
  const historyMap = new Map();

  for (const entry of recent) {
    const commodities = Array.isArray(entry.feed?.market?.commodities) ? entry.feed.market.commodities : [];

    for (const row of commodities) {
      const id = String(row?.id || '').trim();
      const midPriceCents = getMidPriceCents(row);

      if (!id || !Number.isFinite(midPriceCents)) continue;

      if (!historyMap.has(id)) {
        historyMap.set(id, []);
      }

      historyMap.get(id).push(midPriceCents);
    }
  }

  return historyMap;
}

export function PrototypeApp() {
  const [latest, setLatest] = useState(null);
  const [index, setIndex] = useState(null);
  const [historySnapshots, setHistorySnapshots] = useState([]);
  const [loadState, setLoadState] = useState({ loading: true, error: '' });


  useEffect(() => {
    let cancelled = false;

    async function loadData() {
      setLoadState({ loading: true, error: '' });

      try {
        const [latestJson, indexJson] = await Promise.all([
          loadJson('/data/latest.json'),
          loadJson('/data/index.json'),
        ]);

        if (!cancelled) {
          setLatest(latestJson);
          setIndex(indexJson);
          setLoadState({ loading: false, error: '' });
        }
      } catch (error) {
        if (!cancelled) {
          setLoadState({ loading: false, error: String(error?.message || error) });
        }
      }
    }

    loadData();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function loadHistorySnapshots() {
      const recent = Array.isArray(index?.recent) ? index.recent : [];

      if (!recent.length) {
        setHistorySnapshots([]);
        return;
      }

      const settled = await Promise.allSettled(
        recent.map(async (row) => {
          if (!row?.path) return null;

          const snapshot = await loadJson(`/data/${row.path}`);
          return {
            path: row.path,
            generated_at: row.generated_at || snapshot?.generated_at || '',
            feed: snapshot,
          };
        })
      );

      if (cancelled) return;

      const deduped = new Map();
      for (const result of settled) {
        if (result.status !== 'fulfilled' || !result.value) continue;

        const item = result.value;
        const key = String(item.generated_at || item.path || '').trim();
        if (!key || deduped.has(key)) continue;
        deduped.set(key, item);
      }

      setHistorySnapshots(Array.from(deduped.values()).sort((left, right) => {
        return Date.parse(left.generated_at || left.path || '') - Date.parse(right.generated_at || right.path || '');
      }));
    }

    loadHistorySnapshots();

    return () => {
      cancelled = true;
    };
  }, [index]);

  const commodities = useMemo(() => {
    const historyMap = buildHistorySnapshotsMap(historySnapshots);

    return (latest?.market?.commodities || []).map((row) => {
      const history7d = historyMap.get(row.id) || [];
      return normalizeCommodity({
        ...row,
        history7d,
      });
    });
  }, [latest, historySnapshots]);

  const generatedAt = latest?.generated_at || '';
  const ranges = index?.ranges || {};
  const historyCount = historySnapshots.length;

  return (
    <div className="prototype-shell">
      <header className="site-topbar">
        <a className="site-mark" href="/" aria-label="Idle Hacking Market Viewer home">
          <strong>Idle Hacking Market Viewer</strong>
        </a>
      </header>

      <main className="prototype-page">
        {loadState.loading ? <div className="panel empty-state">Loading public market data…</div> : null}
        {loadState.error ? <div className="panel empty-state">Could not load public market data: {loadState.error}</div> : null}
        {!loadState.loading && !loadState.error ? (
          <MarketPage
            commodities={commodities}
            generatedAt={generatedAt}
            ranges={ranges}
            historyCount={historyCount}
          />
        ) : null}
      </main>

      <SiteFooter />
    </div>
  );
}

function MarketPage({ commodities, generatedAt, ranges, historyCount }) {
  const [includeEssences, setIncludeEssences] = useState(false);
  const [historyRange, setHistoryRange] = useState(ranges.has_1d ? '1d' : 'all');
  const [sortState, setSortState] = useState({ field: 'name', direction: 'asc' });

  const rangeOptions = [
    ranges.has_1d ? { value: '1d', label: '1d' } : null,
    ranges.has_7d ? { value: '7d', label: '7d' } : null,
    ranges.has_30d ? { value: '30d', label: '30d' } : null,
    ranges.has_all ? { value: 'all', label: 'All' } : null,
  ].filter(Boolean);

  useEffect(() => {
    if (ranges.has_1d && historyRange !== '1d') setHistoryRange('1d');
    else if (!ranges.has_1d && ranges.has_all && historyRange !== 'all') setHistoryRange('all');
  }, [ranges.has_1d, ranges.has_all]);

  const handleSort = (field) => {
    setSortState((current) => ({
      field,
      direction: current.field === field && current.direction === 'asc' ? 'desc' : 'asc',
    }));
  };

  const visibleCommodities = useMemo(() => {
    const rows = includeEssences
      ? commodities
      : commodities.filter((row) => !row.isEssence);

    return [...rows].sort((left, right) => {
      if (sortState.field === 'name') {
        const a = displayCommodityName(left.label).toLowerCase();
        const b = displayCommodityName(right.label).toLowerCase();
        const cmp = a.localeCompare(b);
        return sortState.direction === 'asc' ? cmp : -cmp;
      }

      let a = null;
      let b = null;

      if (sortState.field === 'price') {
        a = Number(left.midPriceCents);
        b = Number(right.midPriceCents);
      } else if (sortState.field === 'diff') {
        a = Number(getMovePct(left));
        b = Number(getMovePct(right));
      } else if (sortState.field === 'spread') {
        a = Number(getSpreadPct(left));
        b = Number(getSpreadPct(right));
      } else if (sortState.field === 'volume') {
        a = Number(left.volumeQty);
        b = Number(right.volumeQty);
      }

      const aValid = Number.isFinite(a);
      const bValid = Number.isFinite(b);

      if (!aValid && !bValid) return 0;
      if (!aValid) return 1;
      if (!bValid) return -1;

      return sortState.direction === 'asc' ? a - b : b - a;
    });
  }, [commodities, includeEssences, sortState]);

  return (
    <div className="page-stack">
      <section className="page-heading">
        <h1>Idle Hacking Market Viewer</h1>
        <div className="page-updated">{formatMarketUpdated(generatedAt)}</div>
      </section>

      <section className="panel market-panel">
        <div className="section-head">
          <div>
            <h2>Commodities</h2>
          </div>
          <label className="filter-check">
            <input
              type="checkbox"
              checked={includeEssences}
              onChange={(event) => setIncludeEssences(event.target.checked)}
            />
            <span>include essences</span>
          </label>
        </div>
        <div className="table-wrap">
          <table className="market-table">
            <colgroup>
              <col className="col-commodity" />
              <col className="col-price" />
              <col className="col-sparkline" />
              <col className="col-diff" />
              <col className="col-spread" />
              <col className="col-volume" />
            </colgroup>
            <thead>
              <tr>
                <th>
                  <SortHeader label="Name" field="name" sortState={sortState} onSort={handleSort} />
                </th>
                <th>
                  <div className="price-head">
                    <SortHeader label="Price" field="price" sortState={sortState} onSort={handleSort} />
                    <label className="range-select-label">
                      <span className="sr-only">Price history range</span>
                      <select
                        className="range-select"
                        value={historyRange}
                        onChange={(event) => setHistoryRange(event.target.value)}
                      >
                        {rangeOptions.map((option) => (
                          <option value={option.value} key={option.value}>{option.label}</option>
                        ))}
                      </select>
                    </label>
                  </div>
                </th>
                <th className="sparkline-head"><span className="sr-only">Price history sparkline</span></th>
                <th className="num">
                  <SortHeader label="Diff" field="diff" sortState={sortState} onSort={handleSort} className="sort-header-num" />
                </th>
                <th className="num">
                  <SortHeader label="Spread" field="spread" sortState={sortState} onSort={handleSort} className="sort-header-num" />
                </th>
                <th className="num">
                  <SortHeader label="Volume" field="volume" sortState={sortState} onSort={handleSort} className="sort-header-num" />
                </th>
              </tr>
            </thead>
            <tbody>
              {visibleCommodities.map((row) => {
                const trend = getTrend(row);
                const hasHistory = historyCount > 1 && Array.isArray(row.history7d) && row.history7d.length > 1;
                const spread = getSpreadPct(row);

                return (
                  // TODO: add commodity detail panel with larger price/volume chart when real history is available.
                  <tr key={row.id}>
                    <td>
                      <div className="commodity-name">{displayCommodityName(row.label)}</div>
                    </td>
                    <td className="price-cell">
                      <div className="price-primary">{formatMainCredits(row.midPriceCents)}</div>
                      <div className="price-subline price-bid">
                        <span className="stack-label">Bid</span> {formatRoundedCreditSubline(row.bestBidCents)}
                      </div>
                      <div className="price-subline price-ask">
                        <span className="stack-label">Ask</span> {formatRoundedCreditSubline(row.bestAskCents)}
                      </div>
                    </td>
                    <td className="sparkline-cell">
                      {hasHistory ? <Sparkline values={row.history7d} trend={trend} /> : <span className="muted">history pending</span>}
                    </td>
                    <td className={`num diff-cell delta-${trend}`}>
                      {hasHistory ? formatDelta(getMovePct(row)) : '—'}
                    </td>
                    <td className="num spread-cell">
                      {Number.isFinite(spread) ? `${spread.toFixed(1)}%` : '—'}
                    </td>
                    <td className="num volume-cell">{formatCompactQuantity(row.volumeQty)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {!visibleCommodities.length ? (
            <div className="empty-state">No commodities match the current filters.</div>
          ) : null}
        </div>
      </section>

      {/* Keep Recent Volume Changes off the page for now. User explicitly requested this section stay removed. */}
    </div>
  );
}

function Metric({ label, value, subvalue, trend }) {
  return (
    <div className={`metric proto-metric ${trend ? `metric-${trend}` : ''}`}>
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
      {subvalue ? <div className="metric-subvalue">{subvalue}</div> : null}
    </div>
  );
}

function SiteFooter() {
  return (
    <footer className="site-footer">
      <nav aria-label="Footer">
        <a href={links.official}>Official Site</a>
        <a href={links.steam}>Steam</a>
        <a href={links.discord}>Discord</a>
      </nav>
    </footer>
  );
}
