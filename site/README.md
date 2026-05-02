# Idle Hacking Market Companion

Minimal public GitHub Pages companion site for Idle Hacking market snapshots.

## Run

```bash
cd site
npm install
npm run dev
```

## Build

```bash
cd site
npm run build
```

## Preview

```bash
cd site
npm run preview
```

## Notes

- The app loads public data from `public/data/latest.json`.
- `vite.config.js` currently uses `base: './'` so the build is suitable for GitHub Pages subpaths.
- If you later deploy to a different base path, adjust `base` in `site/vite.config.js`.
