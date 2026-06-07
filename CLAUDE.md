# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Spatial Delta Agent: Bantal vs. OSM** — a geospatial delta-detection system that compares Israel's official national topographic database (BANTAL/בנט"ל, maintained by מפ"י) against community-sourced OpenStreetMap data. The goal is to surface discrepancies in building polygons and address points across 11 pilot settlement zones so BANTAL editors can prioritize field updates.

## Running the App

The virtual environment lives in `c:\Users\danielb\Documents\GEOAI\Project\Daniel-Carmel\venv`.

```powershell
# Activate venv
c:\Users\danielb\Documents\GEOAI\Project\Daniel-Carmel\venv\Scripts\Activate.ps1

# Run the Streamlit EDA dashboard (from the CSV directory)
streamlit run eda_app.py
```

Install dependencies (if venv is fresh):
```powershell
pip install -r c:\Users\danielb\Documents\GEOAI\Project\Daniel-Carmel\requirements.txt
```

## Data Architecture

All CSV files use `encoding="cp1255"` (Windows Hebrew). Geometry is stored as WKT strings.

| File | Geometry | CRS | Description |
|------|----------|-----|-------------|
| `BANTAL_BLDG.csv` | Polygon | EPSG:2039 (ITM) | Official building polygons |
| `BANTAL_ADDR.csv` | Line | EPSG:2039 | Official address points (line geometry) |
| `OSM_BLDG.csv` | MultiPolygon | EPSG:4326 → 2039 | OSM buildings |
| `OSM_ADDR.csv` | Point | EPSG:4326 → 2039 | OSM addresses |
| `SETEL.csv` | Polygon | — | Pilot settlement boundaries |
| `TOPO_STREET_NAME.csv` | — | — | Street name lookup (`str_id` → `STR_NAME`) |
| `TOPO_SETEL_NAME.csv` | — | — | Settlement name lookup (`SETEL_CODE` → `SETEL_NAME`) |
| `bycode2024.csv` | — | — | 2024 settlement demographics |
| `synonym.csv` | — | — | Street name synonym table: `שם תקני` (canonical) → `שמות כפי שמופיעים בלמ"ס` (comma-separated variants); ~26,332 entries; encoding: `utf-8-sig` |
| `STR_SYNONIMS.csv` | — | — | Per-street alias table: `StreetID` (= `STR_ID` in TOPO_STREET_NAME) → `StreetAlias` (one alias per row, multiple rows per street); ~95,777 rows / 36,978 streets; encoding: `cp1255`; contains repeated header rows that must be filtered |

**CRS rule**: BANTAL data arrives in ITM (EPSG:2039, meters). OSM data arrives in WGS84 (EPSG:4326, degrees) and must be projected via `to_crs(epsg=2039)` before any spatial operation to get real meter-based distances.

## Delta Detection Logic

**Buildings**: Spatial intersection (`ST_Intersects`). OSM polygons with no overlap with any BANTAL polygon = candidate new buildings. BANTAL polygons with no overlap with any OSM polygon = demolished or unmapped.

**Addresses** — 4 scenarios:
- **Full Match**: Same address content + both points inside the same BANTAL building polygon
- **Spatial Mismatch**: Same content but different physical locations (different polygons, one inside/outside, or >15 m apart when both are outside polygons)
- **Missing in BANTAL**: Exists in OSM, no counterpart in BANTAL
- **Missing in OSM**: Exists in BANTAL, no counterpart in OSM

**Street name normalization** uses two synonym tables in sequence:
1. `synonym.csv` (checked first): general name variants → canonical form. E.g. `שד הרצל` / `שדרות הרצל` → `הרצל`.
2. `STR_SYNONIMS.csv` (checked second, only if not found in synonym.csv): per-street aliases tied to BANTAL `STR_ID`. Alias is resolved via `StreetID → STR_NAME` (from TOPO_STREET_NAME), then synonym.csv is re-applied to the result. E.g. `רא"ל יגאל ידין` (alias) → `STR_ID` → `יגאל ידין` (STR_NAME). Both leading-ה stripping and full-name lookup are tried for each table.

## Key Schema Fields

- `FTYPE` (BANTAL buildings): building type code — 11=regular, 12=ruin, 13=construction, 14=agricultural, 15=industrial, 16=warehouse, 17=security, 18=public, 31=religious, 32=special
- `SETL_CODE` / `STR_CODE` / `STR_ID`: join keys linking addresses → streets → settlements
- `HOUSE_NUM` + `ENTRY_LTR`: address identifiers
- `building` (OSM): free-text tag (e.g. "yes", "apartments", "house")
- `other_tags` (OSM addresses): hstore-style string containing `addr:*` fields

## Data Constraints

- BANTAL raw data is proprietary (מפ"י license) — **never commit to version control**
- OSM data is public (ODbL)
- The `.qmd` files are QGIS layer metadata — not needed for Python workflows
