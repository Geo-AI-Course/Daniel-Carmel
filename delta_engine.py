"""
Delta Engine: BANTAL vs OSM
Produces classified delta tables for buildings and addresses across 11 pilot settlements.

Output files (in ./output/):
  delta_buildings.csv  - per-building delta rows
  delta_addresses.csv  - per-address delta rows
  delta_summary.csv    - per-settlement aggregation + delta_score
"""

import os
import re
import warnings
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely import wkt as shapely_wkt

warnings.filterwarnings("ignore")

DATA = "."
OUT  = "output"
os.makedirs(OUT, exist_ok=True)

ENC = "cp1255"

# ── Helpers ───────────────────────────────────────────────────────

def load_gdf(path, src_crs):
    df = pd.read_csv(path, encoding=ENC)
    df["geometry"] = df["WKT"].apply(shapely_wkt.loads)
    return gpd.GeoDataFrame(df, geometry="geometry", crs=src_crs)

def parse_hstore(s):
    if pd.isna(s):
        return {}
    return dict(re.findall(r'"([^"]+)"=>"([^"]+)"', str(s)))

def norm_street(s):
    """Normalize Hebrew street name via two synonym tables + ה-article stripping.

    Lookup order (applied with and without leading ה):
    1. VARIANT_MAP  — synonym.csv: general name variants  (e.g. 'שד הרצל' → 'הרצל')
    2. ALIAS_MAP    — STR_SYNONIMS: alias→canonical STR_NAME from BANTAL street table
                      (e.g. 'רא"ל יגאל ידין' → 'יגאל ידין' via StreetID→STR_NAME)
    3. ה-stripped form — fallback when name not found in either table
    """
    if pd.isna(s):
        return ""
    s = str(s).strip()
    # 1+2: full name lookups
    if s in VARIANT_MAP:
        return VARIANT_MAP[s]
    if s in ALIAS_MAP:
        canonical = ALIAS_MAP[s]
        return VARIANT_MAP.get(canonical, canonical)   # re-apply synonym on result
    # 3: strip ה and retry both maps
    if s.startswith("ה"):
        s_stripped = s[1:]
        if s_stripped in VARIANT_MAP:
            return VARIANT_MAP[s_stripped]
        if s_stripped in ALIAS_MAP:
            canonical = ALIAS_MAP[s_stripped]
            return VARIANT_MAP.get(canonical, canonical)
        return s_stripped
    return s

def norm_house(s):
    """Extract leading numeric part from house number."""
    if pd.isna(s):
        return ""
    m = re.match(r"(\d+)", str(s).strip())
    return m.group(1) if m else ""

def sjoin_dedup(left, right, **kwargs):
    """sjoin then drop duplicate left-side rows (keep first match)."""
    joined = gpd.sjoin(left, right, **kwargs)
    return joined[~joined.index.duplicated(keep="first")]

# ── 1. Load all data ──────────────────────────────────────────────

print("Loading data...")
setel    = load_gdf(f"{DATA}/SETEL.csv",            "EPSG:2039")
bldg_b   = load_gdf(f"{DATA}/BANTAL_BLDG.csv",      "EPSG:2039")
addr_b   = load_gdf(f"{DATA}/BANTAL_ADDR.csv",      "EPSG:2039")
bldg_o   = load_gdf(f"{DATA}/OSM_BLDG.csv",         "EPSG:2039")
addr_o   = load_gdf(f"{DATA}/OSM_ADDR.csv",         "EPSG:2039")
streets  = pd.read_csv(f"{DATA}/TOPO_STREET_NAME.csv", encoding=ENC)
setnames = pd.read_csv(f"{DATA}/TOPO_SETEL_NAME.csv",  encoding=ENC)

# Build synonym lookup: variant → canonical street name
# synonym.csv columns: 'שם תקני' (canonical), 'שמות כפי שמופיעים בלמ"ס' (comma-separated variants)
_syn = pd.read_csv(f"{DATA}/synonym.csv", encoding="utf-8-sig")
_syn.columns = ["canonical", "variants"]
VARIANT_MAP = {}
for canonical, variants_str in zip(_syn["canonical"], _syn["variants"]):
    canonical = str(canonical).strip()
    for v in str(variants_str).split(","):
        v = v.strip()
        if v:
            VARIANT_MAP[v] = canonical
print(f"  synonym.csv variants loaded: {len(VARIANT_MAP):,}")

