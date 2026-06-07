# סיכום תוצאות — Spatial Delta Agent: BANTAL vs. OSM

**פיילוט 2 | 11 ישובים | תאריך הרצה: יוני 2026**

---

## מה נבנה

| קובץ | תפקיד |
|------|--------|
| [delta_engine.py](delta_engine.py) | מנוע דלתאות — חישוב מרחבי, סיווג, שמירה |
| [ml_risk.py](ml_risk.py) | מודל Ridge Regression + חיזוי סיכון לכל ישובי ישראל |
| [eda_app.py](eda_app.py) | Dashboard Streamlit — הורחב ב-2 טאבים חדשים |
| [synonym.csv](synonym.csv) | טבלת סינונימים כללית (~26,332 רשומות): `שם תקני` ← וריאנטים מהלמ"ס |
| [STR_SYNONIMS.csv](STR_SYNONIMS.csv) | טבלת alias לפי מזהה רחוב (~95,777 שורות, 36,978 רחובות): `StreetID` ← `StreetAlias` |
| [output/](output/) | תיקיית פלט עם 5 קבצי CSV |

---

## תוצאות מנוע הדלתאות

### דלתאות מבנים — `output/delta_buildings.csv`

| סוג דלתא | כמות | משמעות |
|-----------|------|---------|
| `NEW_IN_OSM` | **923** | מבנים שמופיעים ב-OSM אך חסרים בבנטל |
| `MISSING_IN_OSM` | **30,610** | מבנים בבנטל שאינם ממופים ב-OSM |
| **סה"כ** | **31,533** | |

### דלתאות כתובות — `output/delta_addresses.csv`

| סוג דלתא | כמות | משמעות |
|-----------|------|---------|
| `FULL_MATCH` | **6,045** | כתובת זהה + שתי הנקודות באותו מבנה |
| `SPATIAL_MISMATCH` | **1,795** | כתובת זהה בתוכן, שוני במיקום הפיזי |
| `MISSING_IN_BANTAL` | **3,318** | קיים ב-OSM, חסר בבנטל |
| `MISSING_IN_OSM` | **57,880** | קיים בבנטל, חסר ב-OSM |
| **סה"כ** | **69,038** | |

---

## ציוני דלתא לפי ישוב — `output/delta_summary.csv`

| ישוב | מבנים בנטל | מבנים OSM | חדש ב-OSM | חסר ב-OSM | חסר בבנטל (כת') | **delta_score** |
|------|-----------|-----------|-----------|-----------|-----------------|----------------|
| Tverya (Tiberias) | 6,583 | 4,102 | **205** | 2,402 | 410 | **0.1874** |
| Lod | 7,131 | 4,232 | **66** | 2,619 | 161 | **0.1447** |
| Pardes Hana - Karkur | 11,444 | 6,551 | 54 | 4,614 | 201 | **0.1364** |
| Netivot | 5,460 | 3,302 | 63 | 1,865 | 107 | 0.1313 |
| Haifa | 26,500 | 18,021 | **240** | 8,098 | **1,148** | 0.1304 |
| Kefar Saba | 8,958 | 5,622 | 46 | 3,074 | 92 | 0.1270 |
| Ramla | 7,057 | 4,338 | 168 | 2,075 | 40 | 0.1179 |
| Modi'in - Makabim - Re'ut | 8,699 | 5,387 | 20 | 2,661 | 74 | 0.1151 |
| Gderot | 562 | 361 | 4 | 203 | 327 | 0.1112 |
| Rosh Ha'ayin | 8,802 | 5,448 | 54 | 2,683 | 23 | 0.1058 |
| Hof Ashkelon | 990 | 601 | 3 | 316 | 735 | 0.0970 |

> **delta_score** = ממוצע משוקלל של: NEW_IN_OSM (40%), MISSING_IN_OSM (30%), MISSING_IN_BANTAL (20%), SPATIAL_MISMATCH (10%). טווח 0–1.

**מסקנה**: **טבריה** בראש הדירוג — 205 מבנים חדשים ב-OSM שטרם עודכנו בבנטל (0.1874). **חיפה** ירדה למקום 5 לאחר שנרמול הסינונימים הפחית 313 כתובות שהיו דלתאות שווא (מ-1,461 ל-1,148).

---

## מודל ML — `output/ml_predictions.csv`

### ביצועים

| מדד | ערך |
|-----|-----|
| נקודות אימון | 9 מ-11 (2 מועצות אזוריות ללא התאמה דמוגרפית) |
| LOO CV R² | −0.321 |
| LOO CV MAE | 0.0183 |
| ישובים בחיזוי | 1,490 |

> **פרשנות**: עם 9 נקודות אימון, כוח הסטטיסטי מוגבל. הדירוג שימושי לסיווג **יחסי** בין ישובים — לא לחיזוי ציון מוחלט. כל פיילוט נוסף ישפר משמעותית את דיוק המודל.

### חשיבות פיצ'רים

| פיצ'ר | כיוון | פרשנות |
|--------|--------|---------|
| `log_pop` | שלילי | ישובים קטנים יותר → סיכון גבוה יותר |
| `pct_arab` | חיובי | אחוז גבוה של ערבים → OSM פחות מכוסה |
| `settlement_form` | חיובי | סוגי ישוב מסוימים → דלתאות גבוהות יותר |
| `pop_density` | חיובי | צפיפות גבוהה → יותר מבנים שחסרים |

### דוגמה: ישובי פיילוט בדירוג הכלל-ארצי

| ישוב | delta_score ממשי | ציון חזוי (0-100) |
|------|-----------------|------------------|
| Tverya (Tiberias) | 0.1874 | — |
| Lod | 0.1447 | — |
| Pardes Hana - Karkur | 0.1364 | — |

*(ישובי הפיילוט מסומנים ⭐ בגרף Scatter בטאב 7 של ה-dashboard)*

---

## קבצי פלט — מבנה עמודות

### `delta_buildings.csv`
```
delta_type | layer | source | setl_code | setl_name | ftype | osm_building_tag | area_sqm | geometry_wkt
```

### `delta_addresses.csv`
```
delta_type | layer | setl_code | setl_name | street_name | house_num | entry_ltr | distance_m
```

### `delta_summary.csv`
```
setl_code | Muni_Eng | Muni_Heb | AreaSQM | total_bantal_bldg | total_osm_bldg |
n_new_bldg | n_missing_bldg | total_bantal_addr | n_full_match | n_spatial_mismatch |
n_missing_bantal_addr | n_missing_osm_addr | osm_coverage_pct | delta_score
```

### `ml_predictions.csv`
```
risk_rank | setl_code | setl_name | religion_type | settlement_form |
population_2024 | AreaSQM | predicted_risk | risk_score_100 | is_pilot | actual_delta_score
```

---

## המלצות להמשך

1. **הרחבת הפיילוט** — כל ישוב נוסף עם delta_score ממשי ישפר את המודל
2. **שתי טבלאות סינונימים בפעולה** — `synonym.csv` ו-`STR_SYNONIMS.csv` משולבות ב-`delta_engine.py`; `MISSING_IN_BANTAL` ירד ב-774 כתובות (מ-4,092 ל-3,318) ביחס לגרסה ללא נרמול
3. **ייצוא GeoJSON** — הוספת פלט מרחבי לחפיפה עם QGIS ולהצגת שכבת דלתא
4. **עדכון אוטומטי** — הרצה מחזורית עם PBF חדש מ-Geofabrik לניטור שינויים לאורך זמן
5. **מודל שיפור** — עם >30 ישובים ניתן לעבור לGradient Boosting / Random Forest
