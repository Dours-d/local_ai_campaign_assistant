# Campaign Assistant Database Schema

## Overview

This database manages fundraising campaigns for Gaza relief, connecting:
- **Campaigns** (on Chuffed & Whydonate platforms)
- **Contacts** (WhatsApp connections to beneficiaries)
- **Communications** (Chat exports and history)

---

## Entity Classes

### 1. Campaign
The core entity representing a fundraising campaign.

**Sources:**
- `campaigns_unified.json` - Normalized view of all campaigns
- `chuffed_campaigns.json` - Raw Chuffed data
- `whydonate_all_campaigns.json` - Raw Whydonate data

**Attributes:**
| Field | Type | Description |
|-------|------|-------------|
| `id` | string | Unique ID (e.g., `chuffed_126397`) |
| `platform` | enum | `chuffed` or `whydonate` |
| `title` | string | Campaign title |
| `beneficiary` | string | Named beneficiary (from title) |
| `raised_eur` | float | Amount raised in EUR |
| `goal_eur` | float | Target amount |
| `status` | enum | `active`, `redacted`, `completed` |
| `url` | string | Campaign page URL |
| `created_at` | datetime | Creation date |

**Nested Objects:**
- `privacy` - Display name handling (public vs private)
- `freedom` - Survival/displacement/rebuild status
- `attention` - Outreach tracking
- `wellbeing` - Emotional/communication state
- `requests` - Open aid requests

---

### 2. Contact
A WhatsApp connection representing a real person.

**Sources:**
- `coupling_vetting.csv` - Chuffed campaign → contact mapping
- `whydonate_coupling_vetting.csv` - Whydonate → contact mapping
- `vetting_checklist.csv` - Consolidated unique contacts

**Attributes:**
| Field | Type | Description |
|-------|------|-------------|
| `number` | string | WhatsApp number (972/970 format) |
| `whatsapp_contact` | string | Contact name in WhatsApp |
| `campaign_count` | int | Number of campaigns managed |
| `beneficiaries` | string | List of beneficiary names |
| `platforms` | string | `chuffed`, `whydonate`, or `chuffed+whydonate` |
| `vetted` | bool | Verification status |
| `verified_name` | string | Confirmed real name |

---

### 3. Communication (Chat)
WhatsApp conversation history with a contact.

**Sources:**
- `data/exports/*.json` - Individual chat exports
- `data/exports/*.html` - Formatted chat views

**Attributes:**
| Field | Type | Description |
|-------|------|-------------|
| `chat_id` | string | WhatsApp chat identifier |
| `contact_number` | string | Phone number |
| `messages` | array | Message history |
| `last_message` | datetime | Most recent activity |

---

## Relationships

```
┌─────────────────┐     N:1     ┌─────────────────┐
│    Campaign     │─────────────│     Contact     │
│                 │             │                 │
│ - id            │             │ - number        │
│ - platform      │             │ - whatsapp_name │
│ - title         │             │ - campaign_count│
│ - beneficiary   │             │ - vetted        │
└─────────────────┘             └────────┬────────┘
                                         │
                                         │ 1:N
                                         │
                                ┌────────▼────────┐
                                │  Communication  │
                                │                 │
                                │ - messages[]    │
                                │ - last_activity │
                                └─────────────────┘
```

### Key Relationships:
1. **Campaign → Contact** (Many-to-One)
   - Multiple campaigns can be managed by the same contact
   - Linked via `number` field in coupling files

2. **Contact → Communications** (One-to-Many)
   - Each contact may have multiple chat exports
   - Linked via phone number

3. **Campaign → Campaign** (Implicit)
   - Same beneficiary may have campaigns on both platforms
   - Cross-referenced by matching WhatsApp numbers

---

## Data Flow

```
Chuffed Dashboard ──► chuffed_campaigns.json ──┐
                                               ├──► campaigns_unified.json
Whydonate Dashboard ─► whydonate_all_campaigns ┘
                                               
coupling_vetting.csv ──────┐
                           ├──► vetting_checklist.csv (143 unique contacts)
whydonate_coupling_vetting ┘

WhatsApp Web ──► data/exports/*.json (166 chat files)
```

---

## Statistics

| Entity | Count |
|--------|-------|
| Chuffed Campaigns | 163 |
| Whydonate Campaigns | 172 |
| **Total Campaigns** | **335** |
| Unique WhatsApp Contacts | 143 |
| Chat Exports | 166 |
| Avg Campaigns per Contact | 2.3 |

---

## Files Summary

| File | Purpose |
|------|---------|
| `campaigns_unified.json` | Master campaign database |
| `coupling_vetting.csv` | Chuffed → WhatsApp mapping |
| `whydonate_coupling_vetting.csv` | Whydonate → WhatsApp mapping |
| `vetting_checklist.csv` | Unique contacts for verification |
| `data/exports/` | WhatsApp chat histories |
