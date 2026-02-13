---
description: Routine integrity flow - observe integrity throughout iterations
---

// turbo-all

1. Check JSON Integrity (Files Health)
   `python scripts/check_json_integrity.py`

2. Audit Growth List (Rationality Check)
   `python scripts/rationality_audit.py`

3. Validate Onboarding & Outbox (Campaignless Check)
   `python scripts/validate_onboarding.py`

4. Reconcile Financial Ledger (True Debt Calculation)
   `python scripts/reconcile_ledger.py`

5. Scan WhatsApp for New Beneficiaries (Feed Onboarding)
   `python scripts/scan_whatsapp_contacts_v2.py`

6. Generate and Update Trust Health Report
   `python scripts/generate_trust_report.py`

7. Verify Redirection & Deployment Integrity (Learned Experience)
   - Ensure `index.html` and `onboard.html` contain `var githubOnboardingUrl` and NOT `var destination`.
   - Check GitHub Actions for `pages-build-deployment` success: `gh run list --limit 1 --workflow static.yml`
   - Heartbeat check: `Invoke-WebRequest -Uri "https://dours-d.github.io/local-ai-campaign-assistant/index.html#/onboard/972567173987" -UseBasicParsing`
