# Databricks notebook source
# MAGIC %md
# MAGIC # Mobi Vancouver — Station-level Next-day Demand (Tutorial)
# MAGIC
# MAGIC In this lab you'll predict next-day pickups per station using the UC tables
# MAGIC created by `01_data.ipynb`. You'll:
# MAGIC
# MAGIC - Build a silver aggregate `silver_station_daily` (per-station, per-day trips)
# MAGIC - Create simple time-series features (lag and rolling mean)
# MAGIC - Train baseline models (Linear Regression, Random Forest) with scikit-learn
# MAGIC - Evaluate and write next-day predictions to `silver_station_daily_predictions`

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 0 — Minimal dependencies
# MAGIC Installs scikit-learn (and mlflow if you want autologging). Keep this lightweight for hackathon speed.

# COMMAND ----------

# MAGIC %pip install -q scikit-learn mlflow

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 1 — Configure Unity Catalog location
# MAGIC Reads `catalog` and `schema` from `config.yaml` using `mlflow.ModelConfig`, then exposes widgets so the
# MAGIC SQL below can reference `${catalog}` and `${schema}`.

# COMMAND ----------

import mlflow
config = mlflow.models.ModelConfig(development_config="config.yaml")

# Widgets (Databricks)
dbutils.widgets.text("catalog", config.get("catalog") or "hive_metastore")
dbutils.widgets.text("schema",  config.get("schema")  or "default")

