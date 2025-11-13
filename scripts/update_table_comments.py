"""Utility script to run the metadata agent from a Databricks notebook or CLI.

Example usage (Databricks notebook):

from pyspark.sql import SparkSession
spark = SparkSession.builder.getOrCreate()
import sys
sys.path.insert(0, '/Workspace/Repos/<your-repo-path>/mobi_agent_starter/src')
from mobi.metadata_agent import analyze_and_update_table

# Preview comments
analyze_and_update_table(spark, 'vanhack', 'mobi_data', 'silver_trips', sample_limit=2000, dry_run=True)

# Apply comments
analyze_and_update_table(spark, 'vanhack', 'mobi_data', 'silver_trips', sample_limit=2000, dry_run=False)

This script is intentionally minimal — it's meant to be copied into a
Databricks notebook (or executed in a workspace with access to the repo).
Ensure the repo `src` path is on sys.path when running in a notebook.
"""

if __name__ == "__main__":
    print("This script is intended to be run from a Databricks notebook. See the file header for usage.")
