
# Anti-Gravity Backup Policy

## Purpose
This policy ensures the maximum protection of highly sensitive campaign data, donor records, and research documentation. Given the project's critical role in resilience and aid, data loss or corruption is considered a major failure.

## Backup Strategy: "Dual-Vault"

The system implements two distinct backup layers managed by `scripts/backup_vault.ps1`:

### 1. Internal Archive (Cold/History)
- **Format**: Compressed `.zip`
- **Location**: `backups/internal/`
- **Cadence**: Suggested after every major data harvest (Exporter run).
- **Retention**: Keep all versions for the last 30 days.
- **Integrity**: Every archive is paired with an `.md5` hash file for corruption detection.

### 2. Secure Vault (Warm/Mirror)
- **Format**: Raw file structure
- **Location**: `backups/vault/latest/`
- **Purpose**: Immediate access and manual verification.
- **Mirroring**: This directory should be mirrored to an external encrypted drive or secure cloud storage.

## Data Sensitivity Tiers

| Tier | Dataset | Protection Level |
| :--- | :--- | :--- |
| **Tier 1 (Critical)** | `data/exports/` (WhatsApp), `data/reports/` (Financial) | Full Archive + Daily Sync |
| **Tier 2 (Internal)** | `campaigns_unified.json`, `rationality_audit.csv` | Full Archive |
| **Tier 3 (Public)** | `docs/`, `src/` | Standard Git / Internal Archive |

## Recovery Procedure

To restore from a backup:
1. Identify the desired timestamp in `backups/internal/`.
2. Verify integrity: `Get-FileHash -Path backup_[timestamp].zip -Algorithm MD5`.
3. Extract content to the project root.
4. Run `python -m src.utils.normalize_campaigns` to verify data consistency.

## Automated Enforcement
The backup script should be executed automatically as the final step of any major data integration workflow.