# Build ALIAS_MAP from STR_SYNONIMS.csv: alias → canonical STR_NAME (via STR_ID join)
_strid_to_name = (streets.dropna(subset=["STR_ID", "STR_NAME"])
                  .set_index("STR_ID")["STR_NAME"].to_dict())
_syn2 = pd.read_csv(f"{DATA}/STR_SYNONIMS.csv", encoding="cp1255")
_syn2 = _syn2[_syn2["StreetID"] != "StreetID"]           # drop repeated header rows
_syn2["StreetID"] = pd.to_numeric(_syn2["StreetID"], errors="coerce")
_syn2 = _syn2.dropna(subset=["StreetID", "StreetAlias"]).copy()
_syn2["StreetID"] = _syn2["StreetID"].astype(int)
_syn2["canonical"] = _syn2["StreetID"].map(_strid_to_name)
_syn2 = _syn2.dropna(subset=["canonical"])

ALIAS_MAP = {}
for alias, canonical in zip(_syn2["StreetAlias"], _syn2["canonical"]):
    alias     = str(alias).strip()
    canonical = str(canonical).strip()
    if alias and canonical and alias not in VARIANT_MAP:  # synonym.csv takes priority
        ALIAS_MAP[alias] = canonical
print(f"  STR_SYNONIMS aliases loaded: {len(ALIAS_MAP):,}")

# CR_PNIM is the canonical settlement code in SETEL (always filled).
# It matches BANTAL_ADDR.SETL_CODE for the same settlements.
setel["setl_code"] = setel["CR_PNIM"].astype(int)
setel_zones = setel[["geometry", "setl_code", "Muni_Eng", "Muni_Heb", "AreaSQM"]].copy()

print(f"  BANTAL BLDG: {len(bldg_b):,}   OSM BLDG: {len(bldg_o):,}")
print(f"  BANTAL ADDR: {len(addr_b):,}   OSM ADDR: {len(addr_o):,}")
print(f"  Pilot settlements: {len(setel)}")


# ── 2. Building Deltas ────────────────────────────────────────────

print("\n[BUILDINGS] Assigning settlements...")

# Assign settlement code via spatial join (buildings have no SETL_CODE column)
bldg_b_sj = sjoin_dedup(bldg_b, setel_zones[["geometry", "setl_code"]], how="left", predicate="within")
bldg_o_sj = sjoin_dedup(bldg_o, setel_zones[["geometry", "setl_code"]], how="left", predicate="within")

bldg_b_sj["area_sqm"] = bldg_b_sj.geometry.area
bldg_o_sj["area_sqm"] = bldg_o_sj.geometry.area

# Restrict to pilot area only
bldg_b_pilot = bldg_b_sj.dropna(subset=["setl_code"]).copy()
bldg_o_pilot = bldg_o_sj.dropna(subset=["setl_code"]).copy()

print(f"  In pilot — BANTAL: {len(bldg_b_pilot):,}   OSM: {len(bldg_o_pilot):,}")

# OSM buildings with no intersecting BANTAL building → NEW_IN_OSM
print("[BUILDINGS] Finding NEW_IN_OSM...")
osm_vs_bantal = sjoin_dedup(bldg_o_pilot[["geometry", "setl_code", "building", "area_sqm"]],
                             bldg_b_pilot[["geometry"]], how="left", predicate="intersects")
new_in_osm = bldg_o_pilot[osm_vs_bantal["index_right"].isna()]

# BANTAL buildings with no intersecting OSM building → MISSING_IN_OSM
print("[BUILDINGS] Finding MISSING_IN_OSM...")
bantal_vs_osm = sjoin_dedup(bldg_b_pilot[["geometry", "setl_code", "FTYPE", "area_sqm"]],
                             bldg_o_pilot[["geometry"]], how="left", predicate="intersects")
missing_in_osm = bldg_b_pilot[bantal_vs_osm["index_right"].isna()]

print(f"  NEW_IN_OSM: {len(new_in_osm):,}   MISSING_IN_OSM: {len(missing_in_osm):,}")

# Build delta_buildings table
bldg_new = new_in_osm[["setl_code", "building", "area_sqm", "geometry"]].copy()
bldg_new["delta_type"]       = "NEW_IN_OSM"
bldg_new["source"]           = "OSM"
bldg_new["ftype"]            = None
bldg_new["osm_building_tag"] = bldg_new["building"]
bldg_new = bldg_new.drop(columns=["building"])

