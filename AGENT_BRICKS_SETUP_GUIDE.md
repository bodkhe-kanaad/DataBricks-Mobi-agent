# 🚀 Agent Bricks Setup Guide - Mobi Vancouver Bike Share

## 📋 Repository Overview

This repository provides a complete toolkit for building AI agents in Agent Bricks using Vancouver's Mobi bike share data. The project processes historical trip data, real-time station information, and website content to create a rich knowledge base for intelligent agents.

**Catalog Name:** `vanhack`  
**Schema Name:** `mobi_data`

---

## 🎯 What This Repository Does

1. **Data Ingestion**: Downloads and processes ~7.6M historical bike trips (2018-2025)
2. **Station Management**: Fetches live station data via GBFS API
3. **Content Scraping**: Extracts Mobi website content for semantic search
4. **Data Transformation**: Creates Bronze → Silver table pipeline
5. **Vector Search**: Builds semantic search capabilities for AI agents
6. **SQL Tools**: Creates reusable functions for agent workflows

---

## 📊 Data Architecture

### **Bronze Layer** (Raw Data)
- `bronze_trips` - Raw trip history
- `bronze_stations` - Station metadata and status
- `bronze_site` - Scraped website content

### **Silver Layer** (Cleaned & Enriched)
- `silver_trips` - Normalized trip data with proper types, timestamps, and station IDs
- `silver_stations` - Clean station reference with geolocation
- `silver_site` - Structured website content ready for embeddings

### **Tools Layer** (Agent Functions)
- `recent_trips_by_station(station_id)` - Get latest trips from a station
- `live_station_status(station_id)` - Real-time availability data
- `nearby_stations(lat, lon, radius_km)` - Find stations within radius
- `site_search(query)` - Semantic search over documentation

---

## 🛠️ Step-by-Step Setup Guide

### **Phase 1: Databricks Preparation**

#### Step 1: Create Unity Catalog
```sql
-- In Databricks SQL Editor or Notebook
CREATE CATALOG IF NOT EXISTS vanhack;
```

**Why**: Unity Catalog is the governance layer in Databricks. It organizes all your data assets (tables, volumes, functions) under a single namespace.

**What happens**: Creates the top-level container for all your Mobi project data.

---

#### Step 2: Verify Configuration
Open `config.yaml` and confirm:
```yaml
catalog: vanhack
schema: mobi_data
raw_data_vol: raw_data
run_web_scrape: false
scrape_url: https://www.mobibikes.ca/en/
scrape_max_depth: 5
scrape_delay: 0.1
shuffle_partitions: 64
overwrite_downloads: false
```

**Note**: 
- `overwrite_downloads: false` uses pre-bundled data (faster for hackathon)
- Set to `true` if you want fresh downloads

---

### **Phase 2: Data Ingestion & Processing**

#### Step 3: Run 01_data.ipynb - Data Pipeline
This is the **most critical step**. It creates your entire data foundation.

**What it does:**
1. Creates schema `vanhack.mobi_data`
2. Creates volume `vanhack.mobi_data.raw_data`
3. Downloads/loads trip CSVs (or uses bundled data)
4. Fetches station data from GBFS API
5. Scrapes Mobi website content
6. Creates Bronze tables (raw data)
7. Creates Silver tables (cleaned, ML-ready data)

**Expected Output:**
- ✅ ~7.6M trips in `silver_trips`
- ✅ ~200+ stations in `silver_stations`
- ✅ ~50+ pages in `silver_site`

**Time**: 10-15 minutes (depending on compute)

**Key Transformations:**
- Standardizes column names
- Parses timestamps correctly
- Normalizes station names
- Creates station IDs for joins
- Adds derived fields (distance_km, electric bike flags)

---

#### Step 4: Run 02_tools.ipynb - Create SQL Functions
Creates reusable agent tools as SQL functions.

**What it does:**
1. Creates `recent_trips_by_station(station_id)` - SQL table function
2. Creates `live_station_status(station_id)` - Python UDTF calling GBFS API
3. Creates `nearby_stations(lat, lon, radius_km)` - Geospatial search with haversine

**Why this matters:**
- These functions can be called from SQL, Python, or Genie rooms
- They encapsulate complex logic into simple interfaces
- Perfect for agent tools that need real-time data

