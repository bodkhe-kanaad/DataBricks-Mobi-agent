"""
Metadata agent helpers

Provides utilities to analyze a Spark table, generate human-friendly column
descriptions, and optionally apply those descriptions to the Databricks table
metadata (column comments).

Usage (Databricks notebook):

from src.mobi.metadata_agent import analyze_and_update_table

# dry run - only preview suggestions
analyze_and_update_table(spark, 'vanhack', 'mobi_data', 'silver_trips', sample_limit=5000, dry_run=True)

# apply suggestions
analyze_and_update_table(spark, 'vanhack', 'mobi_data', 'silver_trips', sample_limit=5000, dry_run=False)

Notes:
- This runs Spark operations in your Databricks workspace. Ensure you have
  the right privileges (USE CATALOG, USE SCHEMA, ALTER TABLE or COMMENT ON
  COLUMN privileges) before applying comments.
"""
from __future__ import annotations

from typing import Dict, Iterable, List, Optional

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql import functions as F


def _basic_stats_for_column(sdf: DataFrame, col: str) -> Dict:
    total = sdf.count()
    nulls = sdf.filter(F.col(col).isNull() | (F.col(col) == "")).count()
    null_pct = float(nulls) / max(total, 1)

    distinct = sdf.select(F.countDistinct(F.col(col))).collect()[0][0]

    # Try to get min/max/mean for numeric/timestamp; ignore errors
    min_v = None
    max_v = None
    mean_v = None
    try:
        stats = sdf.select(F.min(F.col(col)), F.max(F.col(col))).collect()[0]
        min_v, max_v = stats[0], stats[1]
    except Exception:
        pass

    try:
        mean_v = sdf.select(F.mean(F.col(col))).collect()[0][0]
    except Exception:
        pass

    sample_vals = [r[0] for r in sdf.select(col).distinct().limit(5).collect()]

    return {
        "column": col,
        "total_rows": total,
        "null_count": nulls,
        "null_pct": null_pct,
        "distinct_count": distinct,
        "min": min_v,
        "max": max_v,
        "mean": mean_v,
        "sample_values": sample_vals,
    }


def _suggest_comment(col_name: str, dtype: str, stats: Dict) -> str:
    """Create a short, useful comment for a column using heuristics."""
    base = []
    # short, one-sentence guidance
    if "timestamp" in dtype or "date" in dtype:
        base.append("Timestamp column")
        if stats.get("min") is not None and stats.get("max") is not None:
            base.append(f"range: {stats['min']} → {stats['max']}")
    elif any(k in dtype for k in ("int", "long", "double", "float", "decimal")):
        base.append("Numeric column")
        if stats.get("min") is not None and stats.get("max") is not None:
            base.append(f"range: {stats['min']} to {stats['max']}")
        if stats.get("mean") is not None:
            base.append(f"avg: {round(stats['mean'], 2)}")
    elif dtype.startswith("string"):
        base.append("Text field")
        if stats.get("distinct_count") == 1:
            base.append("(constant value)")
        elif stats.get("distinct_count") is not None and stats.get("distinct_count") < 50:
            base.append(f"~{stats['distinct_count']} distinct values")
    else:
        base.append(f"Type: {dtype}")

    # common naming heuristics
    name_lower = col_name.lower()
    if any(x in name_lower for x in ("id", "_id", "id_")):
        base.append("Identifier / key")
    if any(x in name_lower for x in ("lat", "lon", "latitude", "longitude")):
        base.append("Geolocation coordinate")
    if any(x in name_lower for x in ("is_", "has_", "flag", "available")):
        base.append("Boolean flag")

    # nullability note
    if stats.get("null_pct", 0) > 0:
        pct = round(stats.get("null_pct", 0) * 100, 1)
        base.append(f"nullable ({pct}% null)")
    else:
        base.append("non-null")

    # examples
    examples = stats.get("sample_values") or []
    if examples:
        ex_repr = ", ".join([str(e) for e in examples[:3]])
        base.append(f"examples: {ex_repr}")

    # join into a compact comment (keep under ~250 chars)
    comment = "; ".join(base)
    if len(comment) > 250:
        comment = comment[:247] + "..."
    return comment


def summarize_table(spark: SparkSession, catalog: str, schema: str, table: str, sample_limit: int = 2000) -> List[Dict]:
    """Return per-column stats for a Unity Catalog table.

    Args:
        spark: SparkSession (Databricks session)
        catalog: catalog name
        schema: schema name
        table: table name
        sample_limit: limit used when sampling distinct values

    Returns:
        list of dicts with stats per column
    """
    full = f"`{catalog}`.`{schema}`.`{table}`"
    sdf = spark.table(full)

    # use full table for counts/aggregates; use .limit(sample_limit) only for sampling distinct
    sampled = sdf.limit(sample_limit).cache()

    results = []
    for field in sdf.schema.fields:
        col = field.name
        dtype = field.dataType.simpleString()

        # use sampled DataFrame for distinct sample values but compute counts on full table
        stats = _basic_stats_for_column(sdf.select(col), col)
        stats["dtype"] = dtype
        results.append(stats)

    sampled.unpersist()
    return results


def analyze_and_update_table(
    spark: SparkSession,
    catalog: str,
    schema: str,
    table: str,
    sample_limit: int = 2000,
    dry_run: bool = True,
) -> List[Dict]:
    """Analyze table and optionally update column comments.

    Returns a list of suggestions (column -> suggested_comment).
    If dry_run is False, attempts to apply comments using `COMMENT ON COLUMN`.
    """
    full = f"`{catalog}`.`{schema}`.`{table}`"
    print(f"Analyzing table {full} (sample_limit={sample_limit})...")

    sdf = spark.table(full)
    schema_fields = {f.name: f.dataType.simpleString() for f in sdf.schema.fields}

    # For each column compute stats and suggestion
    suggestions = []
    for field_name, dtype in schema_fields.items():
        stats = _basic_stats_for_column(sdf.select(field_name), field_name)
        comment = _suggest_comment(field_name, dtype, stats)
        suggestions.append({"column": field_name, "dtype": dtype, "suggested_comment": comment, "stats": stats})

    # Print summary
    for s in suggestions:
        print(f"- {s['column']} ({s['dtype']}): {s['suggested_comment']}")

    if dry_run:
        print("Dry run: no changes made. Set dry_run=False to apply comments.")
        return suggestions

    print("Applying comments to table metadata...")
    for s in suggestions:
        col = s["column"]
        comment = s["suggested_comment"].replace("'", "\'")
        # Use COMMENT ON COLUMN syntax; Databricks supports this form in SQL
        sql = f"COMMENT ON COLUMN {full}.{col} IS '{comment}'"
        try:
            spark.sql(sql)
        except Exception as e:
            # If COMMENT ON COLUMN fails, try ALTER TABLE ... CHANGE COLUMN ... COMMENT
            alt_sql = f"ALTER TABLE {full} CHANGE COLUMN `{col}` `{col}` {s['stats'].get('dtype', 'STRING')} COMMENT '{comment}'"
            try:
                spark.sql(alt_sql)
            except Exception as e2:
                print(f"Failed to set comment for {col}: {e} / {e2}")
    print("Done applying comments.")
    return suggestions


if __name__ == "__main__":
    print("This module is intended to be used from a Databricks notebook. See the docstring for usage.")
