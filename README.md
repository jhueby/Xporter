# xporter — XSOAR to XSIAM Incident Exporter

Content pack for exporting Cortex XSOAR 6 or XSOAR 8 incidents into Cortex XSIAM. Includes two integrations covering both push and pull workflows.

## Integrations

### 1. XSIAM Alert Pusher (Push — runs on XSOAR 6 or 8)

Pushes XSOAR incidents to XSIAM as parsed alerts via the [Insert Parsed Alerts API](https://docs-cortex.paloaltonetworks.com/r/Cortex-XSIAM/Cortex-XSIAM-API-Reference/Insert-Parsed-Alerts). Compatible with both XSOAR 6 (on-prem) and XSOAR 8 (cloud).

**How it works:**
- Queries XSOAR for incidents matching a configurable filter
- Maps each incident to the XSIAM parsed alert schema with full incident context (custom fields, labels, close status, raw JSON)
- Event timestamp maps to the original XSOAR occurred/created time (adjustable via timestamp offset)
- Posts the alerts to XSIAM where they are ingested and grouped into incidents automatically
- Tracks sync state for incremental pushes — only sends new incidents each run

**Commands:**
| Command | Description |
|---|---|
| `!xsiam-push-incidents` | Bulk push incidents matching a query |
| `!xsiam-push-incident` | Push a single incident by ID |
| `!xsiam-sync-new-incidents` | Find and push only new incidents not yet synced |
| `!xsiam-reset-sync` | Reset sync state so next sync sends all incidents |

**Configuration:**
| Parameter | Description |
|---|---|
| XSOAR Server URL | URL of the XSOAR instance. XSOAR 6: `https://192.168.1.215/`. XSOAR 8: `https://api-{tenant}.xdr.us.paloaltonetworks.com` |
| XSOAR API Key | XSOAR API key for authentication |
| XSOAR API Key ID | XSOAR 8 only — the numeric API Key ID. Leave blank for XSOAR 6 |
| XSIAM API URL | Your XSIAM tenant API URL |
| XSIAM API Key | API key for authentication |
| XSIAM API Key ID | Key ID associated with the API key |
| Incident query filter | Optional XSOAR query to filter incidents |
| Maximum incidents per push | Batch size limit (default: 100) |
| Elevate Low severity to Medium | Map Low severity to Medium so alerts create cases instead of issues only. Only Medium or higher severity alerts will automatically trigger playbooks |
| Timestamp offset (minutes) | Minutes to add to the original XSOAR timestamp. The event timestamp defaults to the XSOAR occurred/created time. Use a positive offset to shift old incidents forward. XSIAM silently drops alerts with timestamps too far in the past |

### 2. XSOAR Incident Collector (Pull — runs on XSIAM)

Runs on XSIAM and fetches incidents from a remote XSOAR 6 or XSOAR 8 instance via the XSOAR REST API.

**How it works:**
- Connects to the XSOAR `/incidents/search` endpoint on a schedule (auto-detects XSOAR 6 vs 8 API paths)
- Fetches incidents created since the last successful run
- Maps them to XSIAM incidents with original XSOAR metadata preserved in custom fields
- Handles deduplication across fetch cycles

**Commands:**
| Command | Description |
|---|---|
| `!xsoar6-get-incidents` | Search incidents on the remote XSOAR instance |
| `!xsoar6-get-incident` | Get a specific incident by ID |

**Configuration:**
| Parameter | Description |
|---|---|
| XSOAR Server URL | URL of the XSOAR instance. XSOAR 6: `https://{server-ip}`. XSOAR 8: `https://api-{tenant}.xdr.us.paloaltonetworks.com` |
| XSOAR API Key | API key for authentication |
| XSOAR API Key ID | XSOAR 8 only — the numeric API Key ID. Leave blank for XSOAR 6 |
| First fetch time | How far back to look on first run (default: 3 days) |
| Maximum incidents per fetch | Batch size limit (default: 50) |
| Incident query filter | Optional XSOAR query to filter incidents |
| Incident type | XSIAM incident type to assign |

## Which integration should I use?

| Scenario | Recommended Integration |
|---|---|
| XSOAR can reach XSIAM (outbound HTTPS) | **XSIAM Alert Pusher** (push) |
| XSIAM can reach XSOAR (inbound HTTPS or Broker VM) | **XSOAR Incident Collector** (pull) |
| Want incidents as XSIAM alerts with auto-grouping | **XSIAM Alert Pusher** (push) |
| Want incidents directly as XSIAM incidents | **XSOAR Incident Collector** (pull) |
| Need on-demand / manual export | **XSIAM Alert Pusher** (push) |
| Need continuous automatic sync | Either — both support scheduled operation |

### 3. Automation Scripts (run on XSIAM)

**CloseFromXSOAR** — Playbook task that extracts Close Reason and Close Notes from a pushed XSOAR alert and closes the XSIAM case if the XSOAR incident was closed.

**SyncXSOARCloseStatus** — Scheduled job script that queries XSIAM for open XSOAR-sourced alerts, checks each alert's description for close status, and resolves alerts whose XSOAR incidents are closed. Maps XSOAR close reasons to XSIAM resolution statuses (Resolved, False Positive, Duplicate, Other).

### 4. Playbook

**Close XSIAM Case From XSOAR** — Attach to XSIAM cases with source "Palo Alto Networks - XSOAR". Runs CloseFromXSOAR to auto-close cases when the XSOAR incident was closed.

## Pack Structure

```
Packs/XSOARIncidentExporter/
├── pack_metadata.json
├── Integrations/
│   ├── XSIAMAlertPusher/
│   │   ├── XSIAMAlertPusher.py
│   │   ├── XSIAMAlertPusher.yml
│   │   └── XSIAMAlertPusher_description.md
│   └── XSOAR6Collector/
│       ├── XSOAR6Collector.py
│       ├── XSOAR6Collector.yml
│       └── XSOAR6Collector_description.md
├── Scripts/
│   ├── CloseFromXSOAR/
│   │   ├── CloseFromXSOAR.py
│   │   └── CloseFromXSOAR.yml
│   └── SyncXSOARCloseStatus/
│       ├── SyncXSOARCloseStatus.py
│       └── SyncXSOARCloseStatus.yml
└── Playbooks/
    └── Close_XSIAM_Case_From_XSOAR.yml
```

## Exporting All XSOAR Incidents to XSIAM

### Step 1 — Install the Integration

Upload the unified `Xporter.yml` file to your XSOAR instance via **Settings → Integrations → Upload Integration**.

### Step 2 — Configure the Instance

Create a new instance of the **Xporter** integration and fill in:

- **XSOAR Server URL** — XSOAR 6: `https://192.168.1.215/`. XSOAR 8: `https://api-{tenant}.xdr.us.paloaltonetworks.com`
- **XSOAR API Key**
- **XSOAR API Key ID** — XSOAR 8 only. Leave blank for XSOAR 6
- **XSIAM API URL** — e.g. `https://api-{tenant}.xdr.us.paloaltonetworks.com`
- **XSIAM API Key** and **XSIAM API Key ID**
- **Elevate Low severity to Medium** — check this if you want all incidents to create cases and trigger playbooks in XSIAM. Only Medium or higher severity alerts automatically trigger playbooks.
- **Timestamp offset (minutes)** — the event timestamp defaults to the original XSOAR occurred/created time. If your incidents are old, set a positive offset to shift them forward so XSIAM doesn't silently drop them.

### Step 3 — Initial Bulk Export

Run in the XSOAR playground:

```
!xsiam-sync-new-incidents max_incidents="100"
```

Each run picks up where the last one left off. Run it repeatedly until all incidents are synced. To start over, run `!xsiam-reset-sync`.

### Step 4 — Ongoing Sync

Create a scheduled job in XSOAR that runs `!xsiam-sync-new-incidents` on an interval (e.g. every 15 minutes). It only sends new incidents each run — no duplicates.

### Step 5 — Close Status Sync (Optional)

Upload the `SyncXSOARCloseStatus` script to XSIAM and set it up as a scheduled job. It queries XSIAM for open XSOAR-sourced alerts, checks each alert's description for close status, and resolves them with the matching close reason and notes.

## License

MIT