CATALOG = dbutils.widgets.get("catalog")
SCHEMA = dbutils.widgets.get("schema")
print(f"Using catalog.schema: {CATALOG}.{SCHEMA}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 2 — Load trips and stations (from UC)
# MAGIC We use the curated `silver_trips` table if available (has `departure_station_id`/`return_station_id`).
# MAGIC If it doesn't exist yet, run `01_data.ipynb` to build bronze/silver tables first.

# COMMAND ----------

from pyspark.sql import functions as F

trips_tbl = f"`{CATALOG}`.`{SCHEMA}`.`silver_trips`"
stations_tbl = f"`{CATALOG}`.`{SCHEMA}`.`bronze_stations`"

try:
    trips_sdf = spark.table(trips_tbl)
except Exception as e:
    raise RuntimeError(
        "Missing `silver_trips`. Please run 01_data.ipynb to materialize bronze/silver tables."
    ) from e

stations_sdf = spark.table(stations_tbl)

print(f"Trips rows: {trips_sdf.count():,}")
print(f"Stations:   {stations_sdf.count():,}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 3 — Build silver_station_daily
# MAGIC Per station and per date:
# MAGIC - trips_out: count of departures (from `departure_station_id`)
# MAGIC - trips_in: count of returns (from `return_station_id`)
# MAGIC - net_flow: trips_out - trips_in

# COMMAND ----------

# Aggregate departures (out) and returns (in)
station_out = (
    trips_sdf
    .select(
        F.col("departure_station_id").cast("string").alias("station_id"),
        F.to_date("departure_time").alias("date"),
    )
    .groupBy("station_id", "date")
    .agg(F.count(F.lit(1)).alias("trips_out"))
)

station_in = (
    trips_sdf
    .select(
        F.col("return_station_id").cast("string").alias("station_id"),
        F.to_date("return_time").alias("date"),
    )
    .groupBy("station_id", "date")
    .agg(F.count(F.lit(1)).alias("trips_in"))
)

station_daily = (
    station_out
    .join(station_in, on=["station_id", "date"], how="full_outer")
    .na.fill({"trips_out": 0, "trips_in": 0})
    .withColumn("net_flow", F.col("trips_out") - F.col("trips_in"))
)

(
    station_daily.write.format("delta").mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"`{CATALOG}`.`{SCHEMA}`.`silver_station_daily`")
)

print("✓ silver_station_daily written")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 4 — Feature engineering (pandas) and time-based split
# MAGIC Create simple features per station: day-of-week, is_weekend, lag-1, rolling-7 mean.
# MAGIC Use the last 30 days as the test window; everything before is train.

# COMMAND ----------

import pandas as pd
import numpy as np

sdf = spark.table(f"`{CATALOG}`.`{SCHEMA}`.`silver_station_daily`")
pdf = sdf.toPandas()

pdf["date"] = pd.to_datetime(pdf["date"])
pdf = pdf.sort_values(["station_id", "date"]).reset_index(drop=True)

# Calendar features
pdf["dow"] = pdf["date"].dt.weekday.astype(int)  # 0=Mon..6=Sun
pdf["is_weekend"] = pdf["dow"].isin([5, 6]).astype(int)

# Lag/rolling features per station (shift(1) to avoid peeking at the target day)
pdf["lag_1"] = pdf.groupby("station_id")["trips_out"].shift(1)
pdf["rolling_7_mean"] = (
    pdf.groupby("station_id")["trips_out"]
    .transform(lambda s: s.shift(1).rolling(window=7, min_periods=1).mean())
)

# Drop rows without minimal history for modeling
features = ["station_id", "dow", "is_weekend", "lag_1", "rolling_7_mean"]
target = "trips_out"
model_df = pdf.dropna(subset=["lag_1", "rolling_7_mean"]).copy()

# Time-based split: last 30 days = test
max_date = model_df["date"].max()
test_start = max_date - pd.Timedelta(days=29)
train_mask = model_df["date"] < test_start
test_mask = model_df["date"] >= test_start

X_train = model_df.loc[train_mask, features]
y_train = model_df.loc[train_mask, target]
X_test  = model_df.loc[test_mask,  features]
y_test  = model_df.loc[test_mask,  target]

print(
    f"Train rows: {len(X_train):,}  |  Test rows: {len(X_test):,}  "
    f"|  Stations: {model_df['station_id'].nunique()}"
)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 5 — Train baseline models
# MAGIC We use scikit-learn pipelines:
# MAGIC - OneHotEncoder for categorical (`station_id`, `dow`)
# MAGIC - Numeric passthrough for (`is_weekend`, `lag_1`, `rolling_7_mean`)

# COMMAND ----------

from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import OneHotEncoder
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_absolute_error, mean_squared_error

categorical_cols = ["station_id", "dow"]
numeric_cols = ["is_weekend", "lag_1", "rolling_7_mean"]

preprocess = ColumnTransformer(
    transformers=[
        ("num", "passthrough", numeric_cols),
        ("cat", OneHotEncoder(handle_unknown="ignore", sparse=False), categorical_cols),
    ]
)

lr_pipeline = Pipeline(
    steps=[
        ("preprocess", preprocess),
        ("model", LinearRegression()),
    ]
)

rf_pipeline = Pipeline(
    steps=[
        ("preprocess", preprocess),
        ("model", RandomForestRegressor(n_estimators=200, random_state=42)),
    ]
)

# Optional MLflow autolog
try:
    import mlflow
    import mlflow.sklearn
    mlflow.sklearn.autolog()
except Exception:
    mlflow = None

# Fit models
if mlflow:
    with mlflow.start_run(run_name="LinearRegression"):
        lr_pipeline.fit(X_train, y_train)
    with mlflow.start_run(run_name="RandomForest"):
        rf_pipeline.fit(X_train, y_train)
else:
    lr_pipeline.fit(X_train, y_train)
    rf_pipeline.fit(X_train, y_train)

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 6 — Evaluate
# MAGIC Report R², MAE, RMSE on the time-based test window.

# COMMAND ----------

def evaluate(model_name: str, pipeline: Pipeline):
    y_pred = pipeline.predict(X_test)
    r2 = r2_score(y_test, y_pred)
    mae = mean_absolute_error(y_test, y_pred)
    rmse = mean_squared_error(y_test, y_pred, squared=False)
    print(f"{model_name:>14} → R²={r2:.3f} | MAE={mae:.2f} | RMSE={rmse:.2f}")
    return {"r2": r2, "mae": mae, "rmse": rmse}

scores_lr = evaluate("LinearRegression", lr_pipeline)
scores_rf = evaluate("RandomForest",    rf_pipeline)

best_name = "RandomForest" if scores_rf["r2"] >= scores_lr["r2"] else "LinearRegression"
best_model = rf_pipeline if best_name == "RandomForest" else lr_pipeline
print(f"\nBest model: {best_name}")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Step 7 — Predict next day per station and save
# MAGIC Build next-day feature rows from the most recent history and write predictions to UC:
# MAGIC - `silver_station_daily_predictions` with columns: station_id, date, predicted_trips_out

# COMMAND ----------

# Build next-day features per station from recent history
last_by_station = (
    pdf.sort_values(["station_id", "date"])
    .groupby("station_id")
    .agg(
        last_date=("date", "max"),
        last_trips=("trips_out", "last"),
    )
    .reset_index()
)

# Rolling-7 mean per station using last 7 observations
rolling7 = (
    pdf.sort_values(["station_id", "date"])
    .groupby("station_id")["trips_out"]
    .apply(lambda s: s.tail(7).mean())
    .rename("rolling_7_mean")
    .reset_index()
)

next_df = last_by_station.merge(rolling7, on="station_id", how="left")
next_df["date"] = next_df["last_date"] + pd.Timedelta(days=1)
next_df["dow"] = next_df["date"].dt.weekday.astype(int)
next_df["is_weekend"] = next_df["dow"].isin([5, 6]).astype(int)
next_df["lag_1"] = next_df["last_trips"].astype(float)
next_df["rolling_7_mean"] = next_df["rolling_7_mean"].fillna(next_df["lag_1"])

pred_features = next_df[["station_id", "dow", "is_weekend", "lag_1", "rolling_7_mean"]]
next_df["predicted_trips_out"] = best_model.predict(pred_features).clip(min=0)

preds_out = next_df[["station_id", "date", "predicted_trips_out"]]
preds_sdf = spark.createDataFrame(preds_out)

(
    preds_sdf.write.format("delta").mode("overwrite")
    .option("overwriteSchema", True)
    .saveAsTable(f"`{CATALOG}`.`{SCHEMA}`.`silver_station_daily_predictions`")
)

print("✓ silver_station_daily_predictions written")

# COMMAND ----------

# MAGIC %md
# MAGIC ## Next steps
# MAGIC - Add external features: weather, holidays, events
# MAGIC - Move to hourly granularity and predict within-day demand peaks
# MAGIC - Persist a model with MLflow and serve it for real-time inference


