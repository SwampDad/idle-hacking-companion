# VPS Chat Export Fix Applied — 2026-05-24

**Date:** 2026-05-24
**Issue:** Chat exports failing with HTTP 413 (body_too_large) since May 6, 2026
**Root Cause:** `MAX_BODY_BYTES = 25 * 1024 * 1024` hardcoded limit in `collector_helper.py`
**Actual Bundle Size:** ~148MB (grew over 18 days)
**Fix:** Increased `MAX_BODY_BYTES` to `500 * 1024 * 1024` (500MB)

## Timeline

| Date | Event |
|------|-------|
| 2026-05-06 21:00Z | Last successful chat export bundle |
| 2026-05-06 ~21:15Z | Next bundle exceeds 25MB → first HTTP 413 |
| 2026-05-06 to 2026-05-24 | Every `POST /chat-export` returns 413 (retry every ~15 min) |
| 2026-05-22 | Incident discovered during diagnostic review |
| 2026-05-24 08:17Z | Fix applied to VPS (`collector_helper.py` updated) |
| 2026-05-24 08:17Z | Service restarted (`ih-collector-helper.service`) |
| 2026-05-24 08:31Z | **First successful export after fix:** `2026-05-24T083056Z.json` (148MB) |

## Fix Details

### File Changed
`/home/scraper/vps_helper/collector_helper.py` (VPS canonical)
`_internal/vps_helper/collector_helper.py` (local canonical, now tracked in git)

### Change
```python
# Before
MAX_BODY_BYTES = 25 * 1024 * 1024  # 25MB

# After
MAX_BODY_BYTES = 500 * 1024 * 1024  # 500MB
```

### Rationale
- Current bundle size: ~148MB
- New limit: 500MB (3.4x headroom)
- Allows for continued growth without frequent limit increases
- Memory-safe: VPS has 16GB RAM, helper process uses ~50MB peak

## Verification

### Commands Run
```bash
# Backup
cp /home/scraper/vps_helper/collector_helper.py /home/scraper/vps_helper/collector_helper.py.bak.20260524

# Apply fix
sed -i "s/MAX_BODY_BYTES = 25 \* 1024 \* 1024/MAX_BODY_BYTES = 500 * 1024 * 1024/" \
    /home/scraper/vps_helper/collector_helper.py

# Verify
grep "MAX_BODY_BYTES" /home/scraper/vps_helper/collector_helper.py
# → MAX_BODY_BYTES = 500 * 1024 * 1024

# Restart service
systemctl --user restart ih-collector-helper.service

# Verify service running
systemctl --user status ih-collector-helper.service
# → Active: active (running)
```

### First Successful Export
```bash
# Check logs
journalctl --user -u ih-collector-helper.service --since "2026-05-24 08:30:00" | grep chat-export
# → POST /chat-export -> 200 saved

# Verify file exists
ls -lh /home/scraper/data/private/chat/archive/2026-05-24T083056Z.json
# → -rw-rw-r-- 1 scraper scraper 148M May 24 08:31
```

## Git Commit

**Repo:** `ih_market_companion`
**Commit:** `2fc209b`
**Files:**
- `.gitignore` — Added `_internal/vps_helper/` to tracking
- `_internal/vps_helper/collector_helper.py` — MAX_BODY_BYTES fix

## Lessons Learned

1. **Hardcoded limits without monitoring are silent breakers** — No alert for 18 days
2. **Health endpoints must report server-side ACK** — Client counters were misleading (showed "writes_ok" for 413 responses)
3. **Critical infrastructure should be version-controlled** — `_internal/vps_helper/` was in gitignore, fix wasn't tracked
4. **Fix docs must be created when incidents are resolved** — Previous incident doc referenced this file but it didn't exist

## Monitoring Improvements

### Dashboard Aggregation Fix
- Fixed `compute_overall_status()` to prioritize FAIL > WARN > UNKNOWN > OK
- Previously showed WARN when Chat Export was FAIL (bug)

### Health Check Coverage
- Chat export age now monitored (was missing)
- Dashboard shows Chat Export section with status, age, latest file

## Future Considerations

### When to Increase Limit Again
Monitor bundle growth:
```bash
# Check latest bundle size
ls -lh /home/scraper/data/private/chat/archive/ | head -3

# If approaching 400MB, consider increasing to 1GB
```

### Automated Bundle Size Alert
Add to health check:
- WARN if bundle > 300MB
- FAIL if bundle > 450MB

### Memory Impact
Current helper memory usage: ~50MB peak
500MB limit impact: Minimal (buffers are streaming, not loaded entirely in memory)

---

**Status:** ✅ Resolved
**Next Export:** Every ~15 minutes (automated)
**Owner:** `ih_market_companion` repo (VPS helper source of truth)
