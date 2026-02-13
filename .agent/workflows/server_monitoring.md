---
description: Waking server & watchdog - monitoring + HTTP Health Check
---

// turbo-all

1. Re-integrate any relay intelligence captured while the server was offline
   `.venv/Scripts/python.exe scripts/reintegrate_relay_intelligence.py`

2. Start the robust monitoring service (handles Server, Watchdog, Tunnel, and Public URL Verification)
   `pwsh -File scripts/monitor_services.ps1`

### Troubleshooting & Learned Experiences

- **Cache Delays**: GitHub Pages updates can lag by 5-10 minutes. The watchdog forces cache-busting by updating timestamps in `index.html` every 60s.
- **Direct Access**: If the GitHub link (`dours-d.github.io`) fails, use the direct Cloudflare tunnel URL found in `data/monitoring.log` (look for "Public URL Verification SUCCESS").
- **Service Crashes**: If the site is down, the watchdog script may have crashed. Restart it using the command above.
- **Data Safety**: Sensitive GGF data is stored in `data/GGF/` and is strictly **local-only**. Do not force-push `data/` to remote.
- **Deployment**: The watchdog automatically commits and pushes URL updates necessary for redirection. Keep it running to maintain site availability.
