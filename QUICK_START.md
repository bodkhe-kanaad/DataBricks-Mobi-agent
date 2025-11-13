# 🚀 Quick Start Guide - 5 Minutes to Agent-Ready Data

## TL;DR - What You Need to Do

**Goal**: Get Vancouver Mobi bike share data into Agent Bricks to build AI agents.

**Catalog Name**: `vanhack`

---

## 📋 Step-by-Step (Do This In Order)

### 1️⃣ In Databricks: Create Catalog (30 seconds)
```sql
CREATE CATALOG IF NOT EXISTS vanhack;
```

### 2️⃣ Run Notebook 1: Data Pipeline (10-15 min)
- Open `01_data.ipynb` in Databricks
- Click "Run All"
- ✅ Creates: Bronze tables (raw) + Silver tables (cleaned)
- ✅ Result: ~7.6M trips, ~200 stations, ~50 site pages

### 3️⃣ Run Notebook 2: SQL Tools (2-3 min)
- Open `02_tools.ipynb`
- Click "Run All"
- ✅ Creates: SQL functions for agents to use

### 4️⃣ Run Notebook 3: Vector Search (5-7 min)
- Open `03_vector_search.ipynb`
- Click "Run All"
- ✅ Creates: Semantic search index for Q&A

### 5️⃣ In Agent Bricks: Create Catalog
- Create catalog named: `vanhack`
- Import these tables:
  - `vanhack.mobi_data.silver_trips`
  - `vanhack.mobi_data.silver_stations`
  - `vanhack.mobi_data.silver_site`

### 6️⃣ Create Your First Agent! 🎉

---

## 🎯 What You Get

### Data
- **7.6 million bike trips** (2018-2025)
- **200+ stations** with live availability
- **50+ documentation pages** for Q&A

### Tools (SQL Functions)
- `recent_trips_by_station('0152')` - Latest trips
- `live_station_status('0152')` - Real-time availability
- `nearby_stations(49.28, -123.12, 1.0)` - Find stations by location
- `site_search('pricing')` - Search documentation

### Agent Capabilities
- Answer questions about trip history
- Check real-time bike availability
- Find nearest stations
- Explain Mobi policies & pricing
- Analyze usage patterns

---

## 🧪 Test Your Setup

### In Databricks (SQL)
```sql
-- Test 1: Check trips table
SELECT COUNT(*) FROM vanhack.mobi_data.silver_trips;
-- Expected: ~7,600,000 rows

-- Test 2: Check stations
SELECT * FROM vanhack.mobi_data.silver_stations LIMIT 5;

-- Test 3: Find recent trips
SELECT * FROM recent_trips_by_station('0152');

-- Test 4: Live station status
SELECT * FROM live_station_status('0152');

-- Test 5: Search docs
SELECT * FROM vanhack.mobi_data.site_search('How to rent a bike');
```

### In Agent Bricks (Agent Queries)
- "How many bike trips happened in 2024?"
- "Are there bikes available at station 0152?"
- "Find me stations near downtown Vancouver"
- "What does a Mobi membership cost?"

---

## 🆘 Common Issues

| Problem | Solution |
|---------|----------|
| "Catalog not found" | Run: `CREATE CATALOG vanhack;` |
| "Schema not found" | Re-run notebook `01_data.ipynb` |
| "Function not found" | Re-run notebook `02_tools.ipynb` |
| "No data in tables" | Check `config.yaml` has `catalog: vanhack` |
| "Vector index not ready" | Wait 5-10 minutes, check endpoint status |

---

## 📚 Files in This Repo

| File | Purpose | When to Use |
|------|---------|------------|
| `config.yaml` | ✅ **Pre-configured** with `vanhack` catalog | Already done! |
| `01_data.ipynb` | **Run first** - Creates all tables | Step 2 |
| `02_tools.ipynb` | **Run second** - Creates SQL functions | Step 3 |
| `03_vector_search.ipynb` | **Run third** - Creates search index | Step 4 |
| `AGENT_BRICKS_SETUP_GUIDE.md` | **Detailed guide** with explanations | Reference |
| `QUICK_START.md` | **This file** - Fast setup | You are here! |

---

## 🎯 Your Next Agent Ideas

### Easy Agents (Start Here)
1. **Bike Availability Bot**: Check station status
2. **Trip Info Assistant**: Answer questions about trips
3. **Policy Helper**: Search documentation for rules

### Advanced Agents
1. **Trip Planner**: Suggest routes with real-time data
2. **System Analyst**: Identify station rebalancing needs
3. **Demand Forecaster**: Predict busy times/locations

---

## 💡 Pro Tips

1. ✅ **Always run notebooks in order**: 01 → 02 → 03
2. ✅ **Use `overwrite_downloads: false`** in config (faster, uses bundled data)
3. ✅ **Test SQL functions in Databricks first** before using in agents
4. ✅ **Start with simple agents**, add complexity later
5. ✅ **Real-time data is the killer feature** - use `live_station_status()`

---

## 📞 Need More Info?

- **Detailed Guide**: See `AGENT_BRICKS_SETUP_GUIDE.md`
- **Repository README**: See `README.md`
- **Databricks Docs**: https://docs.databricks.com/

---

**Ready? Go run those notebooks! 🚴‍♂️🤖**
