-- =============================================================================
-- KPI 2: ORDER THROUGHPUT (orders per minute)
-- =============================================================================
-- Lab-2950 : Real-Time Executive KPI Copilot
--
-- BUSINESS QUESTION:
--   "How many orders are we taking per minute, and what is their total value?"
--
-- HOW IT WORKS:
--   Count every order (regardless of payment outcome) in 1-minute tumbling
--   windows, per region. Measures demand/traffic (vs. revenue = collected money).
--
-- RESUMABLE PATTERN: CREATE TABLE IF NOT EXISTS (once) + INSERT INTO (the job).
--   Re-run STATEMENT 2 to resume after Confluent auto-stops an idle statement,
--   without hitting "table already exists". Money columns are CAST to
--   DECIMAL(12,2) (source `amount` is DOUBLE).
--
-- RUN STATEMENT 1 ONCE, THEN STATEMENT 2 (re-run STATEMENT 2 to resume).
-- =============================================================================


-- ---- STATEMENT 1 : create the output table (run once) ----------------------
CREATE TABLE IF NOT EXISTS kpi_order_throughput (
    window_start           TIMESTAMP(3),
    window_end             TIMESTAMP(3),
    region                 STRING,
    order_count            BIGINT,
    gross_order_value_usd  DECIMAL(12, 2),
    avg_order_value_usd    DECIMAL(12, 2)
);


-- ---- STATEMENT 2 : the continuous job (re-run this to resume) ---------------
INSERT INTO kpi_order_throughput
SELECT
    window_start,
    window_end,
    region,
    COUNT(*)                              AS order_count,
    CAST(SUM(amount) AS DECIMAL(12, 2))   AS gross_order_value_usd,
    CAST(AVG(amount) AS DECIMAL(12, 2))   AS avg_order_value_usd
FROM TABLE(
    TUMBLE(TABLE orders, DESCRIPTOR(`$rowtime`), INTERVAL '1' MINUTE)
)
GROUP BY
    window_start,
    window_end,
    region;

-- Verify:
-- SELECT * FROM kpi_order_throughput;
