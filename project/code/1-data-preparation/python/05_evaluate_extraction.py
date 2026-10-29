"""Langkah 7 (Q1-Q3, Q12): membandingkan hasil ekstraksi dengan gold set dan kebenaran spec, lalu membuat tabel spec (dim_spec) dengan voting antar format.

Keluaran (results/1-data-preparation/): extraction_eval.csv (satu field per metode), extraction_accuracy.csv, extraction_doc_eval.csv,
extraction_errors.csv (Pareto jenis kesalahan), review_queue.csv, dim_spec.csv (spec hasil voting), spec_conflicts.csv.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from extract.llm import cache_to_fields  # noqa: E402

man = pd.read_csv(C.RAW_DIR / "doc_manifest.csv").rename(columns={"file": "doc"})
fmt = man.set_index("doc").format.str.replace("_scan", "").to_dict()
gold = pd.read_csv(C.RAW_DIR / "gold_set.csv", keep_default_na=False).rename(columns={"file": "doc"})
truth = pd.read_csv(C.RAW_DIR / "dim_spec_truth.csv", keep_default_na=False)
ext = pd.read_csv(C.RES_PREP / "extracted_fields.csv", keep_default_na=False)
llm = cache_to_fields(C.RAW_DIR / "llm_cache")
if len(llm):
    ext = pd.concat([ext, llm], ignore_index=True)
methods = list(dict.fromkeys(ext.method))
dv = pd.read_csv(C.RES_PREP / "doc_validation.csv", keep_default_na=False)
dv["schema_ok"] = dv.schema_ok.astype(str).str.lower() == "true"
page_full = ext[ext.method == "rule_full"].drop_duplicates(["doc", "parameter"]).set_index(["doc", "parameter"]).page.to_dict()


def same(a, b, field):
    if field == "unit":
        return str(a) == str(b)
    try:
        return abs(float(a) - float(b)) < 1e-9
    except (TypeError, ValueError):
        return False


rows = []
for method in methods:
    e = ext[ext.method == method].drop_duplicates(["doc", "parameter", "field"]).set_index(["doc", "parameter", "field"])
    for g in gold.itertuples():
        key = (g.doc, g.parameter, g.field)
        got = e.value.get(key, None)
        missing = key not in e.index or (g.field != "unit" and (got == "" or pd.isna(got)))
        ok = (not missing) and same(got, g.value, g.field)
        err = ""
        if not ok:
            f = fmt[g.doc]
            if missing:
                err = {"teks": "Format kalimat (bukan tabel)", "ringkas": "Label singkatan tidak dikenal", "terpotong": "Tabel terpotong ke halaman berikutnya"}.get(f, "Tidak terbaca")
                if f == "terpotong" and page_full.get((g.doc, g.parameter), 1) < 2:
                    err = "Tidak terbaca"
            else:
                err = "Satuan salah" if g.field == "unit" else "Angka salah"
        rows.append(dict(doc=g.doc, model=g.model, revision=g.revision, format=fmt[g.doc], parameter=g.parameter, field=g.field, method=method,
                         extracted_value="" if missing else got, label_value=g.value, is_correct=bool(ok), error_type=err))
ev = pd.DataFrame(rows)
ev.to_csv(C.RES_PREP / "extraction_eval.csv", index=False)

acc = []
for m, d in ev.groupby("method"):
    acc.append(dict(method=m, scope="Semua field", group="semua", n=len(d), correct=int(d.is_correct.sum())))
    for scope, col in (("Jenis field", "field"), ("Format dokumen", "format"), ("Parameter", "parameter")):
        for k, dd in d.groupby(col):
            acc.append(dict(method=m, scope=scope, group=k, n=len(dd), correct=int(dd.is_correct.sum())))
    # parameter terbaca (ada hasil untuk parameter di dokumen itu) dan batas (min+max)
    pp = d.groupby(["doc", "parameter"]).extracted_value.apply(lambda s: (s != "").any())
    acc.append(dict(method=m, scope="Tingkat", group="parameter terbaca", n=len(pp), correct=int(pp.sum())))
    lim = d[d.field.isin(["min", "max"])]
    acc.append(dict(method=m, scope="Tingkat", group="batas (min dan max)", n=len(lim), correct=int(lim.is_correct.sum())))
    un = d[d.field == "unit"]
    acc.append(dict(method=m, scope="Tingkat", group="satuan", n=len(un), correct=int(un.is_correct.sum())))
    dd = d.groupby("doc").is_correct.all()
    acc.append(dict(method=m, scope="Dokumen", group="semua field gold benar", n=len(dd), correct=int(dd.sum())))
acc = pd.DataFrame(acc)
acc["accuracy"] = acc.correct / acc.n
acc.to_csv(C.RES_PREP / "extraction_accuracy.csv", index=False)

err = ev[~ev.is_correct].groupby(["method", "error_type"]).size().rename("n").reset_index().sort_values(["method", "n"], ascending=[True, False])
err["share"] = err.n / err.groupby("method").n.transform("sum")
err["cum_share"] = err.groupby("method").share.cumsum()
err.to_csv(C.RES_PREP / "extraction_errors.csv", index=False)

# ---- evaluasi per dokumen terhadap kebenaran spec lengkap (termasuk tanda '-' = tanpa batas)
tr = truth.copy()
tr["limit_min"] = pd.to_numeric(tr.limit_min, errors="coerce")
tr["limit_max"] = pd.to_numeric(tr.limit_max, errors="coerce")
spec = pd.read_csv(C.RES_PREP / "extracted_specs.csv", keep_default_na=False)
docrows = []
for m in methods:
    for d in man.itertuples():
        t = tr[(tr.model == d.model) & (tr.revision == d.revision)].set_index("parameter")
        s = spec[(spec.method == m) & (spec.doc == d.doc)].drop_duplicates("parameter").set_index("parameter")
        n_ok = 0
        for p in C.PARAMS:
            if p in s.index:
                lo, hi = pd.to_numeric(s.loc[p, "lower"], errors="coerce"), pd.to_numeric(s.loc[p, "upper"], errors="coerce")
                good = (np.isnan(lo) and np.isnan(t.loc[p, "limit_min"]) or (not np.isnan(lo) and abs(lo - t.loc[p, "limit_min"]) < 1e-9)) and \
                       (np.isnan(hi) and np.isnan(t.loc[p, "limit_max"]) or (not np.isnan(hi) and abs(hi - t.loc[p, "limit_max"]) < 1e-9)) and \
                       str(s.loc[p, "unit"]) == str(t.loc[p, "unit"])
                n_ok += bool(good)
        v = dv[(dv.doc == d.doc) & (dv.method == m)].iloc[0]
        g = ev[(ev.doc == d.doc) & (ev.method == m)]
        docrows.append(dict(doc=d.doc, model=d.model, revision=d.revision, format=fmt[d.doc], method=m, text_layer=bool(v.text_layer), schema_ok=bool(v.schema_ok),
                            gold_fields=len(g), gold_correct=int(g.is_correct.sum()), params_exact=n_ok, exact_vs_truth=n_ok == 6, reason=v.reason))
de = pd.DataFrame(docrows)
de["needs_review"] = ~de.schema_ok
de.to_csv(C.RES_PREP / "extraction_doc_eval.csv", index=False)

# ---- dim_spec: voting antar format (hanya dokumen rule_full yang lolos skema); beda antar format masuk spec_conflicts.csv
good = spec[(spec.method == "rule_full") & spec.doc.isin(de[(de.method == "rule_full") & de.schema_ok].doc)].copy()
good["fmt"] = good.doc.map(fmt)
for c in ("lower", "upper"):
    good[c] = pd.to_numeric(good[c], errors="coerce")
dim, conf = [], []
for (mo, rev, p), g in good.groupby(["model", "revision", "parameter"]):
    combos = g.assign(k=list(zip(g.lower.fillna(-1e18), g.upper.fillna(-1e18), g.unit))).groupby("k").doc.apply(list)
    best = max(combos.items(), key=lambda kv: (len(kv[1]), -sorted(combos.index).index(kv[0])))
    chosen = g[g.doc.isin(best[1])].sort_values("fmt", key=lambda s: s.map({"tabel": 0, "ringkas": 1, "terpotong": 2, "teks": 3})).iloc[0]
    if len(combos) > 1:
        conf.append(dict(model=mo, revision=rev, parameter=p, n_docs=len(g), variants=len(combos)))
    eff = g.effective_date.iloc[0]
    dim.append(dict(model=mo, revision=rev, valid_from=eff, parameter=p, lower_limit=chosen.lower, upper_limit=chosen.upper, unit=chosen.unit,
                    source_doc=chosen.doc, source_page=int(chosen.page), n_docs_agree=len(best[1]), n_docs=len(g)))
dim = pd.DataFrame(dim)
dim.to_csv(C.RES_PREP / "dim_spec.csv", index=False)
pd.DataFrame(conf, columns=["model", "revision", "parameter", "n_docs", "variants"]).to_csv(C.RES_PREP / "spec_conflicts.csv", index=False)
assert len(dim) == 54, len(dim)

rq = de[(de.method == "rule_full") & de.needs_review][["doc", "model", "revision", "format", "reason"]].copy()
rq["reason"] = rq.reason.replace("", "gagal validasi skema")
rq.to_csv(C.RES_PREP / "review_queue.csv", index=False)
print(acc[(acc.scope.isin(["Semua field", "Tingkat", "Dokumen"]))].to_string(index=False))
print(err.to_string(index=False))
print("dim_spec", len(dim), "baris; konflik antar format:", len(conf), "; antrean review rule_full:", len(rq))
