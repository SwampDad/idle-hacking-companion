import React, { useEffect, useMemo, useState } from 'react';
import { HistoryChart } from './HistoryChart';
import { Sparkline } from './Sparkline';
import {
  getAvailableHistoryRanges as getCompactHistoryRanges,
  getHistoryRangeLabel,
  loadCommodityHistory,
  loadHistoryIndex,
} from './historyData';

const links = {
  official: 'https://www.idlehacking.com/',
  play: 'https://www.idlehacking.com/play',
  steam: 'https://store.steampowered.com/app/4453290/Idle_Hacking_An_Inaction_RPG/',
  discord: 'https://discord.com/invite/A62Chy8FKk',
};

const TABLE_HISTORY_RANGES = [
  '1d',
  '7d',
  // Add '28d' here once the public compact history has enough source coverage.
];
const RANGE_CUTOFF_MS = {
  '1d': 24 * 60 * 60 * 1000,
  '7d': 7 * 24 * 60 * 60 * 1000,
  // Prefer 28d over a calendar "1mo" label so the chart window is exact.
  '28d': 28 * 24 * 60 * 60 * 1000,
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

function formatDetailedRelativeAge(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'unavailable';

  const diffMs = Date.now() - date.getTime();
  const pastMs = Math.max(0, diffMs);
  const minutes = Math.floor(pastMs / 60000);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) {
    const remMinutes = minutes % 60;
    return remMinutes ? `${hours}h ${remMinutes}m ago` : `${hours}h ago`;
  }
  return `${days}d ago`;
}

function getAvailableRanges(ranges) {
  if (Array.isArray(ranges?.available)) {
    return ranges.available
      .map((range) => String(range).trim())
      .filter((range) => TABLE_HISTORY_RANGES.includes(range));
  }

  return [
    ranges?.has_1d ? '1d' : null,
    ranges?.has_7d ? '7d' : null,
    // ranges?.has_28d ? '28d' : null,
  ].filter((range) => range && TABLE_HISTORY_RANGES.includes(range));
}

function getDefaultHistoryRange(ranges) {
  const available = getAvailableRanges(ranges);
  const configuredDefault = String(ranges?.default || '').trim();

  if (available.includes(configuredDefault)) return configuredDefault;
  if (available.includes('1d')) return '1d';
  return available[0] || '1d';
}

function getHistoryRangeCutoff(newestStamp, range) {
  if (range === 'all') return Number.NEGATIVE_INFINITY;

  const duration = RANGE_CUTOFF_MS[range] || RANGE_CUTOFF_MS['1d'];
  return newestStamp - duration;
}

function getBestHistoryRangeLabel(ranges) {
  const available = getAvailableRanges(ranges);
  const priority = ['7d', '1d'];
  const best = priority.find((range) => available.includes(range));

  if (!best) return '';
  return `${best} history available`;
}

function getMarketFreshness(value, { snapshotCount = 0, ranges = {} } = {}) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return {
      isStale: false,
      text: 'Last updated unavailable',
    };
  }

  const stale = Date.now() - date.getTime() > 90 * 60 * 1000;
  const parts = [
    stale ? `Data delayed · last update ${formatDetailedRelativeAge(value)}` : formatMarketUpdated(value),
  ];

  return {
    isStale: stale,
    text: parts.join(' · '),
  };
}

function isLocalHost() {
  return ['localhost', '127.0.0.1', '::1'].includes(window.location.hostname);
}

function isOlderThan(value, minutes) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return false;
  return Date.now() - date.getTime() > minutes * 60 * 1000;
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

function formatPlainPercent(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return `${Number(value).toFixed(1)}%`;
}

