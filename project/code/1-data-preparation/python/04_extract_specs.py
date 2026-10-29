"""Langkah 6: mengekstrak isi PDF spec dengan dua tingkat aturan (rule_basic, rule_full) dan memvalidasi dengan skema Pydantic.

Keluaran (results/1-data-preparation/): extracted_fields.csv (satu baris per field), extracted_specs.csv (satu baris per parameter per dokumen),
doc_validation.csv (lolos skema atau tidak, dan alasannya). Opsi --llm menjalankan ekstraksi Claude API (butuh ANTHROPIC_API_KEY; tidak dijalankan di sesi pembuatan).
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from extract import rules  # noqa: E402
from extract.schema import SpecDoc, SpecRow  # noqa: E402

if "--llm" in sys.argv:
    from extract import llm
    print("LLM:", llm.run_all(C.DOCS_PDF, C.RAW_DIR / "llm_cache"), "dokumen diproses")
    sys.exit(0)

manifest = pd.read_csv(C.RAW_DIR / "doc_manifest.csv")
fields, specs, valid = [], [], []
for m in manifest.itertuples():
    for method in ("rule_basic", "rule_full"):
        info, rows, status = rules.extract(C.DOCS_PDF / m.file, method)
        rec = dict(doc=m.file, method=method)
        if status == "no_text_layer":
            valid.append({**rec, "text_layer": False, "n_rows": 0, "schema_ok": False, "reason": "tanpa lapisan teks (hasil scan), tanpa OCR"})
            continue
        good, errors = [], []
        for r in rows:
            if r["parameter"] is None:
                errors.append(f"label tidak dikenal: {r['label_raw']}")
                continue
            try:
                lo = None if r["lower"] is None or np.isnan(r["lower"]) else r["lower"]
                hi = None if r["upper"] is None or np.isnan(r["upper"]) else r["upper"]
                if (r["lower"] is not None and np.isnan(r["lower"])) or (r["upper"] is not None and np.isnan(r["upper"])):
                    raise ValueError("angka tidak terbaca")
                good.append(SpecRow(parameter=r["parameter"], lower=lo, upper=hi, unit=r["unit"], page=r["page"]))
                specs.append(dict(**rec, **info, parameter=r["parameter"], lower=lo, upper=hi, unit=r["unit"], unit_source=r["unit_source"], page=r["page"], label_raw=r["label_raw"]))
                for fld, val in (("min", lo), ("max", hi), ("unit", r["unit"])):
                    fields.append(dict(**rec, parameter=r["parameter"], field=fld, value=val, page=r["page"], unit_source=r["unit_source"]))
            except (ValidationError, ValueError) as e:
                errors.append(f"{r['parameter']}: {str(e).splitlines()[-1][:80]}")
                # nilai tetap dicatat agar bisa dievaluasi terhadap gold set (kesalahan tidak disembunyikan)
                for fld, val in (("min", r["lower"]), ("max", r["upper"]), ("unit", r["unit"])):
                    fields.append(dict(**rec, parameter=r["parameter"], field=fld, value=None if (isinstance(val, float) and np.isnan(val)) else val, page=r["page"], unit_source=r["unit_source"]))
        try:
            SpecDoc(model=info["model"] or "", revision=info["revision"] or "", effective_date=info["effective_date"] or "", rows=good)
            ok, reason = not errors, "; ".join(errors)
        except ValidationError as e:
            ok = False
            reason = "; ".join(sorted({err["msg"].replace("Value error, ", "") for err in e.errors()} | set(errors)))
        valid.append({**rec, "text_layer": True, "n_rows": len(rows), "schema_ok": ok, "reason": reason})

pd.DataFrame(fields).to_csv(C.RES_PREP / "extracted_fields.csv", index=False)
pd.DataFrame(specs).to_csv(C.RES_PREP / "extracted_specs.csv", index=False)
dv = pd.DataFrame(valid)
dv.to_csv(C.RES_PREP / "doc_validation.csv", index=False)
print(dv.groupby("method").agg(dokumen=("doc", "count"), lolos_skema=("schema_ok", "sum")).to_string())
