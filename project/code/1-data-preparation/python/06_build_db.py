"""Langkah 5: membangun database DuckDB (dim_spec, measurement, extraction_eval) dari CSV, lalu menguji constraint.

Masukan : results/1-data-preparation/dim_spec.csv, extraction_eval.csv; data/clean/measurement_clean.csv.
Keluaran: spec_compliance.duckdb (tidak di-commit), results/1-data-preparation/constraint_tests.csv, table_counts.csv.
Setiap constraint diuji dengan baris yang sengaja salah; semua harus ditolak.
"""
import os
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

if C.DB_PATH.exists():
    C.DB_PATH.unlink()
os.chdir(C.ROOT)
con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_PREP / "01_schema.sql").read_text())
con.execute((C.SQL_PREP / "02_load.sql").read_text())
counts = pd.DataFrame([(t, con.execute(f"SELECT count(*) FROM {t}").fetchone()[0]) for t in ("dim_spec", "measurement", "extraction_eval")], columns=["table", "rows"])
counts.to_csv(C.RES_PREP / "table_counts.csv", index=False)

tests = [
    ("dim_spec", "model di luar 5W/9W/12W", "INSERT INTO dim_spec VALUES ('7W','Rev 1.0','2026-03-01','cri',80,NULL,'Ra','x.pdf',1,1,1)"),
    ("dim_spec", "format revisi salah", "INSERT INTO dim_spec VALUES ('5W','R1','2026-03-01','cri',80,NULL,'Ra','x.pdf',1,1,1)"),
    ("dim_spec", "kedua batas kosong", "INSERT INTO dim_spec VALUES ('5W','Rev 9.0','2026-03-01','cri',NULL,NULL,'Ra','x.pdf',1,1,1)"),
    ("dim_spec", "batas bawah >= batas atas", "INSERT INTO dim_spec VALUES ('5W','Rev 9.0','2026-03-01','cri',90,80,'Ra','x.pdf',1,1,1)"),
    ("dim_spec", "halaman sumber 0", "INSERT INTO dim_spec VALUES ('5W','Rev 9.0','2026-03-01','cri',80,NULL,'Ra','x.pdf',0,1,1)"),
    ("dim_spec", "kunci ganda (model, revisi, parameter)", "INSERT INTO dim_spec SELECT * FROM dim_spec LIMIT 1"),
    ("measurement", "parameter tidak dikenal", "INSERT INTO measurement VALUES ('U1','2026-03-01','5W','warna',1,'x')"),
    ("measurement", "nilai kosong", "INSERT INTO measurement VALUES ('U1','2026-03-01','5W','cri',NULL,'Ra')"),
    ("measurement", "kunci ganda (unit_id, parameter)", "INSERT INTO measurement SELECT * FROM measurement LIMIT 1"),
    ("extraction_eval", "metode tidak dikenal", "INSERT INTO extraction_eval VALUES ('d','5W','Rev 1.0','tabel','cri','min','gpt','1','1',true,NULL)"),
]
rows = []
for table, desc, sql in tests:
    try:
        con.execute(sql)
        rows.append((table, desc, "DITERIMA (tidak seharusnya)"))
    except duckdb.Error as e:
        rows.append((table, desc, "ditolak"))
pd.DataFrame(rows, columns=["table", "test", "outcome"]).to_csv(C.RES_PREP / "constraint_tests.csv", index=False)
assert all(r[2] == "ditolak" for r in rows), rows
assert con.execute("SELECT count(*) FROM measurement").fetchone()[0] == counts.set_index("table").rows["measurement"], "tabel berubah setelah uji"
print(counts.to_string(index=False)); print(f"{len(tests)} uji constraint: semua ditolak")
