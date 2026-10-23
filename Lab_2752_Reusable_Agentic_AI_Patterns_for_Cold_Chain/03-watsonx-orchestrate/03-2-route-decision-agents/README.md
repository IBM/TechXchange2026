# Lab 3.2 — Route Optimization & Decision Agent

**Duration:** 10 minutes  
**Prerequisite:** [Lab 3.1](../03-1-weather-station-agents/README.md) ✅  
**Agents:** ③ Route Optimization · ④ Decision Agent

---

## Goal

Upload agents ③ and ④. These two tools perform **pure computation** — they do not call the fleet backend API, so no connection object is needed for them.

> **Backup files:** `assets/agents/RouteOptimizationAgent.yaml`, `assets/agents/decision_agent.yaml`, `assets/tools/RouteOptimization/route_optimizer_tool.py`, `assets/tools/decision_tool/decision_analysis_tool.py`

---

## Step 1 — Upload the Route Optimization Agent

### Option A — ADK

```bash
orchestrate agents import --file agents/RouteOptimizationAgent.yaml
orchestrate tools import --file tools/route_tool/route_optimizer_tool.py
```

### Option B — Orchestrate UI

1. **Build → Agents → New agent → Import from YAML** → paste `agents/RouteOptimizationAgent.yaml`.
2. **Build → Tools → Upload Python file** → upload `tools/route_tool/route_optimizer_tool.py`.
3. No connection needed — this tool runs pure computation locally.
4. Attach the tool to the `RouteOptimizationAgent`.

`RouteOptimizationAgent ID: ________________________`

**Test prompt:**
```
Given a truck near Atlanta GA with a storm on I-75, score three alternative routes
to Macon GA and recommend the safest one.
```

**Expected:** Three route options with distance, risk score, and a recommended route.

---

## Step 2 — Upload the Decision Agent

> ⚠️ **Critical:** The Decision agent receives arrays of data from the previous three agents — `stationAnalysis.facilities`, `routeAnalysis.routes`, `weatherAnalysis.segments`. It must pass these arrays **unmodified** to the `analyze_decision` tool. Emptying or truncating arrays is the most common failure mode.

### Option A — ADK

```bash
orchestrate agents import --file agents/decision_agent.yaml
orchestrate tools import --file tools/decision_tool/decision_analysis_tool.py
```

### Option B — Orchestrate UI

1. Import `agents/decision_agent.yaml`.
2. Upload `tools/decision_tool/decision_analysis_tool.py` — no connection needed.
3. Attach the tool.

`decision_agent ID: ________________________`

**Test prompt:**
```
Analyse a cold-chain emergency: pharmaceutical cargo truck on Atlanta→Macon I-75,
temperature 9.2°C (threshold 8°C), severe weather directly on route,
nearest cold storage is 15km off route. Should we reroute?
```

**Expected:**
```
decision: EMERGENCY_REROUTE
urgency: CRITICAL
riskScore: 85+
confidence: 0.9+
```

---

## Step 3 — Verify Agent Instructions Are Pure JSON

Ask Bob (Agent mode):

```
Review the decision_agent.yaml instructions — confirm the agent is instructed
to return pure JSON only with no markdown fences or explanatory text.
```

If the instructions have markdown fences in the output examples, ask Bob to remove them. The backend parser expects raw JSON.

---

## ✅ Checkpoint

- [ ] `RouteOptimizationAgent` uploaded — status **Active**
- [ ] Route tool attached (no connection needed)
- [ ] Route Preview returns 3 scored alternatives
- [ ] `decision_agent` uploaded — status **Active**
- [ ] Decision tool attached (no connection needed)
- [ ] Decision Preview returns `EMERGENCY_REROUTE` with `riskScore ≥ 85`
- [ ] Decision agent instructions specify pure JSON output

---

**[→ Lab 3.3: Notification Agent & Wire All IDs](../03-3-notification-wire/README.md)**
