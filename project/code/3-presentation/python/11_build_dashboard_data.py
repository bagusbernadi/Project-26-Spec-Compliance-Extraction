"""Langkah 11: data ringkas untuk dashboard. dash_rows.csv = hasil per bulan, model, parameter, revisi; dash_units.csv = putusan unit per bulan dan model.
Di-commit supaya dashboard jalan tanpa database. Keluaran: results/3-presentation/dash_rows.csv, dash_units.csv."""
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

con = duckdb.connect(str(C.DB_PATH))
con.execute((C.SQL_ANALYSIS / "03_views.sql").read_text())
r = con.execute(f"""SELECT month, model, parameter, revision, count(*) AS n, sum((result = 'pass')::INT) AS n_pass,
                           sum((result = 'pass' AND margin_sd < {C.NEAR_FAIL_SD})::INT) AS n_near_fail
                    FROM compliance_result GROUP BY ALL ORDER BY ALL""").df()
u = con.execute("SELECT month, model, count(*) AS n, sum(unit_pass::INT) AS n_pass FROM unit_result GROUP BY ALL ORDER BY ALL").df()
r.to_csv(C.RES_PRESENT / "dash_rows.csv", index=False); u.to_csv(C.RES_PRESENT / "dash_units.csv", index=False)
assert r.n.sum() == 105939 and u.n.sum() == 18000
print(len(r), "baris dash_rows;", len(u), "baris dash_units")
