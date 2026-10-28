"""Project 26: hasil ukur lampu LED (simulasi), format panjang (long), plus kebenaran compliance. Seed tetap.

+-18.000 unit x 6 parameter = 108.000 nilai selama +-6 bulan (130 hari kerja). Putusan compliance kebenaran dihitung dari revisi spec
yang berlaku pada tanggal uji. Hasil (data/sim/): measurement.csv (dengan data kotor), truth_compliance.csv, ground_truth_meas.json.
Jalankan: python scripts/generate_measurements.py   (versi data: v1)
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from spec_data import MEAS, MODELS, PARAMS, REVS, SPEC, UNIT, rev_on

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "sim"
SEED = 26260999
DATA_VERSION = "v1"
N_UNITS, N_DAYS, START = 18_000, 130, "2026-03-02"
MODEL_P = [0.35, 0.40, 0.25]
DIRTY_RATE = 0.025
rng = np.random.default_rng(SEED)

days = pd.bdate_range(START, periods=N_DAYS)
d_idx = np.sort(rng.integers(0, N_DAYS, N_UNITS))
model = rng.choice(MODELS, N_UNITS, p=MODEL_P)
unit_id = np.array([f"LED{i + 1:06d}" for i in range(N_UNITS)])
test_date = np.array([d.strftime("%Y-%m-%d") for d in days[d_idx]])
rev = np.array([rev_on(d) for d in test_date])

recs, comp = [], []
for p in PARAMS:
    mu = np.array([MEAS[m][p][0] for m in model]); sd = np.array([MEAS[m][p][1] for m in model])
    v = rng.normal(mu, sd)
    v = np.round(v, 2 if p in ("power", "power_factor") else 1)
    lo = np.array([SPEC[m][r][p][0] if SPEC[m][r][p][0] is not None else np.nan for m, r in zip(model, rev)], dtype=float)
    hi = np.array([SPEC[m][r][p][1] if SPEC[m][r][p][1] is not None else np.nan for m, r in zip(model, rev)], dtype=float)
    ok = (np.isnan(lo) | (v >= lo)) & (np.isnan(hi) | (v <= hi))
    margin = np.fmin(np.where(np.isnan(lo), np.inf, (v - lo) / sd), np.where(np.isnan(hi), np.inf, (hi - v) / sd))
    recs.append(pd.DataFrame({"unit_id": unit_id, "test_date": test_date, "model": model, "parameter": p, "value": v, "unit": UNIT[p]}))
    comp.append(pd.DataFrame({"unit_id": unit_id, "parameter": p, "spec_revision": rev, "pass": ok, "margin_sd": np.round(margin, 2)}))
M, C = pd.concat(recs, ignore_index=True), pd.concat(comp, ignore_index=True)
truth_vals = M["value"].copy()

# data kotor (+-2,5%): kosong, teks N/A, sentinel -999, satuan salah (mW), baris ganda
M["value"] = M["value"].astype(object)
n_dirty = int(round(len(M) * DIRTY_RATE))
pick = rng.permutation(len(M))[:n_dirty]
kinds = ["blank", "text_na", "sentinel", "wrong_unit", "duplicate_row"]
dirty, dup = [], []
for k, i in enumerate(pick):
    kind = kinds[k % 5]
    if kind == "blank": M.at[i, "value"] = None
    elif kind == "text_na": M.at[i, "value"] = "N/A"
    elif kind == "sentinel": M.at[i, "value"] = -999
    elif kind == "wrong_unit":
        if M.at[i, "parameter"] == "power": M.at[i, "value"] = round(float(M.at[i, "value"]) * 1000, 1); M.at[i, "unit"] = "mW"
        else: M.at[i, "value"] = None
    else: dup.append(i)
    dirty.append([unit_id[i % N_UNITS], M.at[i, "parameter"], kind])
M["_o"] = np.arange(len(M), dtype=float)
d2 = M.loc[dup].copy(); d2["_o"] += 0.5
M = pd.concat([M, d2]).sort_values("_o").drop(columns="_o").reset_index(drop=True)

OUT.mkdir(parents=True, exist_ok=True)
M.to_csv(OUT / "measurement.csv", index=False)
C.to_csv(OUT / "truth_compliance.csv", index=False)
pr = C.groupby(["parameter"])["pass"].mean().round(4).to_dict()
mm = pd.DataFrame({"unit_id": unit_id, "model": model, "rev": rev}).set_index("unit_id")
C2 = C.join(mm, on="unit_id")
fl9 = C2[(C2.parameter == "luminous_flux") & (C2.model == "9W")].groupby("rev")["pass"].mean().round(4).to_dict()
cri = C2[C2.parameter == "cri"].groupby("model")["margin_sd"].median().to_dict()
(OUT / "ground_truth_meas.json").write_text(json.dumps({"seed": SEED, "version": DATA_VERSION, "n_units": N_UNITS, "n_values_clean": len(C), "n_rows_with_dirt": len(M),
    "pass_rate_clean": pr, "pass_rate_flux_9W_by_revision": fl9, "median_margin_sd_cri_by_model": cri, "dirty_rate": DIRTY_RATE, "dirty_types": kinds}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"measurement {len(M)} baris; pass rate 9W flux per revisi: {fl9}; margin median CRI: {cri}")