**Test the tools:**
```sql
-- Example 1: Recent trips from station 0152
SELECT * FROM recent_trips_by_station('0152');

-- Example 2: Live status of station 0152
SELECT * FROM live_station_status('0152');

-- Example 3: Stations near Downtown Vancouver
SELECT * FROM nearby_stations(49.2827, -123.1207, 1.0);
```

---

#### Step 5: Run 03_vector_search.ipynb - Build Semantic Search
Creates a vector search index for agent question-answering.

**What it does:**
1. Enables Change Data Feed on `silver_site`
2. Creates Vector Search endpoint: `mobi_vs_endpoint`
3. Builds index: `vanhack.mobi_data.mobi_site_index`
4. Creates `site_search(query)` function for semantic queries

**Why this matters:**
- Allows agents to answer questions about Mobi policies, pricing, rules
- Uses Databricks' built-in embeddings (no external API needed)
- Powers RAG (Retrieval Augmented Generation) workflows

**Test the search:**
```sql
SELECT * FROM vanhack.mobi_data.site_search('What is Mobi?');
SELECT * FROM vanhack.mobi_data.site_search('How do I rent a bike?');
SELECT * FROM vanhack.mobi_data.site_search('Trip pricing and fares');
```

---

### **Phase 3: Agent Bricks Integration**

#### Step 6: Export Data for Agent Bricks

**Option A: Export as CSV/Parquet Files**
```python
# In a Databricks notebook
# Export silver tables for Agent Bricks ingestion

# Export trips
spark.table("vanhack.mobi_data.silver_trips") \
    .write.mode("overwrite") \
    .parquet("/Volumes/vanhack/mobi_data/raw_data/export/silver_trips.parquet")

# Export stations
spark.table("vanhack.mobi_data.silver_stations") \
    .write.mode("overwrite") \
    .csv("/Volumes/vanhack/mobi_data/raw_data/export/silver_stations.csv", header=True)

# Download these files from Databricks to local machine
```

**Option B: Use Databricks SQL Connector**
If Agent Bricks supports SQL connectors, provide:
- **Workspace URL**: Your Databricks workspace URL
- **Access Token**: Create a personal access token in Databricks
- **Catalog**: `vanhack`
- **Schema**: `mobi_data`
- **Tables**: `silver_trips`, `silver_stations`, `silver_site`

---

#### Step 7: Create Agent Bricks Catalog

In Agent Bricks platform:

1. **Create New Catalog**
   - Name: `vanhack`
   - Description: "Vancouver Mobi Bike Share Data - Historical trips, station data, and documentation"

2. **Add Data Sources**
   
   **Source 1: Trip History**
   - Name: `mobi_trips`
   - Type: CSV/Parquet/SQL
   - Source: `silver_trips` table or exported file
   - Key Fields:
     - `trip_id` (Primary Key)
     - `departure_time`
     - `return_time`
     - `departure_station_name`, `return_station_name`
     - `duration_sec`
     - `covered_distance_km`
     - `is_electric_bike`
     - `membership_type`

   **Source 2: Station Data**
   - Name: `mobi_stations`
   - Type: CSV/Parquet/SQL
   - Source: `silver_stations` table or exported file
   - Key Fields:
     - `station_id` (Primary Key)
     - `station_name`
     - `lat`, `lon`
     - `capacity`
     - `num_bikes_available`
     - `num_docks_available`

   **Source 3: Documentation**
   - Name: `mobi_docs`
   - Type: Text/Markdown
   - Source: `silver_site` table or exported markdown files
   - Key Fields:
     - `site_page_id`
     - `title`
     - `url`
     - `content_md`

---

#### Step 8: Configure Agent Tools in Agent Bricks

Create the following tools for your agents:

**Tool 1: Find Recent Trips**
```
Tool Name: get_recent_trips
Description: Get the 10 most recent trips from a specific station
Input: station_id (string)
Query: SELECT * FROM recent_trips_by_station('{station_id}')
```

**Tool 2: Check Station Status**
```
Tool Name: check_station_availability
Description: Get real-time bike and dock availability for a station
Input: station_id (string)
API/Query: SELECT * FROM live_station_status('{station_id}')
```

**Tool 3: Find Nearby Stations**
```
Tool Name: find_nearby_stations
Description: Find all bike stations within a certain radius of coordinates
Inputs: 
  - latitude (float)
  - longitude (float)
  - radius_km (float)
Query: SELECT * FROM nearby_stations({latitude}, {longitude}, {radius_km})
```

