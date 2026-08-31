-- =============================================================================
-- KPI 1: REVENUE PER MINUTE
-- =============================================================================
-- Lab-2950 : Real-Time Executive KPI Copilot
--
-- BUSINESS QUESTION:
--   "How much money are we successfully collecting each minute, per region?"
--
-- HOW IT WORKS (plain English):
--   Revenue = the sum of SUCCESSFUL payments, grouped into 1-minute tumbling
--   windows per region. Flink recomputes this continuously as payments arrive.
--
-- RESUMABLE PATTERN (important):
--   Confluent Cloud auto-stops idle Flink statements. To make resuming easy we
--   split this into TWO statements:
--     STATEMENT 1: CREATE TABLE IF NOT EXISTS  (defines the output table ONCE)
--     STATEMENT 2: INSERT INTO ... SELECT       (the continuous streaming job)
--   If a statement is stopped, just RE-RUN STATEMENT 2 - the table already
--   exists, so you never hit "table already exists". (A one-shot
--   CREATE TABLE ... AS SELECT would fail on resume because the table persists
--   after the job stops.)
--
-- RUN STATEMENT 1 ONCE, THEN STATEMENT 2 (and re-run STATEMENT 2 to resume).
-- =============================================================================


-- ---- STATEMENT 1 : create the output table (run once) ----------------------
CREATE TABLE IF NOT EXISTS kpi_revenue_per_minute (
    window_start         TIMESTAMP(3),
    window_end           TIMESTAMP(3),
    region               STRING,
    successful_payments  BIGINT,
    revenue_usd          DECIMAL(12, 2)
);


-- ---- STATEMENT 2 : the continuous job (re-run this to resume) ---------------
INSERT INTO kpi_revenue_per_minute
SELECT
    window_start,
    window_end,
    region,
    COUNT(*)                          AS successful_payments,
    CAST(SUM(amount) AS DECIMAL(12, 2)) AS revenue_usd
FROM TABLE(
    TUMBLE(TABLE payments, DESCRIPTOR(`$rowtime`), INTERVAL '1' MINUTE)
)
WHERE status = 'success'
GROUP BY
    window_start,
    window_end,
    region;

-- Verify:
-- SELECT * FROM kpi_revenue_per_minute;
