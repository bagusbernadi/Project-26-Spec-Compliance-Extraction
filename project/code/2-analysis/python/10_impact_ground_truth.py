"""Langkah 8: dampak. (a) waktu pengecekan manual spec yang dihemat (skenario menit per dokumen, ASUMSI), (b) risiko spec usang: hasil ukur yang
tampak lolos kalau dinilai dengan revisi lama padahal gagal menurut revisi berlaku (proxy Q10), (c) ekstraksi rule_basic vs rule_full pada putusan.
Masukan: DuckDB, extraction_accuracy.csv. Keluaran (results/2-analysis/): impact_manual_time.csv, impact_stale_spec.csv."""
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

n_docs = len(pd.read_csv(C.RAW_DIR / "doc_manifest.csv"))
rows = []
for mins in C.MANUAL_MIN_SCENARIOS:
    per_period = n_docs * mins / 60
    rows.append(dict(minutes_per_doc=mins, docs_in_data=n_docs, hours_in_data_period=per_period, hours_per_year=per_period * C.DOCS_PER_YEAR_FACTOR, basis="asumsi menit/dokumen; data sekitar 6 bulan x2"))
pd.DataFrame(rows).to_csv(C.RES_ANALYSIS / "impact_manual_time.csv", index=False)

con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_ANALYSIS / "03_views.sql").read_text())
out = []
for rev in ("Rev 1.0", "Rev 2.0"):
    d = con.execute(f"""
      WITH f AS (SELECT m.unit_id, m.parameter, (s.lower_limit IS NULL OR m.value >= s.lower_limit) AND (s.upper_limit IS NULL OR m.value <= s.upper_limit) AS ok
                 FROM measurement m JOIN dim_spec s ON m.model = s.model AND m.parameter = s.parameter AND s.revision = '{rev}'),
      c AS (SELECT unit_id, parameter, result FROM compliance_result),
      j AS (SELECT c.unit_id, c.parameter, c.result, f.ok FROM c JOIN f USING (unit_id, parameter)),
      u AS (SELECT unit_id, bool_and(result = 'pass') AS true_pass, bool_and(ok) AS stale_pass FROM j GROUP BY unit_id)
      SELECT '{rev}' AS stale_revision, count(*) AS n_units, sum((NOT true_pass)::INT) AS units_truly_fail,
             sum((NOT true_pass AND stale_pass)::INT) AS units_fail_hidden, sum((true_pass AND NOT stale_pass)::INT) AS units_false_alarm,
             (SELECT sum((result='fail')::INT) FROM j) AS rows_truly_fail,
             (SELECT sum((result='fail' AND ok)::INT) FROM j) AS rows_fail_hidden
      FROM u""").df()
    out.append(d)
st = pd.concat(out)
st["share_fail_hidden_units"] = st.units_fail_hidden / st.units_truly_fail
st["share_fail_hidden_rows"] = st.rows_fail_hidden / st.rows_truly_fail
st.to_csv(C.RES_ANALYSIS / "impact_stale_spec.csv", index=False)
print(pd.read_csv(C.RES_ANALYSIS / "impact_manual_time.csv").to_string(index=False)); print(st.T.to_string())