bldg_miss = missing_in_osm[["setl_code", "FTYPE", "area_sqm", "geometry"]].copy()
bldg_miss["delta_type"]       = "MISSING_IN_OSM"
bldg_miss["source"]           = "BANTAL"
bldg_miss["ftype"]            = bldg_miss["FTYPE"]
bldg_miss["osm_building_tag"] = None
bldg_miss = bldg_miss.drop(columns=["FTYPE"])

delta_bldg = pd.concat([bldg_new, bldg_miss], ignore_index=True)
delta_bldg["layer"]        = "BUILDING"
delta_bldg["geometry_wkt"] = delta_bldg["geometry"].apply(lambda g: g.wkt)
delta_bldg = delta_bldg.drop(columns=["geometry"])

# Add settlement names
setcode_to_name = setel.set_index("setl_code")["Muni_Eng"].to_dict()
delta_bldg["setl_name"] = delta_bldg["setl_code"].map(setcode_to_name)

cols_bldg = ["delta_type", "layer", "source", "setl_code", "setl_name", "ftype",
             "osm_building_tag", "area_sqm", "geometry_wkt"]
delta_bldg[cols_bldg].to_csv(f"{OUT}/delta_buildings.csv", index=False, encoding="utf-8-sig")
print(f"  Saved: output/delta_buildings.csv ({len(delta_bldg):,} rows)")


# ── 3. Address Deltas ─────────────────────────────────────────────

print("\n[ADDRESSES] Preparing BANTAL addresses...")

# Join street names onto BANTAL addresses
addr_b_full = addr_b.merge(streets[["STR_ID", "STR_NAME"]], on="STR_ID", how="left")
addr_b_full["norm_street"] = addr_b_full["STR_NAME"].apply(norm_street)
addr_b_full["norm_house"]  = addr_b_full["HOUSE_NUM"].apply(norm_house)
# Use only rows with a valid house number
addr_b_full = addr_b_full[addr_b_full["norm_house"] != ""].copy()
# Canonical address key: settlement_code + street + house
addr_b_full["addr_key"] = (
    addr_b_full["SETL_CODE"].astype(str) + "_"
    + addr_b_full["norm_street"] + "_"
    + addr_b_full["norm_house"]
)
# Convert Line geometry to centroid for point operations
addr_b_full["centroid"] = addr_b_full.geometry.centroid
addr_b_full = addr_b_full.reset_index(drop=True)

print(f"  BANTAL addresses with house number: {len(addr_b_full):,}")

print("[ADDRESSES] Preparing OSM addresses...")
osm_tags         = addr_o["other_tags"].apply(parse_hstore)
addr_o["house_num"]   = osm_tags.apply(lambda t: t.get("addr:housenumber", ""))
addr_o["street_name"] = osm_tags.apply(lambda t: t.get("addr:street", ""))
addr_o["norm_street"] = addr_o["street_name"].apply(norm_street)
addr_o["norm_house"]  = addr_o["house_num"].apply(norm_house)

# Assign settlement via spatial join (OSM_ADDR has no SETL_CODE)
addr_o_sj = sjoin_dedup(addr_o, setel_zones[["geometry", "setl_code"]], how="left", predicate="within")
addr_o_sj = addr_o_sj[addr_o_sj["norm_house"] != ""].copy()
addr_o_sj["addr_key"] = (
    addr_o_sj["setl_code"].astype(str) + "_"
    + addr_o_sj["norm_street"] + "_"
    + addr_o_sj["norm_house"]
)
addr_o_sj = addr_o_sj.reset_index(drop=True)

print(f"  OSM addresses with house number: {len(addr_o_sj):,}")

# ── Outer merge on addr_key ────────────────────────────────────────
print("[ADDRESSES] Matching...")

bantal_side = addr_b_full[["addr_key", "SETL_CODE", "STR_NAME", "HOUSE_NUM",
                            "ENTRY_LETR", "centroid"]].copy()
bantal_side = bantal_side.rename(columns={
    "SETL_CODE": "b_setl", "STR_NAME": "b_street",
    "HOUSE_NUM": "b_house", "ENTRY_LETR": "b_entry",
    "centroid": "b_pt"
})

osm_side = addr_o_sj[["addr_key", "setl_code", "street_name", "house_num", "geometry"]].copy()
osm_side = osm_side.rename(columns={
    "setl_code": "o_setl", "street_name": "o_street",
    "house_num": "o_house", "geometry": "o_pt"
})
# Drop duplicate OSM addresses on same key (keep first)
osm_side = osm_side.drop_duplicates(subset=["addr_key"], keep="first")
bantal_side = bantal_side.drop_duplicates(subset=["addr_key"], keep="first")

