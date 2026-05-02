# Idle Hacking Market Companion

Public GitHub Pages companion site for Idle Hacking market snapshots.

This repository contains only the public-facing site, sample public market feed data, and the GitHub Pages deployment workflow.

## Contents

- `site/` - Vite/React static site
- `site/public/data/latest.json` - sample public market feed
- `.github/workflows/pages.yml` - GitHub Pages build and deploy workflow

## Run Locally

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

The workflow builds from `site/` and deploys `site/dist`.
