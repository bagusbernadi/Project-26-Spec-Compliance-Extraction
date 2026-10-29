"""Langkah 4 (Q13): membersihkan hasil ukur mentah dan mencatat keputusan.

Masukan : data/raw/measurement.csv (108.540 baris, dengan data kotor), data/raw/truth_dirty.csv (hanya untuk mencocokkan temuan dengan yang ditanam).
Keluaran: data/clean/measurement_clean.csv, results/1-data-preparation/cleaning_log.csv, data_quality_summary.csv, dirty_found_vs_planted.csv.
Aturan (urut): R1 baris ganda dibuang; R2 nilai kosong dibuang; R3 teks "N/A" dibuang; R4 nilai sentinel -999 dibuang;
R5 satuan mW pada power dikonversi ke W (nilai dibagi 1.000); R6 satuan lain yang tidak sesuai kamus dibuang.
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402
from spec_data import UNIT  # noqa: E402

raw = pd.read_csv(C.RAW_DIR / "measurement.csv", keep_default_na=False, dtype=str)
truth_dirty = pd.read_csv(C.RAW_DIR / "truth_dirty.csv", keep_default_na=False)
n_raw = len(raw)
log = []


def step(rule, desc, found, dropped, fixed, decision):
    log.append(dict(rule=rule, description=desc, table="measurement", rows_found=int(found), rows_dropped=int(dropped), rows_fixed=int(fixed), decision=decision))


df = raw.copy()
df["row_raw"] = np.arange(len(df))
# R1 baris ganda: kunci (unit_id, parameter); baris pertama dipertahankan, salinannya dibuang
dup = df.duplicated(subset=["unit_id", "parameter"], keep="first")
step("R1", "Baris ganda (unit_id dan parameter sama, isi identik)", dup.sum(), dup.sum(), 0, "Dibuang; baris pertama dipertahankan")
assert df[dup].merge(df[~dup], on=["unit_id", "parameter"], suffixes=("_dup", "_ori")).pipe(lambda m: ((m.value_dup == m.value_ori) & (m.test_date_dup == m.test_date_ori)).all())
df = df[~dup]
# R2 nilai kosong
blank = df.value.str.strip() == ""
step("R2", "Nilai kosong", blank.sum(), blank.sum(), 0, "Dibuang; tidak ada dasar untuk menebak nilai")
df = df[~blank]
# R3 teks N/A
na = df.value.str.upper().isin(["N/A", "NA", "NULL", "-"])
step("R3", "Nilai berupa teks N/A", na.sum(), na.sum(), 0, "Dibuang")
df = df[~na]
# R4 sentinel
num = pd.to_numeric(df.value, errors="coerce")
sent = num == -999
step("R4", "Nilai sentinel -999", sent.sum(), sent.sum(), 0, "Dibuang")
df, num = df[~sent], num[~sent]
assert num.notna().all(), "masih ada nilai bukan angka"
df = df.assign(value=num.astype(float))
# R5 satuan mW pada power -> W
mw = (df.unit == "mW") & (df.parameter == "power")
df.loc[mw, "value"] = df.loc[mw, "value"] / 1000
df.loc[mw, "unit"] = "W"
step("R5", "Power dalam mW (nilai 1.000 kali lebih besar)", mw.sum(), 0, mw.sum(), "Dikonversi ke W (dibagi 1.000)")
# R6 satuan lain tidak sesuai kamus
bad_unit = df.apply(lambda r: r.unit != UNIT[r.parameter], axis=1)
step("R6", "Satuan tidak sesuai kamus parameter (selain mW pada power)", bad_unit.sum(), bad_unit.sum(), 0, "Dibuang")
df = df[~bad_unit]
df = df.sort_values("row_raw").drop(columns="row_raw").reset_index(drop=True)
df["round_note"] = ""
df = df.drop(columns="round_note")
df.to_csv(C.CLEAN_DIR / "measurement_clean.csv", index=False)

# ---- ringkasan kualitas dan pencocokan dengan yang ditanam
planted = truth_dirty.effect.value_counts().to_dict()
found = {"duplicate": int(dup.sum()), "blank": int(blank.sum()), "text_na": int(na.sum()), "sentinel": int(sent.sum()), "mW": int(mw.sum())}
# blank yang ditemukan = blank langsung + wrong_unit pada parameter bukan power (terlihat sebagai kosong)
cmp = pd.DataFrame([
    ("duplicate", "Baris ganda", planted.get("duplicate_row", 0), found["duplicate"]),
    ("blank", "Nilai kosong (termasuk kolom satuan salah yang nilainya kosong)", planted.get("blank", 0) + planted.get("wrong_unit_blank", 0), found["blank"]),
    ("text_na", "Teks N/A", planted.get("text_na", 0), found["text_na"]),
    ("sentinel", "Sentinel -999", planted.get("sentinel", 0), found["sentinel"]),
    ("mW", "Power dalam mW", planted.get("wrong_unit", 0), found["mW"]),
], columns=["issue", "description", "planted", "found"])
cmp["match"] = cmp.planted == cmp.found
cmp.to_csv(C.RES_PREP / "dirty_found_vs_planted.csv", index=False)
assert cmp.match.all(), cmp

bad_rows = int(cmp.found.sum())
summary = pd.DataFrame([dict(table="measurement", raw_rows=n_raw, clean_rows=len(df), bad_rows=bad_rows, bad_pct=round(bad_rows / n_raw * 100, 4),
                             dropped=int(dup.sum() + blank.sum() + na.sum() + sent.sum() + bad_unit.sum()), fixed=int(mw.sum()))])
summary.to_csv(C.RES_PREP / "data_quality_summary.csv", index=False)
pd.DataFrame(log).to_csv(C.RES_PREP / "cleaning_log.csv", index=False)
per_param = df.groupby("parameter").size().reindex(C.PARAMS).rename("clean_rows").reset_index()
per_param["raw_rows"] = raw.groupby("parameter").size().reindex(C.PARAMS).values
per_param.to_csv(C.RES_PREP / "rows_per_parameter.csv", index=False)
print(f"mentah {n_raw}, bersih {len(df)}, bermasalah {bad_rows} ({bad_rows / n_raw * 100:.2f}%); semua ditemukan = ditanam")
