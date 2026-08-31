# Step 7 Deep-Dive: IBM watsonx BI

Connect IBM watsonx BI to the native KPI tables in watsonx.data (via **Presto**),
import them, and ask KPI questions in the conversational Copilot.

> **Validated** end-to-end. The steps below reflect what actually worked
> (connection via the **JSON** from watsonx.data's **Configuration** tab, and an
> **API key from the TechZone reservation page**). A field-by-field reference
> follows in case your console exposes individual fields instead of JSON.

---

## Note: service-to-service authorization was NOT required

In our validated run, **no service-to-service (s2s) authorization was needed** —
we simply supplied the Presto instance details + an API key and the connection
worked. This held true even though **watsonx.data and watsonx BI were in two
different IBM Cloud accounts**: because the connector authenticates with an
explicit **API key** (not implicit service identity), watsonx BI connects as a
normal client, so no cross-account IAM policy is required.

> IBM's generic docs mention s2s authorization for the "IBM watsonx.data Presto"
> connector (used for profiling/metadata jobs). If your environment ever fails
> the connection/profiling step, s2s auth is the thing to check — but it was
> **not** necessary here. For a TechZone-provisioned lab across two accounts,
> the API-key connection is sufficient.

---

## 7a — Get the connection JSON + API key

1. **Connection JSON** — In the **watsonx.data console**, open the
   **Configuration** tab and copy the **watsonx.data Presto connection details
   in JSON** (host, port, instance ID/name, CRN, engine hostname/ID/port, SSL,
   etc.). This single JSON contains everything the connector needs.
2. **API key** — Retrieve your API key from the **TechZone reservation page**
   for this environment. (In TechZone-provisioned labs the API key is shown on
   the reservation details, not generated in IAM.)
3. **Username** — `ibmlhapikey_<YOUR_EMAIL>` (the API key is the password).

> Keep the JSON + API key handy; you paste them in 7b.

---

## 7b — Create the connection in watsonx BI

1. watsonx BI → **Data and Metrics** → **Create metrics** → give the semantic
   model a name (e.g. `KPI Copilot`).
2. **Add data** → **New connection**.
3. Select the **IBM watsonx.data Presto** connector.
4. **Paste the JSON** from 7a into the connection form (this fills host, port,
   instance ID/name, CRN, and engine details in one shot). Then set:
   - **Username**: `ibmlhapikey_<YOUR_EMAIL>`
   - **Password**: the **API key** from the TechZone reservation page
   - **SSL is enabled**: checked (paste the SSL certificate if requested)
5. **Test connection** → **Create**.

✅ **Checkpoint:** Connection test succeeds.

---

## 7c — Import the KPI tables

From the new connection, browse to **`iceberg_catalog` → `kpi`** and import the
4 tables:
- `kpi_revenue_per_minute`
- `kpi_order_throughput`
- `kpi_payment_failure_rate`
- `kpi_regional_sales_trends`

Continue the create-metrics flow to bring them in as data assets / metrics.

✅ **Checkpoint:** The 4 KPI tables are imported into watsonx BI.

---

## 7d — Ask KPI questions in the conversation (Copilot)

Open the **conversation** experience and ask natural-language questions against
the imported KPIs, for example:
- "What is our total revenue in the last 10 minutes?"
- "Which region has the highest net sales right now?"
- "Is our payment failure rate increasing?"
- "Show orders per minute as a trend."

(Optional) Build a dashboard: revenue line chart over `window_start`,
net-revenue bar by `region`, a failure-rate KPI tile.

✅ **Done** when the Copilot returns sensible answers about your KPIs. 🎉

---

## Field-by-field reference (fallback, if no JSON paste)

If your console asks for individual fields rather than a JSON blob, use the
**IBM watsonx.data Presto** connector with:

| Field | Value / where |
|-------|---------------|
| Name / Description | Your choice |
| Select the environment | leave **unchecked** |
| Hostname / IP | watsonx.data instance URL (Configuration → Connection info) |
| Port | from Connection info |
| Instance ID / Instance name / CRN | instance home (**info icon**) |
| Engine's hostname (no `:port`) | Presto engine details |
| Engine ID / Engine's port | Presto engine details |
| SSL is enabled | **checked**; paste the certificate downloaded from the console |
| Username | `ibmlhapikey_<YOUR_EMAIL>` |
| Password | API key (TechZone reservation page, or an IAM API key) |

---

## Notes & gotchas

- **Data freshness**: watsonx BI reads the **native** KPI tables, which are a
  snapshot from the last Spark bridge run (Step 6). Re-run the bridge to refresh
  before a live demo.
- **Empty results in BI**: verify in Presto first
  (`SELECT * FROM iceberg_catalog.kpi.kpi_revenue_per_minute LIMIT 5;`). If
  Presto has rows but BI doesn't, re-check the connection's engine details.
- **Connection test fails**: check the pasted JSON/engine details (host, port,
  engine hostname/ID/port), the SSL certificate, and that the **API key** is
  current (TechZone reservations can expire). s2s authorization was **not**
  required in our run, but it's worth checking if profiling specifically fails.