function getMovePct(row) {
  const first = row.sparklineHistory?.[0];
  const last = row.sparklineHistory?.[row.sparklineHistory.length - 1];
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

function buildHistorySnapshotsMap(historySnapshots, range = '1d') {
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
  const cutoff = getHistoryRangeCutoff(newestStamp, range);
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
  const [historyRange, setHistoryRange] = useState('1d');
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

      // Interim path: raw snapshot fan-out keeps the table range selector honest for now.
      // Compact history files should replace this before longer history ranges grow.
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

  useEffect(() => {
    if (!index?.ranges) return;

    const available = getAvailableRanges(index.ranges);
    const nextRange = available.includes(historyRange)
      ? historyRange
      : getDefaultHistoryRange(index.ranges);

    if (nextRange !== historyRange) {
      setHistoryRange(nextRange);
    }
  }, [index?.ranges, historyRange]);

  const commodities = useMemo(() => {
    const historyMap = buildHistorySnapshotsMap(historySnapshots, historyRange);

    return (latest?.market?.commodities || []).map((row) => {
      const sparklineHistory = historyMap.get(row.id) || [];
      return normalizeCommodity({
        ...row,
        sparklineHistory,
      });
    });
  }, [latest, historyRange, historySnapshots]);

  const generatedAt = latest?.generated_at || '';
  const ranges = index?.ranges || {};
  const snapshotCount = Array.isArray(index?.recent) ? index.recent.length : historySnapshots.length;
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
            snapshotCount={snapshotCount}
            historyCount={historyCount}
            historyRange={historyRange}
            onHistoryRangeChange={setHistoryRange}
          />
        ) : null}
      </main>

      <SiteFooter />
    </div>
  );
}

function MarketPage({
  commodities,
  generatedAt,
  ranges,
  snapshotCount,
  historyCount,
  historyRange,
  onHistoryRangeChange,
}) {
  const [includeEssences, setIncludeEssences] = useState(false);
  const [sortState, setSortState] = useState({ field: 'name', direction: 'asc' });
  const [selectedCommodityId, setSelectedCommodityId] = useState(null);
  const freshness = getMarketFreshness(generatedAt, { snapshotCount, ranges });
  const showLocalStaleWarning = isLocalHost() && isOlderThan(generatedAt, 90);

  const availableRanges = getAvailableRanges(ranges);
  const rangeOptions = (availableRanges.length ? availableRanges : [historyRange]).map((range) => ({
    value: range,
    label: range,
  }));

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

  const selectedCommodity = useMemo(() => {
    if (!selectedCommodityId) return null;
    return commodities.find((row) => row.id === selectedCommodityId) || null;
  }, [commodities, selectedCommodityId]);

  const openCommodityDetail = (commodityId) => {
    setSelectedCommodityId(commodityId);
  };

  return (
    <div className="page-stack">
      <section className="page-heading">
        <h1>Idle Hacking Market Viewer</h1>
        <div className={`page-updated ${freshness.isStale ? 'page-updated-stale' : ''}`}>
          {freshness.text}
        </div>
        {showLocalStaleWarning ? (
          <div className="page-local-warning">Local bundled data · stale</div>
        ) : null}
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
                        onChange={(event) => onHistoryRangeChange(event.target.value)}
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
                const hasHistory = historyCount > 1 && Array.isArray(row.sparklineHistory) && row.sparklineHistory.length > 1;
                const spread = getSpreadPct(row);

                return (
                  <tr
                    key={row.id}
                    className="market-row-clickable"
                    tabIndex={0}
                    onClick={() => openCommodityDetail(row.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault();
                        openCommodityDetail(row.id);
                      }
                    }}
                  >
                    <td>
                      <button
                        type="button"
                        className="commodity-name commodity-detail-trigger"
                        onClick={(event) => {
                          event.stopPropagation();
                          openCommodityDetail(row.id);
                        }}
                      >
                        {displayCommodityName(row.label)}
                      </button>
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
                      <button
                        type="button"
                        className="sparkline-trigger"
                        onClick={(event) => {
                          event.stopPropagation();
                          openCommodityDetail(row.id);
                        }}
                        aria-label={`Open ${displayCommodityName(row.label)} history`}
                      >
                        {hasHistory ? <Sparkline values={row.sparklineHistory} trend={trend} /> : <span className="muted">history pending</span>}
                      </button>
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

      {selectedCommodity ? (
        <CommodityDetailDrawer
          commodity={selectedCommodity}
          onClose={() => setSelectedCommodityId(null)}
        />
      ) : null}

      {/* Keep Recent Volume Changes off the page for now. User explicitly requested this section stay removed. */}
    </div>
  );
}