merged = bantal_side.merge(osm_side, on="addr_key", how="outer")

# Separate matched vs unmatched
matched_mask   = merged["b_house"].notna() & merged["o_house"].notna()
only_bantal    = merged[merged["o_house"].isna()].copy()
only_osm       = merged[merged["b_house"].isna()].copy()
both           = merged[matched_mask].copy()

print(f"  Matched pairs: {len(both):,}  "
      f"Only BANTAL: {len(only_bantal):,}  "
      f"Only OSM: {len(only_osm):,}")

# ── Spatial classification of matched pairs ────────────────────────

# Build GeoSeries for vectorized operations
both = both.reset_index(drop=True)
b_pts = gpd.GeoSeries(both["b_pt"].values,   crs="EPSG:2039")
o_pts = gpd.GeoSeries(both["o_pt"].values,   crs="EPSG:2039")
both["distance_m"] = b_pts.distance(o_pts).round(2)

# Point-in-polygon: which BANTAL building contains each address point?
bldg_polys = bldg_b_pilot[["geometry"]].reset_index(drop=True)

b_gdf = gpd.GeoDataFrame(both[["addr_key"]], geometry=b_pts, crs="EPSG:2039")
o_gdf = gpd.GeoDataFrame(both[["addr_key"]], geometry=o_pts, crs="EPSG:2039")

b_in_bldg = gpd.sjoin(b_gdf, bldg_polys, how="left", predicate="within")
b_in_bldg = b_in_bldg[~b_in_bldg.index.duplicated(keep="first")]["index_right"].rename("b_bldg_idx")

o_in_bldg = gpd.sjoin(o_gdf, bldg_polys, how="left", predicate="within")
o_in_bldg = o_in_bldg[~o_in_bldg.index.duplicated(keep="first")]["index_right"].rename("o_bldg_idx")

both = both.join(b_in_bldg).join(o_in_bldg)

# Classify
same_bldg      = both["b_bldg_idx"].notna() & (both["b_bldg_idx"] == both["o_bldg_idx"])
both_outside   = both["b_bldg_idx"].isna()  & both["o_bldg_idx"].isna()
close_outside  = both_outside & (both["distance_m"] <= 15)

both["delta_type"] = "SPATIAL_MISMATCH"
both.loc[same_bldg | close_outside, "delta_type"] = "FULL_MATCH"

# ── Assemble full address delta table ─────────────────────────────

# Matched pairs (FULL_MATCH or SPATIAL_MISMATCH)
addr_matched = pd.DataFrame({
    "delta_type":  both["delta_type"].values,
    "layer":       "ADDRESS",
    "setl_code":   both["b_setl"].values,
    "street_name": both["b_street"].values,
    "house_num":   both["b_house"].values,
    "entry_ltr":   both["b_entry"].values,
    "distance_m":  both["distance_m"].values,
})

# BANTAL-only addresses (no OSM counterpart)
addr_only_b = pd.DataFrame({
    "delta_type":  "MISSING_IN_OSM",
    "layer":       "ADDRESS",
    "setl_code":   only_bantal["b_setl"].values,
    "street_name": only_bantal["b_street"].values,
    "house_num":   only_bantal["b_house"].values,
    "entry_ltr":   only_bantal["b_entry"].values,
    "distance_m":  np.nan,
})

# OSM-only addresses within pilot area (no BANTAL counterpart)
only_osm_pilot = only_osm[only_osm["o_setl"].notna()].copy()
addr_only_o = pd.DataFrame({
    "delta_type":  "MISSING_IN_BANTAL",
    "layer":       "ADDRESS",
    "setl_code":   only_osm_pilot["o_setl"].values,
    "street_name": only_osm_pilot["o_street"].values,
    "house_num":   only_osm_pilot["o_house"].values,
    "entry_ltr":   np.nan,
    "distance_m":  np.nan,
})

delta_addr = pd.concat([addr_matched, addr_only_b, addr_only_o], ignore_index=True)
delta_addr["setl_code"]  = pd.to_numeric(delta_addr["setl_code"], errors="coerce")
delta_addr["setl_name"]  = delta_addr["setl_code"].map(setcode_to_name)

cols_addr = ["delta_type", "layer", "setl_code", "setl_name", "street_name",
             "house_num", "entry_ltr", "distance_m"]
delta_addr[cols_addr].to_csv(f"{OUT}/delta_addresses.csv", index=False, encoding="utf-8-sig")

