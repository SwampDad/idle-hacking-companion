import React from 'react';

function downsample(values, maxPoints) {
  if (!Array.isArray(values) || values.length <= maxPoints) return values || [];

  const stride = Math.ceil(values.length / maxPoints);
  const sampled = [];

  for (let index = 0; index < values.length; index += stride) {
    sampled.push(values[index]);
  }

  if (sampled[sampled.length - 1] !== values[values.length - 1]) {
    sampled.push(values[values.length - 1]);
  }

  return sampled;
}

export function Sparkline({ values, trend = 'flat', width = 150, height = 42 }) {
  const points = downsample(values, 96).filter((value) => Number.isFinite(Number(value)));

  if (points.length < 2) {
    return <span className="sparkline sparkline-empty" aria-label="No history available" />;
  }

  const min = Math.min(...points);
  const max = Math.max(...points);
  const range = max - min || 1;
  const pad = 3;
  const innerWidth = width - pad * 2;
  const innerHeight = height - pad * 2;

  const d = points
    .map((value, index) => {
      const x = pad + (index / (points.length - 1)) * innerWidth;
      const y = pad + (1 - (value - min) / range) * innerHeight;
      return `${index === 0 ? 'M' : 'L'}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(' ');

  return (
    <svg
      className={`sparkline sparkline-${trend}`}
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label="Price sparkline"
    >
      <path className="sparkline-grid" d={`M${pad} ${height - pad}H${width - pad}`} />
      <path className="sparkline-line" d={d} />
    </svg>
  );
}