# ---- lima fakta yang ditanam vs temuan (Design bagian 4); angka fakta diambil dari data, bukan ditulis tangan
gtd = __import__("json").loads((C.RAW_DIR / "ground_truth_docs.json").read_text(encoding="utf-8"))
mp = pd.read_csv(C.RES_ANALYSIS / "margin_param_model.csv")
rv = pd.read_csv(C.RES_ANALYSIS / "revision_param_model.csv")
er = pd.read_csv(C.RES_PREP / "extraction_errors.csv")
dq = pd.read_csv(C.RES_PREP / "data_quality_summary.csv").iloc[0]
cmpd = pd.read_csv(C.RES_PREP / "dirty_found_vs_planted.csv")
rq = pd.read_csv(C.RES_PREP / "review_queue.csv")
cri = mp[mp.parameter == "cri"].set_index("model")
f1 = cri.median_margin_sd.idxmin() == "12W" and (mp.sort_values("median_margin_sd").iloc[0][["parameter", "model"]].tolist() == ["cri", "12W"])
fl = rv[(rv.model == "9W") & (rv.parameter == "luminous_flux")].set_index("revision")
f2 = fl.loc["Rev 1.0", "pass_rate"] == 1.0 and fl.loc["Rev 2.0", "pass_rate"] < fl.loc["Rev 1.0", "pass_rate"]
sp = pd.read_csv(C.RES_PREP / "dim_spec.csv")
lim = sp[(sp.model == "9W") & (sp.parameter == "luminous_flux")].set_index("revision").lower_limit
e_b = er[er.method == "rule_basic"].set_index("error_type").n
f3 = {"Format kalimat (bukan tabel)", "Label singkatan tidak dikenal"} <= set(e_b.index)
f4 = len(rq) == 1 and rq.doc.iloc[0] == "LED_9W_Rev2.0_teks_scan.pdf" and "Tabel terpotong ke halaman berikutnya" in e_b.index
f5 = bool(cmpd.match.all()) and 2.0 <= dq.bad_pct <= 3.0
facts = pd.DataFrame([
    (1, "CRI pada model 12W paling dekat ke batas", f"median margin CRI 12W {cri.loc['12W', 'median_margin_sd']:.2f} simpangan baku (5W {cri.loc['5W', 'median_margin_sd']:.2f}, 9W {cri.loc['9W', 'median_margin_sd']:.2f}); pass rate {cri.loc['12W', 'pass_rate'] * 100:.1f}%", "Sesuai" if f1 else "Tidak sesuai"),
    (2, "Revisi spec menaikkan batas minimal luminous flux 9W", f"batas {lim['Rev 1.0']:.0f} lm (Rev 1.0) menjadi {lim['Rev 2.0']:.0f} lm (Rev 2.0); pass rate 9W flux {fl.loc['Rev 1.0', 'pass_rate'] * 100:.1f}% menjadi {fl.loc['Rev 2.0', 'pass_rate'] * 100:.1f}%", "Sesuai" if f2 else "Tidak sesuai"),
    (3, "Satuan dan simbol beragam antar format", f"aturan dasar gagal pada {int(e_b['Format kalimat (bukan tabel)'])} field kalimat dan {int(e_b['Label singkatan tidak dikenal'])} field singkatan; aturan lengkap membaca semuanya", "Sesuai" if f3 else "Tidak sesuai"),
    (4, "Tabel terpotong dan satu PDF hasil scan", f"{int(e_b['Tabel terpotong ke halaman berikutnya'])} field gagal pada tabel terpotong; PDF scan {rq.doc.iloc[0]} masuk antrean review", "Sesuai" if f4 else "Tidak sesuai"),
    (5, "Sekitar 2–3% hasil ukur kotor", f"{dq.bad_rows:.0f} dari {dq.raw_rows:.0f} baris ({dq.bad_pct:.2f}%); semua jenis ditemukan sama dengan yang ditanam", "Sesuai" if f5 else "Tidak sesuai"),
], columns=["fact_no", "fakta", "ditemukan", "hasil"])
facts.to_csv(C.RES_ANALYSIS / "ground_truth_check.csv", index=False)
print(facts[["fact_no", "hasil"]].to_string(index=False))

# ---- Q13: apakah pass rate berubah jika data kotor diperlakukan berbeda (tiga perlakuan)
raw = pd.read_csv(C.RAW_DIR / "measurement.csv", keep_default_na=False, dtype=str)
spec = pd.read_csv(C.RES_PREP / "dim_spec.csv", parse_dates=["valid_from"])


def judge(df):
    """Putusan per baris (merge_asof ke revisi berlaku); df punya model, parameter, test_date, value (float; NaN dihitung gagal)."""
    out = []
    for (mo, pa), g in df.groupby(["model", "parameter"]):
        sg = spec[(spec.model == mo) & (spec.parameter == pa)].sort_values("valid_from")
        j = pd.merge_asof(g.sort_values("test_date"), sg[["valid_from", "lower_limit", "upper_limit"]], left_on="test_date", right_on="valid_from")
        ok = (j.lower_limit.isna() | (j.value >= j.lower_limit)) & (j.upper_limit.isna() | (j.value <= j.upper_limit)) & j.value.notna()
        out.append(j.assign(ok=ok))
    return pd.concat(out)


raw["test_date"] = pd.to_datetime(raw.test_date)
raw["value_num"] = pd.to_numeric(raw.value, errors="coerce")
naive = raw.assign(value=raw.value_num)                                                   # A: mentah apa adanya (kosong, N/A -> gagal; -999 dan mW dibaca apa adanya)
dedup = raw.drop_duplicates(["unit_id", "parameter"])
dropall = dedup[(dedup.value_num.notna()) & (dedup.value_num != -999) & (dedup.unit == dedup.parameter.map(__import__("spec_data").UNIT))].assign(value=lambda d: d.value_num)  # B: semua baris bermasalah dibuang
clean = pd.read_csv(C.CLEAN_DIR / "measurement_clean.csv", parse_dates=["test_date"])     # C: sesuai log (mW dikonversi) = dipakai
rows = []
for name, d in (("A. Mentah apa adanya", naive), ("B. Baris bermasalah dibuang semua", dropall), ("C. Cleaning sesuai log (dipakai)", clean)):
    j = judge(d)
    c12 = j[(j.parameter == "cri") & (j.model == "12W")]
    rows.append(dict(perlakuan=name, n_rows=len(j), pass_rate=j.ok.mean(), n_fail=int((~j.ok).sum()), cri_12w_pass_rate=c12.ok.mean(),
                     top_fail_param=j[~j.ok].groupby("parameter").size().idxmax()))
pd.DataFrame(rows).to_csv(C.RES_ANALYSIS / "sensitivity_cleaning.csv", index=False)
print(pd.DataFrame(rows).to_string(index=False))
