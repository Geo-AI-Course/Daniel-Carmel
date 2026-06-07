"""
ML Risk Scoring: predict delta_score for all Israeli settlements.

Input:  output/delta_summary.csv  (from delta_engine.py)
        bycode2024.csv            (demographics, utf-8-sig)
        SETEL.csv                 (pilot settlement boundaries)
        TOPO_SETEL_NAME.csv       (settlement name lookup)

Output: output/ml_predictions.csv  (all ~2000 settlements ranked by predicted risk)

Model: Ridge Regression with Leave-One-Out CV on 11 pilot settlements,
       then predict for all settlements in bycode2024.
11111
       
       """

import os
import warnings
import numpy as np
import pandas as pd
from sklearn.linear_model import RidgeCV
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.model_selection import LeaveOneOut
from sklearn.metrics import mean_absolute_error, r2_score

warnings.filterwarnings("ignore")

DATA = "."
OUT  = "output"
os.makedirs(OUT, exist_ok=True)

# ── 1. Load inputs ────────────────────────────────────────────────

print("Loading data...")

summary  = pd.read_csv(f"{OUT}/delta_summary.csv", encoding="utf-8-sig")
demo     = pd.read_csv(f"{DATA}/bycode2024.csv",   encoding="utf-8-sig")
setel    = pd.read_csv(f"{DATA}/SETEL.csv",         encoding="cp1255")
setnames = pd.read_csv(f"{DATA}/TOPO_SETEL_NAME.csv", encoding="cp1255")

# Standardize column names (Hebrew headers in bycode2024)
demo = demo.rename(columns={
    "שם יישוב":              "setl_name_demo",
    "סמל יישוב":             "setl_code_demo",
    "דת יישוב":              "religion_type",
    "סך הכל אוכלוסייה 2024": "population_2024",
    "סך הכל ישראלים 2024":   "pop_israelis",
    "יהודים ואחרים":          "pop_jewish",
    "ערבים":                  "pop_arab",
    "זרים":                   "pop_foreign",
    "צורת יישוב שוטפת":      "settlement_form",
})

# Clean population: remove commas and convert to numeric
for col in ["population_2024", "pop_israelis", "pop_jewish", "pop_arab", "pop_foreign"]:
    demo[col] = pd.to_numeric(
        demo[col].astype(str).str.replace(",", "").str.strip(), errors="coerce"
    )

demo["setl_code_demo"] = pd.to_numeric(demo["setl_code_demo"], errors="coerce")

print(f"  Demo records: {len(demo):,}   Pilot settlements: {len(summary)}")

# ── 2. Join pilot delta_summary with demographics ─────────────────

print("\nJoining pilot data with demographics...")

# summary uses CR_PNIM as setl_code; demo uses סמל יישוב (LAMAS code)
# For most cities these are the same; for regional councils they may differ.
# Primary join: on numeric code; fallback: name-based

setel["setl_code"]    = setel["CR_PNIM"].astype(int)
setel["lamas_code"]   = pd.to_numeric(setel["CR_LAMAS"], errors="coerce")
setel["Muni_Eng_up"]  = setel["Muni_Eng"].str.strip()

# Try direct code join first
pilot = summary.merge(
    demo[["setl_code_demo", "religion_type", "population_2024",
          "pop_jewish", "pop_arab", "settlement_form", "setl_name_demo"]],
    left_on="setl_code", right_on="setl_code_demo", how="left"
)

# For rows still missing demographics (regional councils with no LAMAS match),
# attempt name-based fuzzy match
missing_mask = pilot["population_2024"].isna()
if missing_mask.any():
    name_map = demo.set_index("setl_name_demo")[
        ["setl_code_demo", "religion_type", "population_2024", "pop_jewish",
         "pop_arab", "settlement_form"]
    ]
    for idx in pilot[missing_mask].index:
        eng_name = pilot.loc[idx, "Muni_Eng"]
        heb_name = pilot.loc[idx, "Muni_Heb"]
        # Try Hebrew name
        if heb_name in name_map.index:
            for col in ["religion_type", "population_2024", "pop_jewish",
                        "pop_arab", "settlement_form", "setl_code_demo"]:
                pilot.loc[idx, col] = name_map.loc[heb_name, col]

# Add area from SETEL (already in summary via setel_zones — but AreaSQM column exists)
if "AreaSQM" not in pilot.columns:
    pilot = pilot.merge(setel[["setl_code","AreaSQM"]], on="setl_code", how="left")

print(f"  Pilot rows with demographics: {pilot['population_2024'].notna().sum()} / {len(pilot)}")

# ── 3. Feature Engineering ────────────────────────────────────────

