# Lab 1 — Fleet Backend

**Duration:** 10 minutes  
**Prerequisite:** [Lab 0 — Setup](../00-setup/README.md) ✅  
**Service:** `fleetops-backend` · running at `http://localhost:8085`

---

## Overview

The fleet backend is fully pre-built and running. In this lab you will explore what it exposes, verify the key APIs via Swagger UI, understand the incident truck scenario, and run the agent pipeline in **mock mode** — so you understand the complete flow before building the real agents in Lab 3.

| Exercise | Task | Time |
|---|---|---|
| [Exercise 1](#exercise-1--explore-the-api) | Swagger UI walkthrough | 3 min |
| [Exercise 2](#exercise-2--understand-the-incident-truck) | Inspect the incident truck telemetry | 3 min |
| [Exercise 3](#exercise-3--run-the-pipeline-in-mock-mode) | Run the 5-agent pipeline in mock mode | 4 min |

---

## What the Backend Provides

| Endpoint | Purpose |
|---|---|
| `GET /api/trucks` | Live telemetry for all 10 simulated trucks |
| `GET /api/trucks/{truck_id}` | Single truck — temperature, location, cargo, route |
| `GET /api/alerts` | Active temperature and weather alerts |
| `POST /api/agents/execute` | Trigger the 5-agent watsonx Orchestrate pipeline |
| `GET /api/agents/status/{execution_id}` | Poll pipeline execution status |
| `GET /api/agents/notifications/{truck_id}` | Notifications sent by the pipeline |
| `GET /api/agents/history` | Historical pipeline executions |

The simulation engine runs a background loop every **5 seconds**, advancing truck positions and drifting temperatures. Four trucks have pre-assigned incidents. One truck is your critical scenario truck.

---

## Exercise 1 — Explore the API

Open `http://localhost:8085/docs` in your browser.

### Step 1.1 — List all trucks

Expand `GET /api/trucks` → **Try it out** → **Execute**.

You should receive a list of 10 trucks. Note the structure of each truck:
- `telemetry` — temperature, coolantStatus, currentLocation, speed
- `cargo` — type, value, criticalThreshold
- `currentTrip` — origin, destination, plannedRoute, estimatedArrival
- `status` — ACTIVE / DIVERTED / SPOILED

### Step 1.2 — Check active alerts

Expand `GET /api/alerts` → **Try it out** → **Execute**.

Look for alerts with `type: WEATHER_FAILURE` and `severity: CRITICAL`.

### Step 1.3 — Ask Bob to explain the API

Switch IBM Bob to **Agent mode** (default). Send:

```
Explain the fleet backend API structure — what does each endpoint return
and how do the trucks, alerts, and agents endpoints connect to each other?
```

Review the explanation before continuing.

---

## Exercise 2 — Understand the Incident Truck

Call `GET /api/trucks/{truck_id}` in the Swagger UI. Use the truck ID that shows a `WEATHER_FAILURE` alert (check the alerts from Exercise 1.2 — note the `truckId` field).

**Key values to observe:**

| Field | What to look for |
|---|---|
| `temperature` | Is it above or approaching `criticalThreshold`? |
| `coolantStatus` | `NORMAL` for a weather incident |
| `cargo.type` | `pharmaceuticals` |
| `incidentType` | `WEATHER_FAILURE` |
| `currentTrip` | Atlanta, GA → Macon, GA · I-75 |

> **The scenario:** The cargo is above threshold, a severe weather system sits directly on the I-75 corridor, and there is under 2 hours to act before the pharmaceutical cargo is unrecoverable.

---

## Exercise 3 — Run the Pipeline in Mock Mode

Before building real agents, run the pipeline in **mock mode** to understand the full flow.

> **Mock mode** is active whenever `WATSONX_ORCHESTRATE_URL` is not set or the agent IDs are blank — which is the case right now. The pipeline completes in 2–3 seconds with hardcoded responses.

### Step 3.1 — Trigger the pipeline

In Swagger UI, expand `POST /api/agents/execute` → **Try it out**. Enter:

```json
{ "truck_id": "<your-incident-truck-id>" }
```

Click **Execute**. You will receive an `execution_id` and `status: RUNNING`.

### Step 3.2 — Poll for completion

Copy the `execution_id`. Expand `GET /api/agents/status/{execution_id}`. Enter the ID and execute.

You will see five agent stages — `weather`, `station`, `route`, `decision`, `notification` — each with a status field. Poll every 5 seconds until `status: COMPLETED`.

### Step 3.3 — Read the mock decision

When `COMPLETED`, the decision agent output will show:
```
decision: EMERGENCY_REROUTE
urgency: CRITICAL
riskScore: 85
recommendation: Reroute to nearest cold storage facility
```

### Step 3.4 — Verify the truck was updated

Call `GET /api/trucks/{truck_id}` again. The `status` field should now show `DIVERTED`.

### Step 3.5 — Check the notification

Call `GET /api/agents/notifications/{truck_id}`. You should see the mock notification stored for the driver.

> This is the **exact same flow** you will run in Lab 4 — but with real agents making intelligent decisions based on actual weather, station, and route data.

---

## ✅ Checkpoint

Before moving to Lab 2, confirm:

- [ ] `GET /api/trucks` returns 10 trucks
- [ ] At least one truck shows `incidentType: WEATHER_FAILURE`
- [ ] Mock pipeline completes with `decision: EMERGENCY_REROUTE`
- [ ] Truck status shows `DIVERTED` after pipeline completion
- [ ] Notification is stored for the incident truck

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Swagger UI does not load | Start the backend (from Lab 0 Step 3): `cd 01-fleet-backend && python3.12 -m venv venv && source venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --host 127.0.0.1 --port 8085 --reload` |
| No trucks returned | Backend started but simulation not initialised — wait 5 seconds and retry. |
| Pipeline stuck on `RUNNING` | In mock mode it should complete in 2–3 s. If stuck after 10 s, restart the backend. |

---

**[→ Lab 2: Build the Forecast Service](../02-forecast-service/README.md)**