**Tool 4: Search Documentation**
```
Tool Name: search_mobi_docs
Description: Search Mobi documentation for policies, pricing, and information
Input: query (string)
Query: SELECT * FROM site_search('{query}')
```

---

### **Phase 4: Create Your First Agent**

#### Step 9: Design Agent Persona

**Example Agent: "Mobi Assistant"**

**System Prompt:**
```
You are Mobi Assistant, an expert on Vancouver's Mobi bike share system. 
You help users with:
- Finding available bikes and stations
- Understanding trip patterns and statistics
- Explaining Mobi policies, pricing, and rules
- Recommending optimal stations based on location

You have access to:
- 7.6 million historical bike trips (2018-2025)
- Real-time station availability data
- Complete Mobi documentation

Always provide accurate, helpful information. When discussing availability, 
check real-time data. When explaining policies, reference official documentation.
```

**Capabilities:**
- Answer questions about trip history
- Check real-time bike availability
- Find nearest stations to a location
- Explain pricing and membership options
- Analyze usage patterns

---

#### Step 10: Test Agent Workflows

**Test Queries:**

1. **Basic Information**
   - "What is Mobi?"
   - "How much does it cost to rent a bike?"
   - "What's the difference between membership types?"

2. **Real-Time Queries**
   - "Are there bikes available at station 0152?"
   - "Find me stations near downtown Vancouver (49.2827, -123.1207)"
   - "Which stations have the most bikes right now?"

3. **Historical Analysis**
   - "What were the busiest months for bike rentals in 2024?"
   - "Which stations are most popular?"
   - "What percentage of trips use electric bikes?"

4. **Combined Queries**
   - "I'm at coordinates 49.2827, -123.1207. Find the nearest station with available bikes."
   - "Show me trip patterns from Stanley Park station in summer 2024"
   - "What's the average trip duration for electric vs regular bikes?"

---

## 🎨 Advanced Agent Use Cases

### Use Case 1: Trip Planning Agent
**Goal**: Help users plan optimal bike trips

**Features:**
- Check current availability at start/end stations
- Suggest alternative nearby stations if needed
- Estimate trip duration based on historical data
- Warn about high-demand times

**Data Used:**
- `silver_trips` (historical patterns)
- `live_station_status()` (real-time availability)
- `nearby_stations()` (alternatives)

---

### Use Case 2: System Analytics Agent
**Goal**: Provide insights for Mobi operations team

**Features:**
- Identify stations that are frequently full/empty
- Predict demand patterns by time/location
- Analyze electric vs regular bike usage
- Generate rebalancing recommendations

**Data Used:**
- `silver_trips` (usage patterns)
- `silver_stations` (capacity data)
- Time-series analysis

---

### Use Case 3: Customer Support Agent
**Goal**: Answer user questions about policies and troubleshooting

**Features:**
- Search documentation for policies
- Explain membership benefits
- Troubleshoot common issues
- Provide pricing information

**Data Used:**
- `site_search()` (documentation retrieval)
- `silver_trips` (usage examples)

---

## 📈 Data Schema Reference

### silver_trips Table
| Column | Type | Description |
|--------|------|-------------|
| trip_id | BIGINT | Unique trip identifier |
| departure_time | TIMESTAMP | Trip start time |
| return_time | TIMESTAMP | Trip end time |
| departure_station_name | STRING | Starting station |
| departure_station_id | STRING | Starting station ID |
| return_station_name | STRING | Ending station |
| return_station_id | STRING | Ending station ID |
| duration_sec | DOUBLE | Trip duration in seconds |
| covered_distance_m | DOUBLE | Distance in meters |
| covered_distance_km | DOUBLE | Distance in kilometers |
| is_electric_bike | BOOLEAN | Electric bike flag |
| membership_type | STRING | User membership type |
| departure_year | INT | Year (for partitioning) |
| departure_month | INT | Month (for partitioning) |

### silver_stations Table
| Column | Type | Description |
|--------|------|-------------|
| station_id | STRING | Unique station identifier |
| station_name | STRING | Clean station name |
| lat | DOUBLE | Latitude |
| lon | DOUBLE | Longitude |
| capacity | INT | Total dock capacity |
| num_bikes_available | INT | Current bikes available |
| num_docks_available | INT | Current docks available |
| is_renting | BOOLEAN | Can rent from this station |
| is_returning | BOOLEAN | Can return to this station |

