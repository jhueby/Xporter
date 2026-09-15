# xporter — XSOAR 6 to XSIAM Incident Exporter

Content pack for exporting Cortex XSOAR 6 incidents into Cortex XSIAM. Includes two integrations covering both push and pull workflows.

## Integrations

### 1. XSIAM Alert Pusher (Push — runs on XSOAR 6)

Pushes XSOAR 6 incidents to XSIAM as parsed alerts via the [Insert Parsed Alerts API](https://docs-cortex.paloaltonetworks.com/r/Cortex-XSIAM/Cortex-XSIAM-API-Reference/Insert-Parsed-Alerts).

**How it works:**
- Queries XSOAR 6 for incidents matching a configurable filter
- Maps each incident to the XSIAM parsed alert schema (severity, timestamps, description)
- Posts the alerts to XSIAM where they are ingested and grouped into incidents automatically

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
| XSIAM API URL | Your XSIAM tenant API URL |
| XSIAM API Key | API key for authentication |
| XSIAM API Key ID | Key ID associated with the API key |
| Incident query filter | Optional XSOAR query to filter incidents |
| Maximum incidents per push | Batch size limit (default: 100) |

### 2. XSOAR 6 Incident Collector (Pull — runs on XSIAM)

Runs on XSIAM and fetches incidents from a remote XSOAR 6 instance via the XSOAR 6 REST API.

**How it works:**
- Connects to the XSOAR 6 `/incidents/search` endpoint on a schedule
- Fetches incidents created since the last successful run
- Maps them to XSIAM incidents with original XSOAR 6 metadata preserved in custom fields
- Handles deduplication across fetch cycles

**Commands:**
| Command | Description |
|---|---|
| `!xsoar6-get-incidents` | Search incidents on the remote XSOAR 6 |
| `!xsoar6-get-incident` | Get a specific incident by ID |

**Configuration:**
| Parameter | Description |
|---|---|
| XSOAR 6 Server URL | URL of the XSOAR 6 instance |
| XSOAR 6 API Key | API key for authentication |
| First fetch time | How far back to look on first run (default: 3 days) |
| Maximum incidents per fetch | Batch size limit (default: 50) |
| Incident query filter | Optional XSOAR query to filter incidents |
| Incident type | XSIAM incident type to assign |

## Which integration should I use?

| Scenario | Recommended Integration |
|---|---|
| XSOAR 6 can reach XSIAM (outbound HTTPS) | **XSIAM Alert Pusher** (push) |
| XSIAM can reach XSOAR 6 (inbound HTTPS or Broker VM) | **XSOAR 6 Incident Collector** (pull) |
| Want incidents as XSIAM alerts with auto-grouping | **XSIAM Alert Pusher** (push) |
| Want incidents directly as XSIAM incidents | **XSOAR 6 Incident Collector** (pull) |
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

## Installation

1. Upload the unified `Xporter.yml` file to your XSOAR 6 instance via **Settings → Integrations → Upload Integration**.
2. Configure the appropriate integration instance with your API credentials.
3. For the push integration, use `!xsiam-sync-new-incidents` on a scheduled job in XSOAR 6 to continuously push new incidents.
4. For the pull integration, enable `Fetches incidents` on the XSIAM integration instance.
5. To auto-close XSIAM issues when XSOAR incidents close, set up the `SyncXSOARCloseStatus` script as a scheduled job in XSIAM.

## License

MIT
