"""Langkah 6: menjalankan view compliance dan semua query analisis di DuckDB; hasil tiap query ditulis ke CSV.

Masukan : spec_compliance.duckdb (dari 06_build_db.py), 2-analysis/sql/03_views.sql dan 04_queries.sql.
Keluaran: results/2-analysis/<nama_query>.csv, compliance_check.csv (pemeriksaan: setiap hasil ukur punya spec).
Q8/Q10 (spec salah): seluruh hasil ukur dinilai dengan revisi lama (Rev 1.0) lalu dibandingkan dengan revisi yang berlaku.
"""
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_ANALYSIS / "03_views.sql").read_text())

chk = con.execute("""SELECT count(*) AS n_measurement, sum((revision IS NULL)::INT) AS n_without_spec, sum((result = 'pass')::INT) AS n_pass, sum((result = 'fail')::INT) AS n_fail
                     FROM compliance_result""").df()
chk["n_units"] = con.execute("SELECT count(*) FROM unit_result").fetchone()[0]
chk.to_csv(C.RES_ANALYSIS / "compliance_check.csv", index=False)
assert chk.n_without_spec[0] == 0, "ada hasil ukur tanpa spec berlaku"

text = (C.SQL_ANALYSIS / "04_queries.sql").read_text()
parts = re.split(r"^-- name: (\S+)\s*$", text, flags=re.M)
queries = list(zip(parts[1::2], parts[2::2]))
for name, sql in queries:
    sql = sql.strip().rstrip(";")
    if "{REV}" in sql:
        for rev in ("Rev 1.0", "Rev 2.0"):
            df = con.execute(sql.replace("{REV}", rev).replace("{NEAR}", str(C.NEAR_FAIL_SD))).df()
            df.insert(0, "assumed_revision", rev)
            df.to_csv(C.RES_ANALYSIS / (name.replace("{REV}", rev.replace("Rev ", "rev").replace(".", "_")) + ".csv"), index=False)
        continue
    df = con.execute(sql.replace("{NEAR}", str(C.NEAR_FAIL_SD))).df()
    df.to_csv(C.RES_ANALYSIS / f"{name}.csv", index=False)

# sensitivitas ambang hampir gagal (Q6)
sens = []
for t in C.NEAR_FAIL_SCENARIOS:
    d = con.execute(f"""SELECT parameter, model, count(*) AS n, sum((result='pass' AND margin_sd < {t})::INT) AS n_near_fail
                        FROM compliance_result GROUP BY 1, 2 ORDER BY 1, 2""").df()
    d.insert(0, "near_fail_sd", t)
    sens.append(d)
pd.concat(sens).assign(share=lambda x: x.n_near_fail / x.n).to_csv(C.RES_ANALYSIS / "near_fail_sensitivity.csv", index=False)
print(chk.to_string(index=False)); print(len(queries), "query dijalankan")
