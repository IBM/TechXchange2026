-- =============================================================================
-- KPI 3: PAYMENT FAILURE RATE
-- =============================================================================
-- Lab-2950 : Real-Time Executive KPI Copilot
--
-- BUSINESS QUESTION:
--   "What percentage of payment attempts are failing right now? A spike could
--    mean a broken gateway or a fraud attack -- executives want to know fast."
--
-- HOW IT WORKS:
--   Per 1-minute window: total attempts, failed attempts, and
--   failure_rate_pct = failed / total * 100. We multiply by 100.0 (decimal) so
--   the division is decimal arithmetic (integer division would truncate to 0).
--
-- RESUMABLE PATTERN: CREATE TABLE IF NOT EXISTS (once) + INSERT INTO (the job).
--   Re-run STATEMENT 2 to resume after an idle stop, without "table already
--   exists".
--
-- RUN STATEMENT 1 ONCE, THEN STATEMENT 2 (re-run STATEMENT 2 to resume).
-- =============================================================================


-- ---- STATEMENT 1 : create the output table (run once) ----------------------
CREATE TABLE IF NOT EXISTS kpi_payment_failure_rate (
    window_start      TIMESTAMP(3),
    window_end        TIMESTAMP(3),
    region            STRING,
    total_payments    BIGINT,
    failed_payments   BIGINT,
    failure_rate_pct  DECIMAL(5, 2)
);


-- ---- STATEMENT 2 : the continuous job (re-run this to resume) ---------------
INSERT INTO kpi_payment_failure_rate
SELECT
    window_start,
    window_end,
    region,
    COUNT(*)                                             AS total_payments,
    SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END)   AS failed_payments,
    CAST(
        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) * 100.0
        / COUNT(*)
    AS DECIMAL(5, 2))                                     AS failure_rate_pct
FROM TABLE(
    TUMBLE(TABLE payments, DESCRIPTOR(`$rowtime`), INTERVAL '1' MINUTE)
)
GROUP BY
    window_start,
    window_end,
    region;

-- Verify:
-- SELECT * FROM kpi_payment_failure_rate;
