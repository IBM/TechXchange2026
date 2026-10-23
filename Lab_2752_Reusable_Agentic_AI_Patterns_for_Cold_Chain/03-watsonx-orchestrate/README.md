# Lab 3 — watsonx Orchestrate

**Duration:** 30 minutes  
**Prerequisite:** [Lab 2 — Forecast Service](../02-forecast-service/README.md) ✅  
**Bob Mode:** 🚛 FleetOps Agent Builder  
**Output:** 5 agent YAMLs + 5 Python tools · uploaded to watsonx Orchestrate · IDs wired to backend

---

## Overview

You will use IBM Bob's **FleetOps Agent Builder mode** to generate all five watsonx Orchestrate agents and their Python tools in one prompt. You will then upload them to watsonx Orchestrate, set the connection credentials the tools need, and wire the five agent IDs back to the fleet backend.

### The Five-Agent Pipeline

```
① Weather Advisor → ② Station Agent → ③ Route Optimization → ④ Decision Agent → ⑤ Notification Agent
```

Each agent runs sequentially. The Decision agent's output is what changes the truck status to `DIVERTED` and triggers the WhatsApp notification.

### Sub-Labs

| Sub-Lab | Folder | What You Do | Time |
|---|---|---|---|
| 3.1 | [`03-1-weather-station-agents/`](./03-1-weather-station-agents/README.md) | Build + upload agents ① and ② | 10 min |
| 3.2 | [`03-2-route-decision-agents/`](./03-2-route-decision-agents/README.md) | Build + upload agents ③ and ④ | 10 min |
| 3.3 | [`03-3-notification-wire/`](./03-3-notification-wire/README.md) | Build agent ⑤, set connections, wire all IDs | 10 min |

---

## Before You Start — Activate the Bob Mode

1. In IBM Bob IDE, click the **mode selector** (bottom-left).
2. Select **🚛 FleetOps Agent Builder**.
3. Bob confirms: *"FleetOps Agent Builder mode active."*

---

## Generate All Five Agents in One Prompt

With the mode active, send Bob:

```
Build the complete five-agent pipeline for a cold-chain logistics emergency rerouting
workflow. The agents run sequentially:
  weather_advisor → station_agent → RouteOptimizationAgent → decision_agent → notification_agent

The fleet backend API is at http://localhost:8085. Build all five agent YAML files and
all five Python tools with @tool decorators, Pydantic models, and API integration.
Output everything into an agents/ and tools/ folder.
```

Bob will ask discovery questions — answer as follows:

| Question | Answer |
|---|---|
| Backend URL? | `http://localhost:8085` |
| Cargo type? | `pharmaceutical` (temperature range 2–8 °C) |
| WhatsApp notification? | Include the tool but use demo/mock mode — no real Twilio credentials needed |
| Plan file first? | Yes |

Review the `plan.md` Bob creates. Approve it. Bob generates:

```
agents/weather_advisor.yaml          tools/weather_forecast/weather_forecast_tool.py
agents/station_agent.yaml            tools/station_tool/station_search_tool.py
agents/RouteOptimizationAgent.yaml   tools/route_tool/route_optimizer_tool.py
agents/decision_agent.yaml           tools/decision_tool/decision_analysis_tool.py
agents/notification_agent.yaml       tools/notification_tool/whatsapp_notification_tool.py
```

Apply all generated files. Then continue to the sub-labs to upload them.

---

## ✅ Lab 3 Complete Checklist

- [ ] All 5 agent YAMLs generated and applied
- [ ] All 5 Python tool files generated and applied
- [ ] `fleetops_api` connection created in watsonx Orchestrate with team credentials
- [ ] All 5 agents uploaded and showing **Active** in Orchestrate
- [ ] All 5 agent IDs recorded in `01-fleet-backend/.env`
- [ ] Fleet backend restarted — startup log shows `WatsonX Orchestrate configuration validated`

---

**[→ Lab 4: Carbon Dashboard & Live Pipeline](../04-carbon-dashboard/README.md)**
