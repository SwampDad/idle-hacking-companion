import React, { useMemo, useState } from 'react';

function formatCredits(value) {
  if (!Number.isFinite(Number(value))) return '—';
  return new Intl.NumberFormat(undefined, {
    notation: Math.abs(Number(value) / 100) >= 1_000_000 ? 'compact' : 'standard',
    maximumFractionDigits: 2,
  }).format(Number(value) / 100);
}

function formatDateTime(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return 'Unavailable';

  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  }).format(date);
}

function buildLinePath(points, getX, getY) {
  return points
    .map((point, index) => `${index === 0 ? 'M' : 'L'}${getX(point).toFixed(2)} ${getY(point).toFixed(2)}`)
    .join(' ');
}

function findNearestPoint(points, x, getX) {
  if (!points.length) return null;

  let best = points[0];
  let bestDistance = Math.abs(getX(best) - x);

  for (const point of points.slice(1)) {
    const distance = Math.abs(getX(point) - x);
    if (distance < bestDistance) {
      best = point;
      bestDistance = distance;
    }
  }

  return best;
}

export function HistoryChart({ points = [] }) {
  const [activePoint, setActivePoint] = useState(null);

  const chart = useMemo(() => {
    const parsed = points
      .map((point) => ({
        ...point,
        stamp: Date.parse(point?.t || ''),
        bid: Number(point?.bestBidCents),
        ask: Number(point?.bestAskCents),
        mid: Number(point?.midPriceCents),
      }))
      .filter((point) => {
        return Number.isFinite(point.stamp)
          && Number.isFinite(point.bid)
          && Number.isFinite(point.ask);
      })
      .sort((left, right) => left.stamp - right.stamp);

    if (parsed.length < 2) {
      return { points: parsed };
    }

    const width = 760;
    const height = 320;
    const pad = { top: 18, right: 24, bottom: 34, left: 54 };
    const minStamp = parsed[0].stamp;
    const maxStamp = parsed[parsed.length - 1].stamp;
    const minPrice = Math.min(...parsed.map((point) => point.bid));
    const maxPrice = Math.max(...parsed.map((point) => point.ask));
    const priceRange = maxPrice - minPrice || 1;
    const timeRange = maxStamp - minStamp || 1;
    const innerWidth = width - pad.left - pad.right;
    const innerHeight = height - pad.top - pad.bottom;

    const getX = (point) => pad.left + ((point.stamp - minStamp) / timeRange) * innerWidth;
    const getY = (point, value) => pad.top + (1 - ((value - minPrice) / priceRange)) * innerHeight;
    const bidPath = buildLinePath(parsed, getX, (point) => getY(point, point.bid));
    const askPath = buildLinePath(parsed, getX, (point) => getY(point, point.ask));
    const bandPath = [
      parsed
        .map((point, index) => `${index === 0 ? 'M' : 'L'}${getX(point).toFixed(2)} ${getY(point, point.ask).toFixed(2)}`)
        .join(' '),
      parsed
        .slice()
        .reverse()
        .map((point) => `L${getX(point).toFixed(2)} ${getY(point, point.bid).toFixed(2)}`)
        .join(' '),
      'Z',
    ].join(' ');

    return {
      points: parsed,
      width,
      height,
      pad,
      minPrice,
      maxPrice,
      getX,
      getY,
      bidPath,
      askPath,
      bandPath,
    };
  }, [points]);

  if (!chart.points || chart.points.length < 2) {
    return <div className="history-chart-empty">Not enough history for this range yet.</div>;
  }

  const active = activePoint || chart.points[chart.points.length - 1];
  const activeX = chart.getX(active);

  const handlePointer = (event) => {
    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * chart.width;
    setActivePoint(findNearestPoint(chart.points, x, chart.getX));
  };

  return (
    <div className="history-chart-wrap">
      <svg
        className="history-chart"
        viewBox={`0 0 ${chart.width} ${chart.height}`}
        role="img"
        aria-label="Bid and ask price history"
        onPointerMove={handlePointer}
        onPointerDown={handlePointer}
        onPointerLeave={() => setActivePoint(null)}
      >
        <path className="history-chart-grid" d={`M${chart.pad.left} ${chart.height - chart.pad.bottom}H${chart.width - chart.pad.right}`} />
        <path className="history-chart-band" d={chart.bandPath} />
        <path className="history-chart-line history-chart-bid" d={chart.bidPath} />
        <path className="history-chart-line history-chart-ask" d={chart.askPath} />
        <line className="history-chart-crosshair" x1={activeX} x2={activeX} y1={chart.pad.top} y2={chart.height - chart.pad.bottom} />
        <circle className="history-chart-point history-chart-point-bid" cx={activeX} cy={chart.getY(active, active.bid)} r="4" />
        <circle className="history-chart-point history-chart-point-ask" cx={activeX} cy={chart.getY(active, active.ask)} r="4" />
        <text className="history-chart-axis" x={chart.pad.left} y={chart.height - 10}>{formatCredits(chart.minPrice)}</text>
        <text className="history-chart-axis" x={chart.width - chart.pad.right} y={chart.height - 10} textAnchor="end">{formatCredits(chart.maxPrice)}</text>
      </svg>

      <div className="history-tooltip">
        <div className="history-tooltip-time">{formatDateTime(active.t)}</div>
        <div><span>Bid</span><strong>{formatCredits(active.bestBidCents)}</strong></div>
        <div><span>Ask</span><strong>{formatCredits(active.bestAskCents)}</strong></div>
        <div><span>Mid</span><strong>{formatCredits(active.midPriceCents)}</strong></div>
        <div><span>Spread</span><strong>{formatCredits(active.spreadCents)}</strong></div>
      </div>
    </div>
  );
}
