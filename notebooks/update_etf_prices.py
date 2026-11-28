# Databricks notebook source
# /// script
# [tool.databricks.environment]
# environment_version = "6"
# ///
# MAGIC %md
# MAGIC # ETF Daily Closing Prices — Alpha Vantage
# MAGIC Xetra / EUR. Configure a secret scope `finance` with key `alpha-vantage` before running. Schedule after market close, e.g. 23:00 Europe/Vienna. Compact imports up to 100 sessions; older existing rows are preserved.

# COMMAND ----------

import requests
import math
import yaml

from pyspark.sql import functions as F
from pathlib import Path
from datetime import date, datetime, time
from zoneinfo import ZoneInfo
from time import sleep

# Load configuration
with Path("../config/etfs.yaml").open(encoding="utf-8") as file:
    config = yaml.safe_load(file)

# Load credentials
API_KEY = dbutils.secrets.get(
    scope=config["secrets"]["scope"],
    key=config["secrets"]["key"]
).strip()

if not API_KEY:
    raise RuntimeError("API key is empty.")

# Target table
TABLE = config["target"]["table"]

# Active instruments
ETF_CONFIG = [
    (etf["isin"], etf["ticker"], etf["name"])
    for etf in config["instruments"]
    if etf.get("active", True)
]

# COMMAND ----------

CATALOG, SCHEMA, TABLE_NAME = TABLE.split(".")

spark.sql(f"""
    CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}
""")

spark.sql(f"""
    CREATE TABLE IF NOT EXISTS {TABLE} (
        date DATE NOT NULL,
        isin STRING NOT NULL,
        ticker STRING NOT NULL,
        name STRING NOT NULL,
        close_eur DOUBLE NOT NULL
    )
    USING DELTA
""")

# COMMAND ----------

def fetch_prices(ticker):

    response = requests.get(
        "https://www.alphavantage.co/query",
        params={
            "function": config["source"]["function"],
            "symbol": ticker,
            "outputsize": config["source"]["outputsize"],
            "apikey": API_KEY
        },
        timeout=30
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"HTTP error {response.status_code} for {ticker}"
        )

    data = response.json()

    if "Time Series (Daily)" not in data:
        raise RuntimeError(
            f"No daily price data received for {ticker}"
        )

    return data["Time Series (Daily)"]

# COMMAND ----------

raw_data = {}

for isin, ticker, name in ETF_CONFIG:

    print(f"Fetching {ticker}...")

    raw_data[isin] = {
        "ticker": ticker,
        "name": name,
        "prices": fetch_prices(ticker)
    }

    sleep(1)

    print(f"{len(raw_data[isin]['prices'])} records received")

# COMMAND ----------

rows = []

for isin, instrument in raw_data.items():
    for price_date, values in instrument["prices"].items():

        close = float(values["4. close"])

        if not math.isfinite(close) or close <= 0:
            raise ValueError(
                f"Invalid closing price for {isin} on {price_date}"
            )

        rows.append({
            "date": date.fromisoformat(price_date),
            "isin": isin,
            "ticker": instrument["ticker"],
            "name": instrument["name"],
            "close_eur": close
        })

# COMMAND ----------

schema = """
    date DATE,
    isin STRING,
    ticker STRING,
    name STRING,
    close_eur DOUBLE
"""

df = spark.createDataFrame(rows, schema=schema)

display(df)

# COMMAND ----------

if df.count() == 0:
    raise RuntimeError("No valid price records available.")

duplicates = (
    df.groupBy("date", "isin")
      .count()
      .filter(F.col("count") > 1)
)

if duplicates.count() > 0:
    raise RuntimeError("Duplicate price records detected.")

expected_isins = {isin for isin, _, _ in ETF_CONFIG}

actual_isins = {
    row["isin"]
    for row in df.select("isin").distinct().collect()
}

if expected_isins != actual_isins:
    raise RuntimeError("Missing instruments in extracted data.")

print("Data validation successful.")

# COMMAND ----------

df.createOrReplaceTempView("incoming_etf_prices")

spark.sql(f"""
    MERGE INTO {TABLE} AS target
    USING incoming_etf_prices AS source

    ON target.date = source.date
    AND target.isin = source.isin

    WHEN MATCHED THEN
        UPDATE SET *

    WHEN NOT MATCHED THEN
        INSERT *
""")

# COMMAND ----------

display(spark.sql(f"""
    SELECT
        isin,
        ticker,
        COUNT(*) AS observations,
        MIN(date) AS first_date,
        MAX(date) AS last_date
    FROM {TABLE}
    GROUP BY isin, ticker
    ORDER BY ticker
"""))