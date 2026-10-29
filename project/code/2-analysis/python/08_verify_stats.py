"""Langkah 7: verifikasi hasil SQL (pandas independen + kunci jawaban simulasi) dan uji statistik.

Masukan : DuckDB, data/clean/measurement_clean.csv, results/1-data-preparation/dim_spec.csv, data/raw/truth_compliance.csv.
Keluaran (results/2-analysis/): pandas_crosscheck.csv, truth_compliance_check.csv, wilson_passrate.csv, chi2_models.csv, trend_month.csv.
"""
import sys
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_ANALYSIS / "03_views.sql").read_text())
sql = con.execute("SELECT unit_id, parameter, model, month, revision, result FROM compliance_result").df()

# ---- 1. pandas independen (tanpa SQL): merge_asof per (model, parameter)
m = pd.read_csv(C.CLEAN_DIR / "measurement_clean.csv", parse_dates=["test_date"])
s = pd.read_csv(C.RES_PREP / "dim_spec.csv", parse_dates=["valid_from"])
parts = []
for (mo, pa), g in m.groupby(["model", "parameter"]):
    sg = s[(s.model == mo) & (s.parameter == pa)].sort_values("valid_from")
    parts.append(pd.merge_asof(g.sort_values("test_date"), sg[["valid_from", "revision", "lower_limit", "upper_limit"]], left_on="test_date", right_on="valid_from"))
pdv = pd.concat(parts)
pdv["pass_pd"] = (pdv.lower_limit.isna() | (pdv.value >= pdv.lower_limit)) & (pdv.upper_limit.isna() | (pdv.value <= pdv.upper_limit))
cc = sql.merge(pdv[["unit_id", "parameter", "revision", "pass_pd"]], on=["unit_id", "parameter"], suffixes=("_sql", "_pd"))
cc["same_result"] = (cc.result == "pass") == cc.pass_pd
cc["same_revision"] = cc.revision_sql == cc.revision_pd
out = pd.DataFrame([dict(check="SQL vs pandas", rows=len(cc), result_mismatch=int((~cc.same_result).sum()), revision_mismatch=int((~cc.same_revision).sum()))])
out.to_csv(C.RES_ANALYSIS / "pandas_crosscheck.csv", index=False)
assert len(cc) == len(m) and out.result_mismatch[0] == 0 and out.revision_mismatch[0] == 0

# ---- 2. kunci jawaban simulasi (truth_compliance) -> ketepatan pipeline end-to-end
t = pd.read_csv(C.RAW_DIR / "truth_compliance.csv")
tc = sql.merge(t, on=["unit_id", "parameter"], how="left")
tc["truth_pass"] = tc["pass"].astype(bool)
tc["pipe_pass"] = tc.result == "pass"
gt = pd.DataFrame([dict(rows_checked=len(tc), missing_truth=int(tc["pass"].isna().sum()), result_mismatch=int((tc.truth_pass != tc.pipe_pass).sum()),
                        revision_mismatch=int((tc.revision != tc.spec_revision).sum()), truth_fail=int((~tc.truth_pass).sum()), pipeline_fail=int((~tc.pipe_pass).sum()))])
gt.to_csv(C.RES_ANALYSIS / "truth_compliance_check.csv", index=False)

# ---- 3. interval Wilson 95% pass rate per parameter dan model (kelompok n >= MIN_N)
def wilson(k, n, z=1.96):
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return c - h, c + h

w = sql.assign(ok=sql.result == "pass").groupby(["parameter", "model"]).ok.agg(["sum", "count"]).reset_index()
w["pass_rate"] = w["sum"] / w["count"]
w[["ci_low", "ci_high"]] = [wilson(k, n) for k, n in zip(w["sum"], w["count"])]
w = w.rename(columns={"sum": "n_pass", "count": "n"})
w["n_enough"] = w.n >= C.MIN_N_PER_GROUP
w.to_csv(C.RES_ANALYSIS / "wilson_passrate.csv", index=False)

# ---- 4. chi-square antar model per parameter (apakah pass rate berbeda), dengan koreksi Holm
rows = []
for pa, g in sql.assign(ok=sql.result == "pass").groupby("parameter"):
    ct = pd.crosstab(g.model, g.ok).reindex(columns=[True, False], fill_value=0)
    chi2, p, dof, exp = stats.chi2_contingency(ct)
    rows.append(dict(parameter=pa, chi2=chi2, dof=dof, p_value=p, min_expected=exp.min(), cramers_v=np.sqrt(chi2 / ct.values.sum())))
c2 = pd.DataFrame(rows).sort_values("p_value").reset_index(drop=True)
k = len(c2)
c2["p_holm"] = np.minimum(1, np.maximum.accumulate((k - np.arange(k)) * c2.p_value))
c2["significant_holm_0_05"] = c2.p_holm < 0.05
c2.to_csv(C.RES_ANALYSIS / "chi2_models.csv", index=False)

# ---- 5. tren bulanan pass rate unit (regresi logistik sederhana lewat uji Cochran-Armitage)
u = pd.read_csv(C.RES_ANALYSIS / "month_unit.csv")
x = np.arange(len(u)); n = u.n.values; r = u.n_pass.values
pbar = r.sum() / n.sum()
T = (x * (r - n * pbar)).sum()
V = pbar * (1 - pbar) * ((n * x ** 2).sum() - (n * x).sum() ** 2 / n.sum())
z = T / np.sqrt(V)
pd.DataFrame([dict(test="Cochran-Armitage", months=len(u), z=z, p_value=2 * (1 - stats.norm.cdf(abs(z))), first_month_rate=u.pass_rate.iloc[0], last_month_rate=u.pass_rate.iloc[-1])]).to_csv(C.RES_ANALYSIS / "trend_month.csv", index=False)
print(out.to_string(index=False)); print(gt.to_string(index=False)); print(c2[["parameter", "p_value", "p_holm", "cramers_v"]].to_string(index=False))
print(pd.read_csv(C.RES_ANALYSIS / "trend_month.csv").to_string(index=False))
