# תוכנית יישום — Spatial Delta Engine + ML Risk Scoring

## רקע

הפרויקט השוואה בין בסיס הנתונים הרשמי **BANTAL (בנט"ל)** של מפ"י לבין נתוני **OpenStreetMap (OSM)** עבור 11 ישובי פיילוט. מטרת היישום הנוכחי:

1. **מנוע דלתאות** — חישוב מרחבי אמיתי המייצר טבלה מסווגת של פערים במבנים ובכתובות  
2. **מודל ML** — חיזוי רמת דלתאות בישובים שמחוץ לפיילוט על בסיס נתונים דמוגרפיים

---

## מבנה הקבצים

```
CSV/
├── delta_engine.py          ← מנוע הדלתאות (חישוב מרחבי)
├── ml_risk.py               ← מודל למידת מכונה + חיזוי
├── eda_app.py               ← Streamlit dashboard (הורחב ב-2 טאבים)
├── output/                  ← תיקיית פלט (נוצרת אוטומטית)
│   ├── delta_buildings.csv
│   ├── delta_addresses.csv
│   ├── delta_summary.csv
│   ├── ml_predictions.csv
│   └── ml_feature_importance.csv
└── [קבצי נתונים גולמיים — לא ב-git]
```

---

## שלב 1 — `delta_engine.py`

### עקרון הטעינה

| קובץ | CRS בקובץ | הערה |
|------|-----------|------|
| `BANTAL_BLDG.csv` | EPSG:2039 (ITM) | |
| `BANTAL_ADDR.csv` | EPSG:2039 | |
| `OSM_BLDG.csv` | **EPSG:2039** | הנתונים כבר הומרו — לא EPSG:4326 |
| `OSM_ADDR.csv` | **EPSG:2039** | הנתונים כבר הומרו — לא EPSG:4326 |
| `SETEL.csv` | EPSG:2039 | MULTIPOLYGON Z (תלת-ממדי) |
| `synonym.csv` | — | טבלת סינונימים כללית: `שם תקני` ← וריאנטים מופרדים בפסיק; encoding: `utf-8-sig` |
| `STR_SYNONIMS.csv` | — | טבלת alias לפי מזהה רחוב BANTAL: `StreetID` (= `STR_ID`) ← `StreetAlias`; שורה לכל alias; encoding: `cp1255` |

> **הערה חשובה**: CLAUDE.md מציין שנתוני OSM מגיעים ב-EPSG:4326, אך קבצי ה-CSV שיוצאו מ-QGIS כבר הומרו ל-ITM. השימוש ב-`to_crs(epsg=2039)` על נתוני ITM מייצר קואורדינטות `inf` ו-spatial joins שמחזירים 0 תוצאות.

### מפתח הישוב

`SETEL.CR_PNIM` = `BANTAL_ADDR.SETL_CODE` = `bycode2024.סמל יישוב`

עבור ישובים שאין להם כתובות ישירות בבנטל (מועצות אזוריות: Hof Ashkelon, Gderot), ה-`SETL_CODE` לא מופיע ב-`BANTAL_ADDR` — הפתרון: שימוש ב-Spatial Join עם SETEL.

### לוגיקת דלתאות מבנים

```
OSM ──→ sjoin(intersects) ←── BANTAL
  ├── OSM ללא BANTAL = NEW_IN_OSM
  └── BANTAL ללא OSM = MISSING_IN_OSM
```

שתי הצדדים מוגבלים לאזור הפיילוט בלבד (sjoin עם SETEL polygons).

### לוגיקת דלתאות כתובות

**שלב א** — נרמול שמות רחובות עם שתי טבלאות סינונימים:

```python
# synonym.csv: וריאנט → שם תקני כללי
_syn = pd.read_csv("synonym.csv", encoding="utf-8-sig")
_syn.columns = ["canonical", "variants"]
VARIANT_MAP = {}
for canonical, variants_str in zip(_syn["canonical"], _syn["variants"]):
    for v in str(variants_str).split(","):
        if v.strip(): VARIANT_MAP[v.strip()] = canonical.strip()

# STR_SYNONIMS.csv: alias → STR_NAME קנוני דרך STR_ID
_syn2 = pd.read_csv("STR_SYNONIMS.csv", encoding="cp1255")
_syn2 = _syn2[_syn2["StreetID"] != "StreetID"]  # סינון שורות header כפולות
_strid_to_name = streets.set_index("STR_ID")["STR_NAME"].to_dict()
ALIAS_MAP = {}
for alias, strid in zip(_syn2["StreetAlias"], _syn2["StreetID"]):
    canonical = _strid_to_name.get(int(strid))
    if alias and canonical and alias not in VARIANT_MAP:
        ALIAS_MAP[alias.strip()] = canonical.strip()
```

`norm_street` בודקת לפי הסדר: VARIANT_MAP → ALIAS_MAP → הסרת ה' → fallback.
אם alias נמצא ב-ALIAS_MAP, מוחזר `STR_NAME` ולאחר מכן מוחל עליו VARIANT_MAP שוב.

**שלב ב** — בניית מפתח כתובת מנורמל:
```
BANTAL: SETL_CODE + norm_street(STR_NAME) + norm_house(HOUSE_NUM)
OSM:    CR_PNIM (via sjoin עם SETEL) + norm_street(addr:street) + norm_house(addr:housenumber)
```

**שלב ב** — outer merge על המפתח + סיווג:

| תוצאה | סיווג |
|--------|--------|
| שני הצדדים + שתי הנקודות באותו פוליגון BANTAL | `FULL_MATCH` |
| שני הצדדים + שתי הנקודות מחוץ לפוליגון וקרובות (<15 מ') | `FULL_MATCH` |
| שני הצדדים + מיקומים שונים / מרחק >15 מ' | `SPATIAL_MISMATCH` |
| רק ב-BANTAL | `MISSING_IN_OSM` |
| רק ב-OSM (בתוך אזור פיילוט) | `MISSING_IN_BANTAL` |

**שלב ג** — Point-in-polygon וקטורי (gpd.sjoin, לא לולאה):
```python
b_in_bldg = gpd.sjoin(b_gdf, bldg_polys, how="left", predicate="within")
o_in_bldg = gpd.sjoin(o_gdf, bldg_polys, how="left", predicate="within")
```

### ציון דלתא (delta_score)

```
delta_score = 0.40 × clip(n_new_bldg / total_bantal_bldg)
            + 0.30 × clip(n_missing_bldg / total_bantal_bldg)
            + 0.20 × clip(n_missing_bantal_addr / total_bantal_addr)
            + 0.10 × clip(n_spatial_mismatch / (n_full_match + n_spatial_mismatch))
```

כל יחס נחתך ל-[0,1] כדי לטפל במועצות אזוריות שאין להן כתובות בבנטל.

---

## שלב 2 — `ml_risk.py`

### נתוני אימון

- 11 ישובי פיילוט עם `delta_score` ממדוד (`delta_summary.csv`)
- מחוברים לדמוגרפיה מ-`bycode2024.csv` (encoding: `utf-8-sig`)

### פיצ'רים

| פיצ'ר | מקור |
|--------|------|
| `log_pop` | log(1 + אוכלוסייה 2024) |
| `area_sqkm` | AreaSQM מ-SETEL / 1,000,000 |
| `pop_density` | log_pop / area_sqkm |
| `pct_arab` | ערבים / סך כלל |
| `religion_type` | דת ישוב (1/2/3) |
| `settlement_form` | צורת ישוב שוטפת |
| `is_jewish/mixed/bedouin` | one-hot מ-religion_type |

### מודל

**Ridge Regression** עם Leave-One-Out Cross-Validation:
```python
model = Pipeline([("scaler", StandardScaler()), ("ridge", RidgeCV(alphas=[0.01,0.1,1,10,100]))])
```

**מגבלה ידועה**: עם 9 נקודות אימון (2 מועצות אזוריות לא מצאו התאמה בדמוגרפיה), הדיוק נמוך (LOO CV R²=-0.43). הדירוג שימושי לסיווג יחסי — לא לחיזוי מוחלט.

### פלט

`ml_predictions.csv` עם:
- `risk_rank` — דירוג כלל-ארצי (1 = סיכון גבוה ביותר)
- `risk_score_100` — ציון 0-100
- `is_pilot` / `actual_delta_score` — להשוואה עם נתוני פיילוט ממשיים

---

## שלב 3 — הרחבת `eda_app.py`

### טאב 6: 🔄 דלתאות

- KPI cards: סה"כ לפי סוג דלתא
- Bar chart: delta_score לפי ישוב
- Pie chart: התפלגות סוגי דלתאות כתובות
- Selectbox: drilldown לפי ישוב עם טבלאות מפורטות
- Download buttons לכל קובץ

### טאב 7: 🤖 חיזוי סיכון

- TOP-N bar chart (slider לבחירת כמות)
- Scatter: אוכלוסייה (log) vs. ציון סיכון (צבע לפי דת, ⭐ = פיילוט)
- Feature importance bar chart
- טבלת השוואה: ישובי פיילוט ממשי vs. חזוי

---

## הרצה

```powershell
# 1. הפעל venv
c:\Users\danielb\Documents\GEOAI\Project\Daniel-Carmel\venv\Scripts\Activate.ps1

# 2. חישוב דלתאות (~2-3 דקות)
python delta_engine.py

# 3. ML (תלוי ב-output/delta_summary.csv)
python ml_risk.py

# 4. Dashboard
streamlit run eda_app.py
```

---

## תלויות נוספות שהותקנו

```
scikit-learn==1.9.0   (לא היה ב-requirements.txt המקורי)
scipy==1.17.1
joblib==1.5.3
```

להוסיף ל-`requirements.txt` אם לא קיים.