print("\nAddress delta breakdown:")
print(delta_addr["delta_type"].value_counts().to_string())
print(f"  Saved: output/delta_addresses.csv ({len(delta_addr):,} rows)")


# ── 4. Delta Summary per Settlement ───────────────────────────────

print("\n[SUMMARY] Aggregating per settlement...")

# Building counts from full datasets (before delta filter)
total_bantal_bldg = (bldg_b_pilot.groupby("setl_code").size().rename("total_bantal_bldg"))
total_osm_bldg    = (bldg_o_pilot.groupby("setl_code").size().rename("total_osm_bldg"))

# Building delta counts
bldg_delta_counts = (
    delta_bldg.groupby(["setl_code", "delta_type"]).size()
    .unstack(fill_value=0)
    .rename(columns={"NEW_IN_OSM": "n_new_bldg", "MISSING_IN_OSM": "n_missing_bldg"})
)

# Address counts
total_bantal_addr = (
    addr_b_full.groupby("SETL_CODE").size()
    .rename("total_bantal_addr")
    .rename_axis("setl_code")
)

addr_delta_counts = (
    delta_addr.dropna(subset=["setl_code"])
    .groupby(["setl_code", "delta_type"]).size()
    .unstack(fill_value=0)
)
# Rename columns defensively (not all types may appear per settlement)
addr_rename = {
    "FULL_MATCH":       "n_full_match",
    "SPATIAL_MISMATCH": "n_spatial_mismatch",
    "MISSING_IN_BANTAL":"n_missing_bantal_addr",
    "MISSING_IN_OSM":   "n_missing_osm_addr",
}
addr_delta_counts = addr_delta_counts.rename(columns=addr_rename)
for col in addr_rename.values():
    if col not in addr_delta_counts.columns:
        addr_delta_counts[col] = 0

summary = (setel_zones[["setl_code", "Muni_Eng", "Muni_Heb", "AreaSQM"]]
           .set_index("setl_code")
           .join(total_bantal_bldg, how="left")
           .join(total_osm_bldg,    how="left")
           .join(bldg_delta_counts,  how="left")
           .join(total_bantal_addr,  how="left")
           .join(addr_delta_counts,  how="left"))

# Fill missing count columns with 0
count_cols = ["total_bantal_bldg","total_osm_bldg","n_new_bldg","n_missing_bldg",
              "total_bantal_addr","n_full_match","n_spatial_mismatch",
              "n_missing_bantal_addr","n_missing_osm_addr"]
for c in count_cols:
    if c not in summary.columns:
        summary[c] = 0
    summary[c] = summary[c].fillna(0).astype(int)

# Coverage %
summary["osm_coverage_pct"] = (
    summary["total_osm_bldg"] / summary["total_bantal_bldg"].replace(0, np.nan) * 100
).round(1)

# Delta score: weighted composite (0–1 scale, higher = more deltas)
# Ratios clipped to [0,1] to handle edge cases (e.g. regional councils with 0 BANTAL addresses)
w = {"new_bldg": 0.40, "miss_bldg": 0.30, "miss_addr": 0.20, "spatial": 0.10}
r_new  = (summary["n_new_bldg"] / summary["total_bantal_bldg"].replace(0, np.nan)).clip(0, 1).fillna(0)
r_miss = (summary["n_missing_bldg"] / summary["total_bantal_bldg"].replace(0, np.nan)).clip(0, 1).fillna(0)
r_addr = (summary["n_missing_bantal_addr"] / summary["total_bantal_addr"].replace(0, np.nan)).clip(0, 1).fillna(0)
r_spat = (summary["n_spatial_mismatch"] /
          (summary["n_full_match"] + summary["n_spatial_mismatch"]).replace(0, np.nan)).clip(0, 1).fillna(0)
summary["delta_score"] = (
    w["new_bldg"] * r_new + w["miss_bldg"] * r_miss +
    w["miss_addr"] * r_addr + w["spatial"] * r_spat
).round(4)

summary = summary.reset_index()
summary.to_csv(f"{OUT}/delta_summary.csv", index=False, encoding="utf-8-sig")

print("\nDelta Summary:")
print(summary[["Muni_Eng","total_bantal_bldg","total_osm_bldg",
               "n_new_bldg","n_missing_bldg","n_missing_bantal_addr","delta_score"]].to_string())
print(f"\n  Saved: output/delta_summary.csv")
print("\nDone! All delta files written to ./output/")
