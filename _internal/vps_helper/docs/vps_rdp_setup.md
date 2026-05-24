> **Cross-Reference:** VPS chat incident documentation is in `idlehacking_kb/docs/infrastructure/2026-05-22_vps_chat_body_too_large_incident.md`.

Project Memory — VPS, Idle Hacking Collector, Market Publishing, Chat KB

Purpose

A Hetzner VPS provides an always-on Linux environment for Idle Hacking browser collection, public market data capture, private chat export, storage, and automation.

Primary roles:

1. Keep Idle Hacking running in cloud Chrome.
2. Collect public stackables/commodity market data.
3. Export private chat archives for the KB repo.
4. Preserve market snapshot history.
5. Serve data locally to downstream workflows.
6. Support future cron/systemd automation.
7. Reduce dependence on local Mac uptime.

⸻

VPS Identity

Provider: Hetzner Cloud
Plan: CX23
Server name: ubuntu-4gb-nbg1-1
Server ID: 128814247
Billing/project label: K0510976726
Location: NBG1, Nuremberg, Germany
Network zone: eu-central
Monthly cost: €4.99
OS: Ubuntu 24.04 LTS / observed 24.04.3 LTS
Public IPv4: 46.224.146.164
IPv6 allocation: 2a01:4f8:1c19:2a57::/64
Observed IPv6: 2a01:4f8:1c19:2a57::1

Specs:

CPU: 2 vCPU
RAM: 4 GB
Disk: 40 GB local disk
Initial / usage: ~3.0% of 37.23 GB

Primary access:

Admin SSH: ssh scraper@46.224.146.164
Fallback/root SSH: ssh root@46.224.146.164
RDP host: 46.224.146.164
RDP port: 3389/tcp
Gateway: none / blank

⸻

Users

Primary admin/automation user:

scraper
home: /home/scraper
groups: users, sudo, chrome-remote-desktop

Remote desktop user:

new_cloud
password source: local cloud_config.txt only

Security rule:

Do not store passwords, API keys, cookies, Chrome Remote Desktop PINs, Reddit secrets, SSH private keys, game credentials, or session tokens in project docs.

⸻

Firewall and Network

Configured firewall:

ufw allow OpenSSH
ufw allow 3389/tcp
ufw enable
ufw status

Open ports:

22/tcp    SSH
3389/tcp  XRDP

No RDP gateway is required because the VPS is directly reachable by public IPv4.

Latency note:

Manual remote desktop from the US to Germany is slow. Automation running directly on the VPS should not have the same input-lag problem.

⸻

Installed System Components

Core tools:

git
curl
wget
nano
unzip
sqlite3
htop
tmux
cron
python3
python3-venv
python3-pip
xfce4
xfce4-goodies
dbus-x11
google-chrome-stable
chrome-remote-desktop
xrdp

Desktop environment:

XFCE

Chrome:

Google Chrome stable
purpose: dedicated Idle Hacking collector/browser
policy: do not sign into personal Chrome profile unless necessary

⸻

Remote Desktop

Working path: XRDP

XRDP reaches the login screen for `new_cloud`, and the session is now forced to XFCE via `/home/new_cloud/.xsession`.
Client retry is still needed to confirm the desktop opens cleanly.

Key config:

/home/new_cloud/.xsession

Contents:

startxfce4

Useful commands:

systemctl status xrdp
systemctl restart xrdp
systemctl enable xrdp

Mac client:

Microsoft Remote Desktop / Windows App
PC name: 46.224.146.164
Username: new_cloud or scraper
Gateway: blank

Chrome Remote Desktop

Chrome Remote Desktop was installed but abandoned for now.

Status:

Installed package: chrome-remote-desktop
Registration failed with: Trace/breakpoint trap (core dumped)
No active CRD host process
No ~/.config/chrome-remote-desktop registration found

Security note:

A CRD PIN was exposed during setup. Do not reuse it.