### silver_site Table
| Column | Type | Description |
|--------|------|-------------|
| site_page_id | BIGINT | Unique page identifier |
| url | STRING | Page URL |
| title | STRING | Page title |
| description | STRING | Meta description |
| content_md | STRING | Markdown content (for embeddings) |
| scraped_at | TIMESTAMP | When page was scraped |

---

## 🔧 Troubleshooting

### Issue: Catalog doesn't exist
**Solution:**
```sql
CREATE CATALOG IF NOT EXISTS vanhack;
USE CATALOG vanhack;
```

### Issue: Schema not found
**Solution:**
```sql
CREATE SCHEMA IF NOT EXISTS vanhack.mobi_data;
```

### Issue: Vector Search endpoint not ready
**Solution:**
Wait 5-10 minutes for endpoint to provision, then check:
```python
from databricks.vector_search.client import VectorSearchClient
client = VectorSearchClient()
client.list_endpoints()
```

### Issue: Functions not found
**Solution:**
Re-run `02_tools.ipynb` to recreate SQL functions

### Issue: Missing data in tables
**Solution:**
Re-run `01_data.ipynb` with `overwrite_downloads: false` to use bundled data

---

## 🎓 Key Concepts for Agent Development

### 1. **Bronze-Silver-Gold Pattern**
- **Bronze**: Raw data as-is
- **Silver**: Cleaned, typed, normalized
- **Gold**: Business-level aggregates (not used in this project)

### 2. **Unity Catalog Benefits**
- Centralized governance
- Fine-grained permissions
- Cross-workspace sharing
- Audit logging

### 3. **Vector Search for RAG**
- Converts text to embeddings automatically
- Enables semantic (meaning-based) search
- Powers question-answering agents
- No external API needed

### 4. **Python UDTFs (User-Defined Table Functions)**
- Call external APIs from SQL
- Run custom Python logic
- Return tabular results
- Perfect for agent tools

---

## 📚 Next Steps

1. ✅ **Complete all 3 notebooks** (01_data, 02_tools, 03_vector_search)
2. ✅ **Verify data quality** (check row counts, sample queries)
3. ✅ **Export data** to Agent Bricks format
4. ✅ **Create catalog** in Agent Bricks
5. ✅ **Configure tools** (map functions to agent tools)
6. ✅ **Build first agent** (start simple, iterate)
7. ✅ **Test workflows** (use sample queries above)
8. 🚀 **Deploy and iterate** (add features based on feedback)

---

## 💡 Tips for Success

1. **Start Simple**: Build a basic Q&A agent first, then add complexity
2. **Use Real-Time Data**: The `live_station_status()` function is a killer feature
3. **Leverage Vector Search**: Don't hardcode answers - let the agent search docs
4. **Test Edge Cases**: What happens if a station doesn't exist? Network fails?
5. **Monitor Performance**: Track which queries are slow, optimize accordingly
6. **Iterate Based on Usage**: Add tools as you discover new use cases

---

## 🆘 Support Resources

- **Databricks Docs**: https://docs.databricks.com/
- **GBFS Specification**: https://github.com/MobilityData/gbfs
- **Mobi Open Data**: https://www.mobibikes.ca/en/system-data
- **Vector Search Guide**: https://docs.databricks.com/generative-ai/vector-search.html

---

## 📝 Summary Checklist

- [ ] Created `vanhack` catalog in Databricks
- [ ] Configured `config.yaml` with correct catalog/schema names
- [ ] Ran `01_data.ipynb` successfully (Bronze + Silver tables created)
- [ ] Ran `02_tools.ipynb` successfully (SQL functions created)
- [ ] Ran `03_vector_search.ipynb` successfully (Vector index built)
- [ ] Tested all SQL functions with sample queries
- [ ] Exported data in Agent Bricks-compatible format
- [ ] Created `vanhack` catalog in Agent Bricks
- [ ] Configured agent tools mapping to SQL functions
- [ ] Created first agent with system prompt
- [ ] Tested agent with sample queries
- [ ] Ready to build advanced features!

---

**Good luck building your Mobi AI agents! 🚴‍♂️🤖**
