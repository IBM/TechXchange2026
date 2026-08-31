# =============================================================================
# DIAGNOSTIC / TEST SCRIPT - NOT part of the normal lab flow.
# =============================================================================
# Purpose: prove the WRITE half of the pipeline in isolation - that the Spark
# engine can create a native Iceberg table on IBM COS and Presto can read it.
# It writes a tiny throwaway table `iceberg_catalog.demo.hello`.
#
# The PRODUCTION job is  spark/kpi_to_native_iceberg.py  (reads Tableflow KPIs
# and writes the real native tables). Run THIS file only if you need to debug
# the Spark->COS->Presto write path.
#
# Fill in the two values below, upload to COS, and submit on the Spark engine
# with:  spark.hadoop.wxd.apiKey = Basic <base64 of ibmlhapikey_<userid>:<apikey>>
# =============================================================================
from pyspark.sql import SparkSession

def main():
    # 1. Start a Spark session (Hive support = talk to watsonx.data catalog)
    spark = (
        SparkSession.builder
        .appName("validate-iceberg-cos")
        .enableHiveSupport()
        .getOrCreate()
    )

    catalog = "iceberg_catalog"          # your Iceberg catalog (Spark + Presto engines)
    bucket  = "<YOUR_DATA_BUCKET>"       # the COS bucket behind that catalog

    # 2. The 4 core statements (what you correctly counted)
    spark.sql(f"CREATE DATABASE IF NOT EXISTS {catalog}.demo LOCATION 's3a://{bucket}/'")
    spark.sql(f"CREATE TABLE IF NOT EXISTS {catalog}.demo.hello "
              f"(region STRING, revenue DECIMAL(10,2)) USING iceberg")
    spark.sql(f"INSERT INTO {catalog}.demo.hello "
              f"VALUES ('Europe', 123.45), ('Asia Pacific', 67.89)")
    spark.sql(f"SELECT * FROM {catalog}.demo.hello").show()

    spark.stop()

if __name__ == '__main__':
    main()