function CommodityDetailDrawer({ commodity, onClose }) {
  const [historyState, setHistoryState] = useState({
    loading: true,
    error: '',
    index: null,
    history: null,
  });
  const [selectedRange, setSelectedRange] = useState('1d');

  useEffect(() => {
    let cancelled = false;

    async function loadDetailHistory() {
      setHistoryState({ loading: true, error: '', index: null, history: null });

      try {
        const [historyIndex, commodityHistory] = await Promise.all([
          loadHistoryIndex().catch(() => null),
          loadCommodityHistory(commodity.id),
        ]);

        if (cancelled) return;

        const availableRanges = getCompactHistoryRanges(commodityHistory).filter((range) => range === '1d' || range === '7d');
        setHistoryState({
          loading: false,
          error: '',
          index: historyIndex,
          history: commodityHistory,
        });
        setSelectedRange((current) => {
          if (availableRanges.includes(current)) return current;
          if (availableRanges.includes('1d')) return '1d';
          return availableRanges[0] || '1d';
        });
      } catch (error) {
        if (!cancelled) {
          setHistoryState({
            loading: false,
            error: String(error?.message || error),
            index: null,
            history: null,
          });
        }
      }
    }

    loadDetailHistory();

    return () => {
      cancelled = true;
    };
  }, [commodity.id]);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose();
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const ranges = getCompactHistoryRanges(historyState.history).filter((range) => range === '1d' || range === '7d');
  const rangeOptions = ranges.map((range) => ({
    value: range,
    label: getHistoryRangeLabel(range, historyState.history?.ranges?.[range]),
  }));
  const selectedRangeMeta = historyState.history?.ranges?.[selectedRange] || null;
  const points = Array.isArray(selectedRangeMeta?.points) ? selectedRangeMeta.points : [];
  const spreadCents = Number.isFinite(Number(commodity?.bestAskCents)) && Number.isFinite(Number(commodity?.bestBidCents))
    ? Number(commodity.bestAskCents) - Number(commodity.bestBidCents)
    : null;

  return (
    <div className="detail-backdrop" onPointerDown={onClose}>
      <aside
        className="detail-drawer"
        aria-modal="true"
        role="dialog"
        aria-label={`${displayCommodityName(commodity.label)} market history`}
        onPointerDown={(event) => event.stopPropagation()}
      >
        <div className="detail-head">
          <div>
            <p className="detail-eyebrow">Commodity history</p>
            <h2>{displayCommodityName(commodity.label)}</h2>
          </div>
          <button type="button" className="detail-close" onClick={onClose} aria-label="Close detail view">x</button>
        </div>

        <div className="detail-stat-grid">
          <Metric label="Bid" value={formatMainCredits(commodity.bestBidCents)} subvalue={`${formatCompactQuantity(commodity.bestBidQty)} best qty`} />
          <Metric label="Ask" value={formatMainCredits(commodity.bestAskCents)} subvalue={`${formatCompactQuantity(commodity.bestAskQty)} best qty`} />
          <Metric label="Mid" value={formatMainCredits(commodity.midPriceCents)} />
          <Metric label="Spread" value={formatRoundedCreditSubline(spreadCents)} subvalue={`${formatPlainPercent(getSpreadPct(commodity))}`} />
          <Metric label="Visible volume" value={formatCompactQuantity(commodity.volumeQty)} subvalue={`${formatCompactQuantity(commodity.bidVolumeQty)} bid · ${formatCompactQuantity(commodity.askVolumeQty)} ask`} />
        </div>

        <div className="detail-toolbar">
          <div className="segmented-control" aria-label="History range">
            {rangeOptions.map((option) => (
              <button
                type="button"
                key={option.value}
                className={option.value === selectedRange ? 'segment-active' : ''}
                onClick={() => setSelectedRange(option.value)}
              >
                {option.label}
              </button>
            ))}
            {/* Add 28d once public compact history has enough source coverage. */}
          </div>
        </div>

        {historyState.loading ? <div className="history-chart-empty">Loading compact history…</div> : null}
        {historyState.error ? <div className="history-chart-empty">Could not load compact history: {historyState.error}</div> : null}
        {!historyState.loading && !historyState.error && !points.length ? (
          <div className="history-chart-empty">No compact history points for this range.</div>
        ) : null}
        {!historyState.loading && !historyState.error && points.length ? (
          <HistoryChart points={points} />
        ) : null}
      </aside>
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
