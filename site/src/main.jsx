import React, { useEffect, useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const ROUTES = {
  home: 'home',
  market: 'market',
};

function getRoute() {
  const raw = String(window.location.hash || '').replace(/^#\/?/, '').toLowerCase();
  return raw && ROUTES[raw] ? raw : ROUTES.home;
}

function getDataUrl() {
  return new URL('data/latest.json', window.location.href).toString();
}

function formatDateTime(value) {
  if (!value) return '—';
  const d = new Date(value);
  return Number.isNaN(d.getTime())
    ? value
    : new Intl.DateTimeFormat(undefined, {
        dateStyle: 'medium',
        timeStyle: 'short',
      }).format(d);
}

function formatNumber(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '—';
  return new Intl.NumberFormat(undefined).format(Number(value));
}

function formatPriceCents(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat(undefined, {
    minimumFractionDigits: 0,
    maximumFractionDigits: Number(value) >= 100000 ? 0 : 2,
  }).format(Number(value) / 100);
}

function formatSpread(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return `${Number(value).toFixed(2)}%`;
}

function getMidPriceCents(row) {
  const bid = Number(row?.bestBidCents);
  const ask = Number(row?.bestAskCents);
  if (Number.isFinite(bid) && Number.isFinite(ask)) return (bid + ask) / 2;
  if (Number.isFinite(bid)) return bid;
  if (Number.isFinite(ask)) return ask;
  return null;
}

function getInterpretation(event) {
  const kind = String(event?.kind || '').toLowerCase();
  if (kind === 'fill') return 'likely fill';
  if (kind === 'add') return 'order added';
  if (kind === 'cancel') return 'order removed/canceled';
  if (kind === 'change') return 'book changed';
  if (kind === 'appeared' || kind === 'disappeared') return 'bootstrap / visibility only';
  return 'book activity';
}

function badgeClass(kind) {
  const value = String(kind || '').toLowerCase();
  if (value === 'fill') return 'badge-fill';
  if (value === 'add') return 'badge-add';
  if (value === 'cancel') return 'badge-cancel';
  if (value === 'change') return 'badge-change';
  return 'badge-neutral';
}

function App() {
  const [route, setRoute] = useState(getRoute());
  const [feed, setFeed] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const onHashChange = () => setRoute(getRoute());
    window.addEventListener('hashchange', onHashChange);
    return () => window.removeEventListener('hashchange', onHashChange);
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function load() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetch(getDataUrl(), { cache: 'no-store' });
        if (!res.ok) throw new Error(`Failed to load feed (${res.status})`);
        const json = await res.json();
        if (!cancelled) setFeed(json);
      } catch (err) {
        if (!cancelled) setError(String(err?.message || err));
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const marketRows = feed?.snapshots?.market?.commodities || [];
  const marketEvents = useMemo(() => {
    const rows = feed?.snapshots?.market_events?.events || [];
    return [...rows].reverse();
  }, [feed]);

  const summary = {
    generatedAt: feed?.generated_at || null,
    commodityCount: marketRows.length,
    eventCount: feed?.snapshots?.market_events?.events?.length || 0,
  };

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <div className="brand-kicker">Idle Hacking</div>
          <h1>Market Companion</h1>
        </div>
        <nav className="nav">
          <a className={route === ROUTES.home ? 'active' : ''} href="#home">Home</a>
          <a className={route === ROUTES.market ? 'active' : ''} href="#market">Market</a>
        </nav>
      </header>

      <main className="page">
        <section className="hero panel">
          <div>
            <p className="eyebrow">Rolling public feed</p>
            <h2>Public market snapshots and recent visible activity.</h2>
            <p className="lede">
              Read-only companion site for Idle Hacking. The data refreshes from the live public feed while the publisher is running.
            </p>
          </div>
          <div className="hero-meta">
            <Metric label="Generated" value={formatDateTime(summary.generatedAt)} />
            <Metric label="Commodities" value={formatNumber(summary.commodityCount)} />
            <Metric label="Market events" value={formatNumber(summary.eventCount)} />
          </div>
        </section>

        {loading ? <InfoBanner tone="warn" text="Loading public feed..." /> : null}
        {error ? <InfoBanner tone="bad" text={error} /> : null}

        {route === ROUTES.home ? <HomeView summary={summary} /> : null}
        {route === ROUTES.market ? <MarketView marketRows={marketRows} marketEvents={marketEvents} /> : null}
      </main>
    </div>
  );
}

function HomeView({ summary }) {
  return (
    <div className="stack">
      <section className="grid-2">
        <a className="entry-card panel" href="#market">
          <p className="eyebrow">Market</p>
          <h3>View commodities and recent market activity.</h3>
        </a>
      </section>

      <section className="panel">
        <h3>Snapshot Summary</h3>
        <div className="summary-grid">
          <Metric label="Generated at" value={formatDateTime(summary.generatedAt)} />
          <Metric label="Tracked commodities" value={formatNumber(summary.commodityCount)} />
          <Metric label="Market events" value={formatNumber(summary.eventCount)} />
        </div>
      </section>
    </div>
  );
}

function MarketView({ marketRows, marketEvents }) {
  return (
    <div className="stack">
      <section className="panel">
        <div className="section-head">
          <h3>Commodities</h3>
          <p>Visible book depth snapshot from the public feed.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Commodity</th>
                <th className="num">Best Bid</th>
                <th className="num">Best Ask</th>
                <th className="num">Mid Price</th>
                <th className="num">Spread %</th>
                <th className="num">Volume</th>
              </tr>
            </thead>
            <tbody>
              {marketRows.map(row => (
                <tr key={row.id}>
                  <td>
                    <div className="cell-title">{row.label}</div>
                    <div className="cell-sub">{row.id}</div>
                  </td>
                  <td className="num">{formatPriceCents(row.bestBidCents)}</td>
                  <td className="num">{formatPriceCents(row.bestAskCents)}</td>
                  <td className="num">{formatPriceCents(getMidPriceCents(row))}</td>
                  <td className="num">{formatSpread(row.spreadPct)}</td>
                  <td className="num">{formatNumber(row.volumeQty)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="panel">
        <div className="section-head">
          <h3>Recent Market Activity</h3>
          <p>Newest visible first. Fills are labeled as likely fills, not confirmed sales.</p>
        </div>
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Time</th>
                <th>Commodity</th>
                <th>Side</th>
                <th>Kind</th>
                <th className="num">Qty</th>
                <th className="num">Price</th>
                <th>Interpretation</th>
              </tr>
            </thead>
            <tbody>
              {marketEvents.map((event, index) => (
                <tr key={`${event.at}-${event.commodity_id}-${index}`}>
                  <td>{formatDateTime(event.at)}</td>
                  <td>
                    <div className="cell-title">{event.commodity_label || event.commodity_id}</div>
                    <div className="cell-sub">{event.commodity_id}</div>
                  </td>
                  <td><span className={`pill ${badgeClass(event.side)}`}>{String(event.side || 'book').toUpperCase()}</span></td>
                  <td><span className={`pill ${badgeClass(event.kind)}`}>{String(event.kind || 'change').toUpperCase()}</span></td>
                  <td className="num">{formatNumber(event.qty ?? event.filledQty ?? event.addedQty ?? event.canceledQty)}</td>
                  <td className="num">{formatPriceCents(event.priceCents ?? Math.round(Number(event.price || 0) * 100))}</td>
                  <td>{getInterpretation(event)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
    </div>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

function InfoBanner({ tone, text }) {
  return <div className={`banner ${tone}`}>{text}</div>;
}

createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