⸻

2026-05-11 — XRDP Login Fix for new_cloud

Problem:

RDP reached the VPS.
XRDP connected to sesman.
Login failed for user new_cloud.

Observed log pattern:

connecting to sesman on 127.0.0.1:3350
sesman connect ok
sending login info to session manager, please wait...
login failed for user new_cloud

Root cause area:

Linux/XRDP authentication or home directory ownership
not GitHub, site, code, SSH, or network

Actions taken:

Confirmed SSH works through scraper.
Confirmed xrdp and xrdp-sesman active.
Reset Linux password for new_cloud using local cloud_config.txt.
Fixed /home/new_cloud ownership.
Confirmed account active, unlocked, not expired.
Restarted xrdp and xrdp-sesman.

Current status:

XRDP authentication for new_cloud is fixed.
The XFCE session config has been applied for new_cloud via /home/new_cloud/.xsession containing startxfce4.
Next step is to retry RDP and verify the desktop opens cleanly instead of the GNOME crash screen.

Current RDP settings:

Host: 46.224.146.164
Username: new_cloud
Gateway: none
Password: stored locally in cloud_config.txt

⸻

Directory Layout

Primary server layout:

/home/scraper/
  data/
    market/
      latest.json
      snapshots/
        recent/
      receipts/
    private/
      chat/
        latest.json
        archive/
        manifests/
          chat_manifest.jsonl
  logs/
    browser_game.log
    reddit_daily.log
    hackbot_remote_log.md
    vps_cloud_doc.md
  scrapers/
    browser_game/
    reddit/
  vps_helper/
    collector_helper.py

Local project paths:

Market companion:
  /Users/buddy/projects/ih_market_companion
Idle Hacking KB:
  /Users/buddy/projects/idlehacking_kb
Idle Hacking helper repo:
  /Users/buddy/projects/idle-hacker

⸻

Idle Hacking Account Policy

Account/persona:

Name: HackBot
Persona: bot-like, dry, self-aware, robotic
Policy: gather only, do not hack
Gathering resource: code
Earned unit: snippets

Public line:

I do not hack. I harvest snippets. This is probably inefficient, but it is policy.

Current use:

Keep account online.
Gather code/snippets.
Collect market data.
Export private chat for KB.

⸻

Collector Overview

The browser userscript collects:

chat capture
full public stackables/commodity market capture
WebSocket market volume-change capture
health heartbeat
small health badge

It intentionally does not include:

large dashboard
equipment market
credits
holdings
personal orders
tokens
cookies
secrets
private player state in public feed

Important browser console checks:

IHCollector.getHealth()
IHCollector.exportPublicMarketFeed(false)
IHCollector.getVolumeChanges()
IHCollector.captureMarketNow('manual-check', { download: false })

Market scope:

Stackables/commodities only
16 commodities
16 books

Volume method:

Primary source: WebSocket MARKET_STACKABLES_DELTA
Uses: payload.price_impacts.bids / asks
Tracks:
  filled_qty
  canceled_qty
  added_qty
  price_cents

Public wording rule:

Use:

volume added
volume removed
likely volume fill
volume changed

Avoid:

confirmed sale
confirmed trade
confirmed transaction

⸻

VPS Collector Helper

Helper path:

/home/scraper/vps_helper/collector_helper.py

Service:

ih-collector-helper.service
type: systemd --user

Process observed:

/usr/bin/python3 /home/scraper/vps_helper/collector_helper.py

Endpoint:

http://127.0.0.1:8765

Routes:

GET  /health
POST /health
POST /market-feed
POST /chat-export

Purpose:

Receive JSON from cloud browser Tampermonkey collector.
Write collector health.
Write public market feed files.
Write private chat export files.
Keep public market and private chat lanes separated.
Survive SSH disconnects.
Restart if helper exits.

CORS requirement:

