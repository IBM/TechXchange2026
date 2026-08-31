-- =============================================================================
-- STEP A: Inspect the source tables (raw Kafka topics)
-- =============================================================================
-- Lab-2950 : Real-Time Executive KPI Copilot
--
-- WHAT IS THIS?
--   In Confluent Cloud, every Kafka topic in your cluster automatically shows
--   up as a TABLE that Flink SQL can read. So the five topics your Python
--   generator writes to (orders, payments, customers, shipments, refunds)
--   are already queryable here -- you do NOT need to CREATE them.
--
-- HOW TO RUN:
--   Open Confluent Cloud -> your environment -> "Flink" -> open a Workspace
--   that is attached to your Kafka cluster. Paste and run these statements
--   one at a time.
-- =============================================================================

-- 1. List every table Flink can see. You should spot orders, payments,
--    customers, shipments, and refunds in the results.
SHOW TABLES;

-- 2. Look at the columns Confluent inferred for each topic.
--    (These come from the JSON your Python producer sends.)
DESCRIBE orders;
DESCRIBE payments;
DESCRIBE customers;
DESCRIBE shipments;
DESCRIBE refunds;

-- 3. Peek at live data. This is a STREAMING query: it keeps running and shows
--    new rows as your Python generator produces them. Stop it when satisfied.
SELECT * FROM orders;

-- 4. A quick sanity check: are payments arriving with success/failed status?
SELECT
    order_id,
    region,
    amount,
    status,
    payment_method
FROM payments;
