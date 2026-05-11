const HISTORY_RANGES = [
  '1d',
  '7d',
  // Add '28d' here once compact history has enough source coverage.
  'all',
];

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

export async function loadHistoryIndex() {
  return loadJson('/data/history/index.json');
}

export async function loadCommodityHistory(commodityId) {
  const safeCommodityId = String(commodityId || '').trim();
  if (!safeCommodityId) throw new Error('Commodity id is required');

  return loadJson(`/data/history/commodities/${encodeURIComponent(safeCommodityId)}.json`);
}

export function getAvailableHistoryRanges(history) {
  const ranges = history?.ranges;

  if (Array.isArray(ranges)) {
    return ranges.filter((range) => HISTORY_RANGES.includes(range));
  }

  if (ranges && typeof ranges === 'object') {
    return HISTORY_RANGES.filter((range) => ranges[range]?.point_count > 1 || ranges[range]?.points?.length > 1);
  }

  return [];
}

export function getHistoryRangeLabel(range, rangeMeta) {
  if (range !== 'all') return range;

  const earliest = rangeMeta?.earliest || rangeMeta?.points?.[0]?.t || '';
  const date = new Date(earliest);
  if (Number.isNaN(date.getTime())) return 'Since start';

  return `Since ${new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: 'numeric',
  }).format(date)}`;
}