Access-Control-Allow-Origin: https://www.idlehacking.com
Access-Control-Allow-Methods: GET, POST, OPTIONS
Access-Control-Allow-Headers: Content-Type

Useful commands:

ssh scraper@46.224.146.164 \
  'systemctl --user status ih-collector-helper.service --no-pager'
ssh scraper@46.224.146.164 \
  'systemctl --user restart ih-collector-helper.service'
ssh scraper@46.224.146.164 \
  'curl -s http://127.0.0.1:8765/health | python3 -m json.tool | head -160'
ssh scraper@46.224.146.164 \
  'python3 -m py_compile /home/scraper/vps_helper/collector_helper.py'

Deploy helper update:

scp _internal/vps_helper/collector_helper.py \
  scraper@46.224.146.164:/home/scraper/vps_helper/collector_helper.py
ssh scraper@46.224.146.164 \
  'python3 -m py_compile /home/scraper/vps_helper/collector_helper.py'
ssh scraper@46.224.146.164 \
  'systemctl --user restart ih-collector-helper.service'

⸻

Public Market Data Lane

VPS paths:

/home/scraper/data/market/latest.json
/home/scraper/data/market/snapshots/recent/*.json
/home/scraper/data/market/receipts/*.json

Behavior:

latest.json is overwritten with latest full public market feed.
snapshots/recent/*.json preserves full archived public market snapshots.
receipts/*.json contains metadata only.
receipt file points to the matching snapshot file.
receipt sha256 hashes the full market payload.

Important change made 2026-05-03:

Old behavior preserved only latest.json plus metadata receipts.
New behavior preserves full historical market snapshots.
Old metadata-only receipts remain unrecoverable as full snapshots.

Example receipt shape:

{
  "created_at": "2026-05-03T053142Z",
  "file": "snapshots/recent/2026-05-03T053142Z.json",
  "message_count": 0,
  "sha256": "4140ca09428f6a1d935229fa634653ef5e6aaad115e377c7662cd70fd1f91c93"
}

Health status observed:

market.status: ok
market.pricing_status: ok
market.commodities: 16
market.books: 16
market.raw_source_state: live
market.raw_source_health: ok
volume.status: ok

Snapshot cadence:

roughly every 15 minutes

Useful commands:

ssh scraper@46.224.146.164 \
  "python3 -c \"import json; print(json.load(open('/home/scraper/data/market/latest.json')).get('generated_at'))\""
ssh scraper@46.224.146.164 \
  "ls -lt /home/scraper/data/market/snapshots/recent | head -20"

⸻

Private Chat Data Lane

VPS paths:

/home/scraper/data/private/chat/latest.json
/home/scraper/data/private/chat/archive/*.json
/home/scraper/data/private/chat/manifests/chat_manifest.jsonl

Purpose:

Private chat archive source for Idle Hacking KB repo.
Not for public market site.
Not for GitHub Pages.

Boundary:

Never copy private chat into:
  /Users/buddy/projects/ih_market_companion/site/public/data
Never publish private chat to GitHub Pages.

Health status observed 2026-05-04:

chat.status: ok
chat.writes_failed: 0
chat.last_message_at: 2026-05-04T13:47:26.760Z
archive advancing every ~15 minutes

Reliability audit:

continuity_gaps = 0
messageId overlap used, not collector key
VPS private chat export considered reliable normal KB source
browser-downloaded chat remains fallback/supplement

Audit comparison:

Channel	Browser IDs	VPS IDs	Shared	Coverage
help	465	515	465	100%
main	5694	7067	5694	100%
trade	145	157	145	100%

Useful commands:

ssh scraper@46.224.146.164 \
  "ls -lt /home/scraper/data/private/chat/archive | head -20"
cd /Users/buddy/projects/idlehacking_kb
mkdir -p data/imports/chat/vps
rsync -avz --ignore-existing \
  scraper@46.224.146.164:/home/scraper/data/private/chat/archive/ \
  data/imports/chat/vps/

⸻

Public Market Publishing

Current automated flow:

VPS Chrome collector
  -> /home/scraper/vps_helper/collector_helper.py
  -> /home/scraper/data/market/
  -> GitHub Actions rsync pull
  -> public site data
  -> GitHub Pages deploy

GitHub Actions reads:

scraper@46.224.146.164:/home/scraper/data/market/

Schedule:

7,37 * * * *

Reason:

Avoid top-of-hour and half-hour GitHub Actions congestion.

Manual dispatch remains available if the site falls behind.

Security boundary:

GitHub Actions should pull only public market data.
Private chat must remain outside public site workflow.

Security incident:

An earlier SSH private key was exposed and is compromised.
A replacement key was generated for GitHub Actions.
Do not reuse exposed key.
Do not document private key material.

⸻

Local Market Companion Workflow

Repo:

/Users/buddy/projects/ih_market_companion

Manual local update command:

cd /Users/buddy/projects/ih_market_companion
_internal/scripts/update_market_data_local.sh

Wrapper behavior:

rsync pulls /home/scraper/data/market/ from VPS
stages cloud files under _internal/data/market/cloud/
imports valid public market feeds
skips metadata-only receipts
writes public site data under site/public/data/
builds the site
prints snapshot freshness/debug status

Important debug fields:

cloud latest full feed
local public latest snapshot
index recent count
cloud receipt count
new-style snapshot receipt count
old metadata-only receipt count
cloud full snapshot file count
missing receipt-backed full snapshots
untracked local public snapshots
newest snapshot age

Good run example:

cloud pull success: True
valid: 44
rejected: 0
available ranges: 1d, all
missing receipt-backed full snapshots: 0
newest age: ~2.5 minutes

⸻

Pipeline Health Checker

Local script:

/Users/buddy/projects/ih_market_companion/_internal/tools/pipeline_health.py

Purpose:

Check VPS -> GitHub Actions -> GitHub Pages market pipeline.

Checks:

live GitHub Pages JSON timestamp
local repo JSON timestamp
VPS latest market JSON timestamp
VPS helper health
VPS market status
VPS volume status
GitHub update workflow recency
GitHub Pages workflow recency

Run:

/opt/homebrew/bin/python3 \
  /Users/buddy/projects/ih_market_companion/_internal/tools/pipeline_health.py

Healthy example:

Live timestamp matched VPS timestamp.
VPS helper status ok.
market status ok.
pricing ok.
books 16/16.
volume ok.
chat ok.

⸻

KB Chat Ingestion

KB repo:

/Users/buddy/projects/idlehacking_kb

Current full daily runner:

/Users/buddy/projects/idlehacking_kb/scripts/daily_runner.py

Collector ingest:

/Users/buddy/projects/idlehacking_kb/scripts/chat/ingest_collector_chat.py

VPS audit:

/Users/buddy/projects/idlehacking_kb/scripts/chat/audit_vps_chat_export.py

Normal daily ingestion:

python3 /Users/buddy/projects/idlehacking_kb/scripts/daily_runner.py \
  --downloads-dir /Users/buddy/Downloads \
  --helper-repo-root /Users/buddy/projects/idle-hacker \
  --kb-repo-root /Users/buddy/projects/idlehacking_kb

With browser-chat fallback:

python3 /Users/buddy/projects/idlehacking_kb/scripts/daily_runner.py \
  --downloads-dir /Users/buddy/Downloads \
  --helper-repo-root /Users/buddy/projects/idle-hacker \
  --kb-repo-root /Users/buddy/projects/idlehacking_kb \
  --include-download-chat

⸻

2026-05-11 — Daily Runner Performance Concern

Observation:

The KB daily runner is too slow for lightweight freshness checks.

Likely expensive work combined in one run:

VPS chat rsync
collector chat ingest
VPS chat audit
Discord ingest
site snapshot processing
report generation
all-time dev/trgKai markdown export rebuilds

Current rsync behavior:

source:
  scraper@46.224.146.164:/home/scraper/data/private/chat/archive/
destination:
  /Users/buddy/projects/idlehacking_kb/data/imports/chat/vps/
option:
  --ignore-existing

Desired fast refresh path:

1. Sync latest VPS chat collector files.
2. Ingest only new/unprocessed collector bundles.
3. Skip Discord ingest.
4. Skip full VPS audit.
5. Skip site snapshot.
6. Skip all-time dev/trgKai export rebuilds.
7. Print newest chat timestamps by channel.
8. Optionally rebuild chat UI data only if needed.

Candidate implementation names:

daily_runner.py --fast-refresh
scripts/chat/refresh_chat_fast.py

Open performance questions:

Is it scanning all VPS bundle files every run?
Is it rereading full canonical chat archives?
Is it rebuilding all-time dev/trgKai exports?
Is it recursively scanning Downloads?
Is Discord ingest processing every matching export?
Is full VPS audit the bottleneck?
Is site snapshot workflow slow?

Codex constraints for this work:

Do not run scripts/daily_runner.py.
Do not run full ingest.
Do not run rsync.
Do not run LLM/Ollama/model commands.
Do not edit live filters, aliases, registries, KB claims, or site files.
Do not stage or commit.
Use only cheap metadata commands:
  find
  ls
  wc
  du
  stat
  head
  tail
  grep/ripgrep

Reason:

Use Codex for static inspection, patch planning, and lightweight metadata checks only unless a full ingest is explicitly intended.

⸻

Reddit Scraper

Status:

Deferred.
Idle Hacking collector has priority.

Original intended layout:

/home/scraper/scrapers/reddit/reddit_daily.py
/home/scraper/scrapers/reddit/.venv
/home/scraper/logs/reddit_daily.log
/home/scraper/data/reddit.sqlite

Suggested setup:

cd /home/scraper/scrapers/reddit
python3 -m venv .venv
source .venv/bin/activate
pip install requests beautifulsoup4 feedparser praw

Suggested cron:

15 3 * * * cd /home/scraper/scrapers/reddit && /home/scraper/scrapers/reddit/.venv/bin/python reddit_daily.py >> /home/scraper/logs/reddit_daily.log 2>&1

⸻

File Transfer Workflow

Preferred workflow:

Edit locally on Mac.
Transfer with scp or rsync.
Run/test over SSH.
Use RDP only for browser/game visual tasks.

Examples:

scp ~/Desktop/reddit_daily.py \
  scraper@46.224.146.164:/home/scraper/scrapers/reddit/
scp ~/Desktop/hackbot.user.js \
  scraper@46.224.146.164:/home/scraper/scrapers/browser_game/
scp -r ~/Desktop/my_scraper_folder \
  scraper@46.224.146.164:/home/scraper/scrapers/

SSH:

ssh scraper@46.224.146.164

View files:

ls -la ~/scrapers/
cat /home/scraper/scrapers/browser_game/hackbot.user.js
nano /home/scraper/scrapers/browser_game/hackbot.user.js

Longer-term option:

cd ~/scrapers
git clone https://github.com/YOURNAME/YOURREPO.git
cd ~/scrapers/YOURREPO
git pull

⸻

Storage

Current approach:

Local VPS disk first.
No Hetzner Object Storage currently used.

Market data:

JSON latest file
JSON full snapshots
metadata receipts

Private chat:

JSON latest file
JSON archive files
manifest JSONL

Possible future storage:

SQLite for structured chat/Reddit data
JSONL append-only logs
compressed daily backups
optional copy to local Mac/cloud storage

Example chat SQLite table:

CREATE TABLE chat (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts DATETIME DEFAULT CURRENT_TIMESTAMP,
  username TEXT,
  message TEXT,
  raw TEXT
);

⸻

Logging

Important logs/docs:

/home/scraper/logs/hackbot_remote_log.md
/home/scraper/logs/vps_cloud_doc.md
/home/scraper/logs/browser_game.log
/home/scraper/logs/reddit_daily.log

Append pattern:

cat >> ~/logs/vps_cloud_doc.md <<'EOF'
## YYYY-MM-DD — Entry title
Notes here.
EOF

Policy:

Append corrections rather than rewriting history.
Exception: remove or rotate exposed secrets immediately.

⸻

Security Notes

Never store:

root password
scraper password
new_cloud password
game password
Google password
Chrome Remote Desktop PIN
API keys
Reddit API secret
cookies
session tokens
SSH private keys

Known security incidents:

Chrome Remote Desktop PIN was exposed. Do not reuse.
An earlier SSH private key was exposed. Treat as compromised.

Recommended hardening:

Use SSH key login.
Disable root password login after key login works.
Keep firewall limited to SSH/RDP.
Do not expose databases publicly.
Do not run collectors as root.
Back up data.
Add alerting for stale market/chat files.

Possible SSH hardening after key login is tested:

PermitRootLogin prohibit-password
PasswordAuthentication no

Restart:

sudo systemctl restart ssh

⸻

Current Trust Level

As of latest notes:

VPS running.
Ubuntu updated.
scraper user works.
new_cloud RDP login fixed.
XRDP works.
Chrome collector running.
Helper service healthy.
Public market export healthy.
Market snapshots advancing.
Private chat export healthy.
Private chat archives advancing.
GitHub Actions public market publishing automated.
KB daily runner works but is too heavy for frequent freshness checks.

Remaining risks:

Chrome may hang.
Tampermonkey collector may stop if page crashes.
GitHub scheduled workflows can be delayed.
Chat UI/site view can become stale.
No alerting/watchdog yet.
Full KB daily runner is too slow for lightweight checks.

Recommended next work:

Add fast KB chat refresh path.
Add stale-file alerts for market latest.json and private chat latest.json.
Add alert for delayed GitHub Actions market workflow.
Add Chrome/collector watchdog.
Consider VPS-side workflow_dispatch trigger after fresh market snapshots.
Set up SSH-key-only login.
Add backups.



## 2026-05-11 — RDP status correction: authentication fixed, desktop session still broken

Correction to earlier notes:

RDP is **not fully working yet**.

Current accurate status:

- Network access to VPS works.
- SSH access as `scraper` works.
- XRDP service is reachable.
- `xrdp-sesman` is reachable.
- RDP login for `new_cloud` now gets past the earlier password/authentication failure.
- The password issue was fixed by resetting the password without shell expansion.
- However, after login, the desktop session crashes and shows the GNOME error screen:

```text
Oh no! Something has gone wrong.
A problem has occurred and the system can't recover.
Please log out and try again.



## 2026-05-11 — Added 4 GB swapfile after Chrome OOM

Hetzner console showed the Linux OOM killer had killed a Chrome process. The VPS had 4 GB RAM and no swap, so Chrome memory spikes could cause process kills.

A 4 GB swapfile was added and enabled.

Results:

- Disk before: `/dev/sda1` 12G used, 25G free
- Disk after: `/dev/sda1` 16G used, 21G free
- Swap active: 4.0 GiB
- RAM available after setup: about 1.7 GiB
- Chrome still running under `scraper`
- Collector helper health still `ok`
- Latest market timestamp checked: `2026-05-11 06:50:15 UTC`

Commands used conceptually:

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-swappiness.conf
sudo sysctl vm.swappiness=10

Purpose:

Swap uses disk as overflow memory. It does not add RAM or cost extra money, but it gives Chrome and the desktop a buffer during memory spikes.

Remaining issues:

* RDP as scraper still needs session/display repair.
* Private chat latest/archive files appear stale since May 6 even though collector health reports chat activity.


