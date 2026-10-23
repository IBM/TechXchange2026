# Lab 4 — Carbon Dashboard & Live Pipeline

**Duration:** 15 minutes  
**Prerequisite:** [Lab 3 — watsonx Orchestrate](../03-watsonx-orchestrate/README.md) ✅  
**Bob Mode:** Agent mode (default)  
**Service:** `FleetOps` · running at `http://localhost:4000`

---

## Overview

The Carbon dashboard is already scaffolded with five tabs — but the data bindings are empty. You will use IBM Bob to complete the JavaScript wiring, then run the full end-to-end agentic pipeline live, watching the truck reroute in real time.

| Exercise | Task | Time |
|---|---|---|
| [Exercise 1](#exercise-1--complete-the-dashboard-with-bob) | Wire all 5 tabs with Bob | 7 min |
| [Exercise 2](#exercise-2--verify-the-dashboard) | Start and verify all tabs | 3 min |
| [Exercise 3](#exercise-3--run-the-live-pipeline) | Run the live pipeline, watch the reroute | 5 min |

---

## Exercise 1 — Complete the Dashboard with Bob

Switch IBM Bob back to **Agent mode** (default). Send:

```
I have a Carbon dashboard at smart-cold-chain/FleetOps/public/.
It has five tabs: Fleet Overview, Truck Detail, Forecast, Agent Pipeline, and Notifications.
The fleet backend runs at http://localhost:8085 and the forecast service at http://localhost:5001.
The Node.js proxy in server.js forwards /api/* to port 8085 and /forecast/* to port 5001.
Wire up all five tabs so each one fetches live data from the correct endpoint and
updates every 5 seconds. Use vanilla JavaScript with the fetch API — no React needed.
```

Bob will generate or patch the JavaScript files in `FleetOps/public/`. Apply all changes.

---

## Exercise 2 — Verify the Dashboard

### Step 2.1 — Start the dashboard

```bash
cd FleetOps
npm install
node server.js
```

Open `http://localhost:4000` in your browser.

### Step 2.2 — Verify Fleet Overview tab

The Fleet Overview tab should populate with all 10 trucks within 5 seconds.  
Each truck card shows: truck ID, temperature, status, cargo type.

### Step 2.3 — Verify Truck Detail tab

Click the **Truck Detail** tab. Confirm you see the incident truck with:

- Temperature: above the 8.0 °C threshold (shown with a red indicator)
- Coolant Status: NORMAL
- Cargo: pharmaceuticals
- Route: Atlanta, GA → Macon, GA · I-75
- Incident: WEATHER_FAILURE

### Step 2.4 — Verify Forecast tab

Click the **Forecast** tab. Confirm:
- `breach_predicted: true`
- `risk_level: CRITICAL` or `HIGH`
- Temperature chart showing the predicted rise

If any tab shows an error or empty data, use these Bob debug prompts:

**Forecast tab not loading:**
```
The Forecast tab is not loading data — the fetch to /forecast/api/forecast/temperature/{truck_id}
is failing. Debug and fix the proxy configuration in server.js.
```

**Truck Detail tab not showing incident truck:**
```
The Truck Detail tab is showing all trucks instead of filtering to the incident truck.
Fix the JavaScript in public/app.js to filter for the truck with incidentType WEATHER_FAILURE.
```

**Agent Pipeline tab not updating:**
```
The Agent Pipeline tab is not polling for status updates. The execution_id is returned
but the status never changes from RUNNING. Fix the polling logic in public/agents.js
to call GET /api/agents/status/{execution_id} every 3 seconds until COMPLETED.
```

**Fleet Overview not populating:**
```
The Fleet Overview tab shows 0 trucks. The fetch to /api/trucks is failing.
Debug the proxy in server.js — confirm /api/* forwards to port 8085.
```

Apply any fixes and refresh.

---

## Exercise 3 — Run the Live Pipeline

### Step 3.1 — Trigger the pipeline

Click the **Agent Pipeline** tab on the dashboard. Find the incident truck and click **Run Pipeline**.

The dashboard calls `POST /api/agents/execute` and begins polling `GET /api/agents/status/{execution_id}` every 3 seconds.

### Step 3.2 — Watch the pipeline progress

You should see five stages light up sequentially:

```
☁️  Weather Advisor     — fetches live weather along the I-75 corridor
🏢  Station Agent       — searches for cold storage stations near the diversion point
🗺️  Route Optimization  — calculates the optimal reroute avoiding the storm
✓   Decision Agent      — scores the risk and issues a recommendation
📩  Notification Agent  — sends an alert to the driver
```

### Step 3.3 — Read the live decision

When status reaches `COMPLETED`:

```
decision:          EMERGENCY_REROUTE
urgency:           CRITICAL
recommended_route: Nearest cold storage diversion off I-75
confidence:        0.94
```

### Step 3.4 — Confirm the truck rerouted

Switch to the **Fleet Overview** tab. The incident truck status should now show **DIVERTED**.

### Step 3.5 — Check the notification

Click the **Notifications** tab. You should see the WhatsApp-style notification stored for the incident truck with the reroute instruction.

---

## ✅ Lab Complete

You have built the full end-to-end workflow:

```
Live telemetry  →  Granite TTM-R2 forecast  →  5-agent agentic pipeline
                →  Autonomous reroute decision  →  Dashboard update
```

**Lab 4 Complete. Lab 2752 Complete.**

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Dashboard port shows nothing | Confirm the backend is on 8085 and forecast service on 5001. Check proxy config in `server.js`. |
| Fleet Overview shows 0 trucks | The proxy `/api/*` forward is not working. Ask Bob to check `server.js`. |
| Forecast tab empty | The proxy `/forecast/*` forward is missing. Ask Bob to debug `server.js`. |
| Pipeline stuck on `RUNNING` > 60 s | Check backend terminal for IAM token errors — your API key may be invalid or expired. |
| `DIVERTED` not showing after pipeline | The Decision agent may be returning markdown instead of JSON. Check agent instructions. |

---

## What You Built — Summary

| Component | What you did |
|---|---|
| **Fleet Backend** | Explored, verified APIs, ran mock pipeline |
| **Forecast Service** | Built with Bob TTM mode — IBM Granite TTM-R2 risk scoring |
| **watsonx Orchestrate** | 5 agents + Python tools — uploaded, connected, wired |
| **Carbon Dashboard** | 5 tabs wired with Bob — live 5-second polling |

---


