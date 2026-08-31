-- =============================================================================
-- KPI 4: REGIONAL SALES TRENDS  (view + CREATE TABLE + INSERT INTO)
-- =============================================================================
-- Lab-2950 : Real-Time Executive KPI Copilot
--
-- BUSINESS QUESTION:
--   "Over a rolling 5-minute view, how do regions compare on net sales
--    (revenue minus refunds), order volume, and unique buyers?"
--
-- RUN THE THREE STATEMENTS ONE AT A TIME:
--   STATEMENT 1: CREATE VIEW  - blends payments + refunds into one tagged stream
--                (carries the event-time column $rowtime through as rt).
--   STATEMENT 2: CREATE TABLE IF NOT EXISTS - the output table (run once).
--   STATEMENT 3: INSERT INTO ... SELECT - the continuous windowed job.
--
-- RESUMABLE PATTERN: if Confluent auto-stops the job, just RE-RUN STATEMENT 3
--   (and STATEMENT 1 if the view was dropped). You will never hit "table
--   already exists" because CREATE TABLE is separate from the job.
--
-- Notes: Confluent Flink runs a single statement per execution and does not
--   allow an inline subquery inside TUMBLE(), hence the VIEW. The VIEW itself is
--   just a definition (not an always-on job); only STATEMENT 3 runs continuously.
-- =============================================================================


-- ---- STATEMENT 1 : the blended stream as a VIEW (re-create if dropped) ------
CREATE VIEW IF NOT EXISTS sales_events AS
    SELECT `$rowtime` AS rt, region, customer_id, amount, 'revenue' AS kind
    FROM payments
    WHERE status = 'success'
    UNION ALL
    SELECT `$rowtime` AS rt, region, customer_id, amount, 'refund' AS kind
    FROM refunds;


-- ---- STATEMENT 2 : create the output table (run once) ----------------------
CREATE TABLE IF NOT EXISTS kpi_regional_sales_trends (
    window_start      TIMESTAMP(3),
    window_end        TIMESTAMP(3),
    region            STRING,
    orders_paid       BIGINT,
    unique_customers  BIGINT,
    revenue_usd       DECIMAL(12, 2),
    refund_count      BIGINT,
    refund_usd        DECIMAL(12, 2),
    net_revenue_usd   DECIMAL(12, 2)
);


-- ---- STATEMENT 3 : the continuous job (re-run this to resume) ---------------
INSERT INTO kpi_regional_sales_trends
SELECT
    window_start,
    window_end,
    region,
    SUM(CASE WHEN kind = 'revenue' THEN 1 ELSE 0 END)                 AS orders_paid,
    COUNT(DISTINCT CASE WHEN kind = 'revenue' THEN customer_id END)   AS unique_customers,
    CAST(SUM(CASE WHEN kind = 'revenue' THEN amount ELSE 0 END) AS DECIMAL(12, 2)) AS revenue_usd,
    SUM(CASE WHEN kind = 'refund'  THEN 1 ELSE 0 END)                 AS refund_count,
    CAST(SUM(CASE WHEN kind = 'refund'  THEN amount ELSE 0 END) AS DECIMAL(12, 2)) AS refund_usd,
    CAST(
        SUM(CASE WHEN kind = 'revenue' THEN amount ELSE 0 END)
      - SUM(CASE WHEN kind = 'refund'  THEN amount ELSE 0 END)
    AS DECIMAL(12, 2))                                               AS net_revenue_usd
FROM TABLE(
    TUMBLE(TABLE sales_events, DESCRIPTOR(rt), INTERVAL '5' MINUTE)
)
GROUP BY
    window_start,
    window_end,
    region;

-- Verify (after a 5-minute window closes):
-- SELECT * FROM kpi_regional_sales_trends;
