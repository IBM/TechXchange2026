# Lab 3.3 — Notification Agent & Wire All IDs

**Duration:** 10 minutes  
**Prerequisite:** [Lab 3.2](../03-2-route-decision-agents/README.md) ✅  
**Agent:** ⑤ Notification Agent · then wire all 5 IDs to the fleet backend

---

## Goal

Upload the final agent, then wire all five agent IDs into `01-fleet-backend/.env` so the live pipeline can run in Lab 4.

> **No Twilio credentials required.** The forecast backend automatically runs in **mock mode** when `TWILIO_AUTH_TOKEN` is not set. The notification is stored in memory and returned as a simulated `message_sid` — the full pipeline completes successfully without any real WhatsApp delivery. To confirm: `GET http://localhost:5001/api/notifications/whatsapp/history`

> **Backup files:** `assets/agents/notification_agent.yaml`, `assets/tools/whatsapp_notification/whatsapp_notification_tool.py`, `assets/connections/fleetops_api.yaml`, `assets/connections/forecast_api.yaml`

---

## Step 1 — Upload the Notification Agent

The notification tool uses the `forecast_api` connection (not `fleetops_api`) — it sends notifications via the forecast backend endpoint.

### Option A — ADK

```bash
orchestrate agents import --file agents/notification_agent.yaml
orchestrate tools import --file tools/notification_tool/whatsapp_notification_tool.py \
  --connection forecast_api

orchestrate connections set-credentials -a forecast_api --env draft \
  -e "FORECAST_API_URL=http://localhost:5001"
```

### Option B — Orchestrate UI

1. Import `agents/notification_agent.yaml`.
2. Upload `tools/notification_tool/whatsapp_notification_tool.py`.
3. Create connection `forecast_api` with team credential `FORECAST_API_URL=http://localhost:5001`.
4. Select `forecast_api` as the connection when attaching the tool.

`notification_agent ID: ________________________`

**Test prompt:**
```
Send an emergency reroute notification for TRUCK-003 pharmaceutical truck.
The truck should divert off I-75 to the nearest cold storage facility.
urgency: CRITICAL, decision: EMERGENCY_REROUTE
```

**Expected:** JSON response with `"status": "SENT"` and a `message_sid` starting with `MOCK-` (e.g. `MOCK-A3F9B2C1D4E5`). No real WhatsApp is sent.

Verify it was stored:
```bash
curl http://localhost:5001/api/notifications/whatsapp/history
```

---

## Step 2 — Wire All Five Agent IDs to the Fleet Backend

Open `01-fleet-backend/.env` and fill in all five IDs you recorded across Labs 3.1–3.3:

```env
WATSONX_ORCHESTRATE_URL=https://<your-tenant>.ai.ibm.com
WATSONX_ORCHESTRATE_API_KEY=<your-ibm-cloud-api-key>

WATSONX_ORCHESTRATE_AGENT_WEATHER=<weather_advisor Agent ID>
WATSONX_ORCHESTRATE_AGENT_STATION=<station_agent Agent ID>
WATSONX_ORCHESTRATE_AGENT_ROUTE=<RouteOptimizationAgent ID>
WATSONX_ORCHESTRATE_AGENT_DECISION=<decision_agent Agent ID>
WATSONX_ORCHESTRATE_AGENT_NOTIFICATION=<notification_agent Agent ID>
```

---

## Step 3 — Restart the Fleet Backend

Stop the running backend (`Ctrl+C`) and restart:

```bash
cd 01-fleet-backend
source venv/bin/activate   # Windows: venv\Scripts\activate
uvicorn app.main:app --host 127.0.0.1 --port 8085 --reload
```

In the startup log, look for:
```
WatsonX Orchestrate configuration validated
Agents: weather=<id> station=<id> route=<id> decision=<id> notification=<id>
```

✅ **Success:** All five agent IDs appear in the log.  
❌ **Problem:** `missing env var` — confirm all five variables are set and the backend was fully restarted.

---

## Step 4 — Quick Live Test

Trigger the pipeline one more time to confirm live mode works before Lab 4:

```bash
curl -X POST http://localhost:8085/api/agents/execute \
  -H "Content-Type: application/json" \
  -d '{"truck_id": "<your-incident-truck-id>"}'
```

Poll `GET /api/agents/status/{execution_id}` every 5 seconds. In live mode allow **up to 30 seconds** for all five agents to complete.

When `COMPLETED`:
- `decision: EMERGENCY_REROUTE` ✅
- `urgency: CRITICAL` ✅
- `confidence: 0.9+` ✅

---

## ✅ Lab 3 Complete Checklist

- [ ] `notification_agent` uploaded — status **Active**
- [ ] Notification tool attached with `forecast_api` connection
- [ ] All 5 agent IDs recorded and set in `01-fleet-backend/.env`
- [ ] Backend restarted — startup log shows `WatsonX Orchestrate configuration validated`
- [ ] Live pipeline test returns `EMERGENCY_REROUTE` within 30 seconds

---

**[→ Lab 4: Carbon Dashboard & Live Pipeline](../../04-carbon-dashboard/README.md)**