def make_features(df):
    X = pd.DataFrame()
    X["log_pop"]         = np.log1p(pd.to_numeric(df["population_2024"], errors="coerce").fillna(0))
    X["area_sqkm"]       = pd.to_numeric(df.get("AreaSQM", 0), errors="coerce").fillna(0) / 1e6
    X["pop_density"]     = (X["log_pop"] / (X["area_sqkm"] + 1e-9)).clip(upper=100)
    X["pct_arab"]        = (
        pd.to_numeric(df.get("pop_arab", 0), errors="coerce").fillna(0)
        / pd.to_numeric(df["population_2024"], errors="coerce").fillna(1).replace(0, 1)
    ).clip(0, 1)
    X["religion_type"]   = pd.to_numeric(df["religion_type"], errors="coerce").fillna(1)
    X["settlement_form"] = pd.to_numeric(df.get("settlement_form", 0), errors="coerce").fillna(0)
    # One-hot religion
    X["is_jewish"]   = (X["religion_type"] == 1).astype(float)
    X["is_mixed"]    = (X["religion_type"] == 2).astype(float)
    X["is_bedouin"]  = (X["religion_type"] == 3).astype(float)
    return X.fillna(0)


# ── 4. Train on pilot settlements ────────────────────────────────

print("\nTraining Ridge Regression (LOO CV)...")

# Drop rows with no target or no population data
train = pilot.dropna(subset=["delta_score", "population_2024"]).copy()
train = train.reset_index(drop=True)

if len(train) < 3:
    print("  WARNING: Not enough training data — skipping model training.")
    predictions_df = pd.DataFrame()
else:
    X_train = make_features(train)
    y_train = train["delta_score"].values

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("ridge",  RidgeCV(alphas=[0.01, 0.1, 1, 10, 100])),
    ])

    # LOO cross-validation
    loo = LeaveOneOut()
    y_pred_loo = np.zeros(len(train))
    for train_idx, test_idx in loo.split(X_train):
        m = Pipeline([("scaler", StandardScaler()), ("ridge", RidgeCV(alphas=[0.01,0.1,1,10,100]))])
        m.fit(X_train.iloc[train_idx], y_train[train_idx])
        y_pred_loo[test_idx] = m.predict(X_train.iloc[test_idx])

    loo_r2  = r2_score(y_train, y_pred_loo)
    loo_mae = mean_absolute_error(y_train, y_pred_loo)
    print(f"  LOO CV  R²={loo_r2:.3f}   MAE={loo_mae:.4f}")

    # Fit final model on all pilot data
    model.fit(X_train, y_train)
    train_preds = model.predict(X_train)
    print(f"  Train   R²={r2_score(y_train, train_preds):.3f}  "
          f"MAE={mean_absolute_error(y_train, train_preds):.4f}")

    # Feature coefficients (after scaling)
    feature_names = X_train.columns.tolist()
    coefs = model.named_steps["ridge"].coef_
    importance = pd.Series(coefs, index=feature_names).sort_values(key=abs, ascending=False)
    print("\nFeature coefficients (sorted by |coef|):")
    print(importance.round(4).to_string())

    # ── 5. Predict for all settlements in bycode2024 ──────────────

    print("\nPredicting for all settlements...")

    all_setl = demo.copy()
    all_setl["AreaSQM"] = 0.0  # float, no area data for non-pilot settlements

    # For pilot settlements, use actual AreaSQM from SETEL
    area_map = setel.set_index("setl_code")["AreaSQM"].to_dict()
    area_series = all_setl["setl_code_demo"].map(area_map).fillna(0.0)
    all_setl["AreaSQM"] = area_series.values

    X_all = make_features(all_setl)
    all_setl["predicted_risk"] = np.clip(model.predict(X_all), 0, None)

    # Normalize to 0–100 risk score
    max_risk = all_setl["predicted_risk"].max()
    if max_risk > 0:
        all_setl["risk_score_100"] = (all_setl["predicted_risk"] / max_risk * 100).round(1)
    else:
        all_setl["risk_score_100"] = 0.0

    all_setl = all_setl.sort_values("predicted_risk", ascending=False).reset_index(drop=True)
    all_setl["risk_rank"] = range(1, len(all_setl) + 1)

    # Flag pilot settlements
    pilot_codes = set(summary["setl_code"].dropna().astype(int))
    all_setl["is_pilot"] = all_setl["setl_code_demo"].isin(pilot_codes)
    # Attach actual delta_score for pilot settlements
    pilot_score_map = summary.set_index("setl_code")["delta_score"].to_dict()
    all_setl["actual_delta_score"] = all_setl["setl_code_demo"].map(pilot_score_map)

    out_cols = [
        "risk_rank", "setl_code_demo", "setl_name_demo", "religion_type",
        "settlement_form", "population_2024", "AreaSQM",
        "predicted_risk", "risk_score_100", "is_pilot", "actual_delta_score",
    ]
    predictions_df = all_setl[out_cols].rename(columns={
        "setl_code_demo": "setl_code",
        "setl_name_demo": "setl_name",
    })
    predictions_df.to_csv(f"{OUT}/ml_predictions.csv", index=False, encoding="utf-8-sig")

    print(f"\nTop 20 highest-risk settlements:")
    print(predictions_df.head(20)[["risk_rank","setl_name","population_2024",
                                    "risk_score_100","is_pilot"]].to_string())
    print(f"\n  Saved: output/ml_predictions.csv ({len(predictions_df):,} rows)")

    # Save feature importance for dashboard
    coef_df = importance.reset_index()
    coef_df.columns = ["feature", "coefficient"]
    coef_df.to_csv(f"{OUT}/ml_feature_importance.csv", index=False, encoding="utf-8-sig")
    print("  Saved: output/ml_feature_importance.csv")

print("\nDone!")
