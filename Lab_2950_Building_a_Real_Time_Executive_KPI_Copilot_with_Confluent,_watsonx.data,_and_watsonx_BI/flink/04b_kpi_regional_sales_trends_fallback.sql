-- =============================================================================
-- KPI 4 (FALLBACK): REGIONAL SALES TRENDS  -- two-step version
-- =============================================================================
-- Lab-2950 : Real-Time Executive KPI Copilot
--
-- WHEN TO USE THIS FILE:
--   Use this ONLY if the view-based version
--   (04_kpi_regional_sales_trends.sql) fails in your Flink environment.
--   This version windows each source separately, then joins.
--   NOTE: the main 04 (CREATE VIEW + CREATE TABLE AS) was validated and works;
--   this fallback is kept only as a backup for different Flink versions.
--
-- ⚠️ RUN EACH OF THE THREE STATEMENTS BELOW ONE AT A TIME.
--   Confluent Cloud Flink runs a single statement per execution. Highlight
--   statement (a), run it, wait for success; then (b); then (c). Do NOT paste
--   all three at once (you will get "Only a single statement is supported").
--
-- TRADE-OFF:
--   This creates THREE continuously running statements instead of ONE
--   (two windowed aggregates + a join). Fine for solo testing; for the
--   30-person shared lab prefer the single-statement version if it works.
--
-- HOW IT WORKS:
--   (a) revenue per region per 5-min window (successful payments)
--   (b) refunds per region per 5-min window
--   (c) LEFT JOIN them and subtract refunds from revenue
-- =============================================================================

-- (a) Revenue side: successful payments per region in 5-min windows.
CREATE TABLE _rev_5m AS
SELECT
    window_start,
    window_end,
    region,
    COUNT(*)                              AS orders_paid,
    COUNT(DISTINCT customer_id)           AS unique_customers,
    CAST(SUM(amount) AS DECIMAL(12, 2))   AS revenue_usd
FROM TABLE(
    TUMBLE(TABLE payments, DESCRIPTOR(`$rowtime`), INTERVAL '5' MINUTE)
)
WHERE status = 'success'
GROUP BY window_start, window_end, region;

-- (b) Refund side: refunds per region in the same 5-min windows.
CREATE TABLE _refund_5m AS
SELECT
    window_start,
    window_end,
    region,
    COUNT(*)                              AS refund_count,
    CAST(SUM(amount) AS DECIMAL(12, 2))   AS refund_usd
FROM TABLE(
    TUMBLE(TABLE refunds, DESCRIPTOR(`$rowtime`), INTERVAL '5' MINUTE)
)
GROUP BY window_start, window_end, region;

-- (c) Final KPI: net sales = revenue - refunds, per region per 5-min window.
CREATE TABLE kpi_regional_sales_trends AS
SELECT
    r.window_start,
    r.window_end,
    r.region,
    r.orders_paid,
    r.unique_customers,
    r.revenue_usd,
    COALESCE(f.refund_count, 0)                                   AS refund_count,
    COALESCE(f.refund_usd, CAST(0 AS DECIMAL(12, 2)))             AS refund_usd,
    CAST(r.revenue_usd - COALESCE(f.refund_usd, 0) AS DECIMAL(12, 2)) AS net_revenue_usd
FROM _rev_5m AS r
LEFT JOIN _refund_5m AS f
    ON  r.window_start = f.window_start
    AND r.window_end   = f.window_end
    AND r.region       = f.region;

-- Verify:
-- SELECT * FROM kpi_regional_sales_trends;
