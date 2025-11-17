![Mobi Vancouver Bike Share banner](img/header.png)

# 🚴‍♂️ Mobi Vancouver Bike Share — Databricks Hackathon Toolkit

This repository provides a lightweight toolkit to help hackathon teams explore and build with Vancouver’s **Mobi by Rogers** bike share data. Everything here is designed for **Databricks Serverless**, **Unity Catalog**, and **Databricks Vector Search**, with strong emphasis on **Genie rooms** as your team’s primary agentic interface.

Your goal:
**Build an intelligent, agent-powered solution that reasons about bike trips, stations, or site content using Databricks-native tools.**
The repo gives you the raw ingredients — you bring the orchestration, automation, and machine learning.

---

# 🔑 What’s Included

### **Data ingestion + standardization (Notebook: 01_data.ipynb)**
Pulls historical monthly trip CSVs from Mobi’s public site, writes them into UC Volumes, and creates **bronze and silver Delta tables**. This notebook gives each team a consistent, queryable base dataset.

### **Utility tools + feature preparation (Notebook: 02_tools.ipynb)**
Includes helper functions, small utilities, scraping support, and the building blocks for generating embeddings, text features, or structured metadata.

### **Retrieval workflows + Vector Search (Notebook: 03_vector_search.ipynb)**
Demonstrates how to work with Databricks Vector Search, create an index from scraped Mobi content, and issue semantic searches. This directly supports Genie room workflows and Q&A agents.

---
