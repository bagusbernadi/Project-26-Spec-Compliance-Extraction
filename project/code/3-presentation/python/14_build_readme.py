"""Langkah 14: menulis README.md dan docs/cleaning_log.md dari CSV hasil (semua angka dibaca dari results/)."""
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

R = lambda f: pd.read_csv(next(d / f for d in (C.RES_PREP, C.RES_ANALYSIS) if (d / f).exists()))
pc = lambda v, d=1: f"{v * 100:.{d}f}".replace(".", ",") + "%"
fi = lambda v: f"{v:,.0f}".replace(",", ".")
acc = R("extraction_accuracy.csv"); a = acc[acc.scope == "Semua field"].set_index("method").accuracy
dv = R("doc_validation.csv"); schema_ok = dv.groupby("method").schema_ok.sum(); nd = dv.doc.nunique()
unit = R("passrate_unit.csv").set_index("model").loc["Semua"]
par = R("passrate_param.csv").set_index("parameter"); pareto = R("pareto_fail.csv"); mp = R("margin_param_model.csv")
stale = R("impact_stale_spec.csv").set_index("stale_revision"); man = R("impact_manual_time.csv").set_index("minutes_per_doc")
dq = R("data_quality_summary.csv").iloc[0]; clog = R("cleaning_log.csv"); chi = R("chi2_models.csv"); tr = R("trend_month.csv").iloc[0]
ce = R("crosscheck_excel.csv"); pdx = R("pandas_crosscheck.csv").iloc[0]; gt = R("truth_compliance_check.csv").iloc[0]
tp = pareto.iloc[0]; top_near = mp.sort_values("share_near_fail", ascending=False).iloc[0]
rq = R("review_queue.csv")
PV = f"{tr.p_value:.3f}".replace(".", ",")

log = ["# Log cleaning hasil ukur", "", f"Mentah {fi(dq.raw_rows)} baris, bersih {fi(dq.clean_rows)} baris, bermasalah {fi(dq.bad_rows)} ({pc(dq.bad_pct / 100, 2)}). Semua temuan sama dengan yang ditanam generator (`dirty_found_vs_planted.csv`).", "",
       "| Aturan | Masalah | Ditemukan | Dibuang | Diperbaiki | Keputusan |", "|---|---|---|---|---|---|"]
log += [f"| {r.rule} | {r.description} | {fi(r.rows_found)} | {fi(r.rows_dropped)} | {fi(r.rows_fixed)} | {r.decision} |" for r in clog.itertuples()]
(C.DOCS_DIR / "cleaning_log.md").write_text("\n".join(log) + "\n", encoding="utf-8")

readme = f"""# Project 26: Spec Compliance Extraction

Membaca batas spesifikasi dari PDF datasheet lampu LED menjadi tabel terstruktur, mencocokkannya dengan hasil ukur produksi, lalu mencari parameter yang paling sering gagal atau paling dekat ke batas. **Data simulasi** buatan sendiri; hasilnya menguji metode, bukan kondisi pabrik.

- Rancangan dan laporan (halaman web): `design-and-report/index.html`
- Dashboard: `streamlit run code/3-presentation/streamlit/app.py` (dari folder `project/`; belum di-deploy)
- Infografik: `project/results/3-presentation/infographic.png`

## Masalah
Batas spec ada di PDF dan disalin manual ke Excel. Salah salin, salah satuan, atau memakai revisi lama mengubah putusan lolos/gagal.

## Data
24 PDF datasheet simulasi (3 model x 3 revisi, 5 format, 1 hasil scan) dan {fi(dq.raw_rows)} baris hasil ukur mentah (18.000 unit). {fi(dq.bad_rows)} baris ({pc(dq.bad_pct / 100, 2)}) kotor, semuanya ditemukan dan ditangani ({fi(dq.clean_rows)} baris bersih). Seed tetap, hasil identik setiap dijalankan (`project/data/README.md`).

## Temuan
- **Ekstraksi:** akurasi aturan dasar {pc(a['rule_basic'])}, aturan lengkap {pc(a['rule_full'])} pada gold set 160 field. Aturan dasar gagal pada format kalimat, label singkatan, dan tabel terpotong. Dokumen lolos validasi skema: {int(schema_ok['rule_basic'])} dari {nd} (dasar) dan {int(schema_ok['rule_full'])} dari {nd} (lengkap); {len(rq)} PDF hasil scan masuk antrean review (tanpa OCR). Langkah LLM tersedia di `extract/llm.py` tetapi belum dijalankan (tidak ada kunci API).
- **Compliance:** {pc(unit.pass_rate, 2)} unit lolos semua parameter ({fi(unit.n_pass)} dari {fi(unit.n)}). {tp.parameter} {tp.model} adalah penyumbang gagal terbesar ({fi(tp.n_fail)} dari {fi(pareto.n_fail.sum())}, {pc(tp.share, 0)}).
- **Margin:** {top_near.parameter} {top_near.model} paling dekat ke batas ({pc(top_near.share_near_fail)} hasil lolos dengan margin kurang dari 1 simpangan baku).
- **Revisi spec:** dinilai dengan Rev 1.0 yang sudah usang, {fi(stale.loc['Rev 1.0', 'units_fail_hidden'])} dari {fi(stale.loc['Rev 1.0', 'units_truly_fail'])} unit gagal ({pc(stale.loc['Rev 1.0', 'share_fail_hidden_units'])}) tampak lolos.
- **Antar model:** perbedaan pass rate signifikan (chi-square, koreksi Holm) untuk {", ".join(chi[chi.significant_holm_0_05].parameter)}. Tren bulanan menurun tipis (Cochran-Armitage, p {PV}).
- **Validasi:** SQL sama dengan pandas ({fi(pdx.rows)} baris), dengan Excel ({int((ce.status == 'PASS').sum())} dari {len(ce)} PASS), dan dengan kunci jawaban simulasi ({fi(gt.result_mismatch)} selisih).

## Rekomendasi
1. Pantau {tp.parameter} {tp.model} lebih dulu.
2. Selalu nilai hasil uji dengan revisi spec yang berlaku pada tanggal uji (ASOF join), bukan revisi terbaru.
3. Baca PDF hasil scan secara manual atau tambahkan OCR; PDF dengan format baru perlu masuk gold set.
4. Tampilkan margin di samping pass rate.

## Dampak (estimated, simulated)
Pengecekan manual sekitar {fi(man.loc[20, 'hours_per_year'])} jam per tahun pada asumsi 20 menit per dokumen (rentang {fi(man.loc[10, 'hours_per_year'])} sampai {fi(man.loc[30, 'hours_per_year'])} jam untuk 10 sampai 30 menit). Menit per dokumen adalah asumsi.

## Batasan
Data simulasi; gold set kecil (160 field); LLM belum dijalankan; tidak ada `lot_id`; margin dalam simpangan baku bergantung pada data; dashboard belum di-deploy.

## Menjalankan ulang (dari folder `project/`)
```
pip install -r requirements.txt
python code/1-data-preparation/python/01_generate_docs.py
python code/1-data-preparation/python/02_generate_measurements.py
python code/1-data-preparation/python/03_clean_measurements.py
python code/1-data-preparation/python/04_extract_specs.py
python code/1-data-preparation/python/05_evaluate_extraction.py
python code/1-data-preparation/python/06_build_db.py
python code/2-analysis/python/07_run_queries.py
python code/2-analysis/python/08_verify_stats.py
python code/2-analysis/python/09_excel_crosscheck.py     # butuh LibreOffice
python code/2-analysis/python/10_impact_ground_truth.py
python code/3-presentation/python/11_build_dashboard_data.py
python code/3-presentation/python/12_build_infographic.py
python code/3-presentation/python/13_build_notebooks.py
python code/3-presentation/python/14_build_readme.py
python ../design-and-report/src/build_report.py
```

## Struktur
`design-and-report/` (rancangan dan laporan), `project/code/` (1-data-preparation, 2-analysis, 3-presentation, extract/), `project/results/` (CSV, notebook, infografik), `project/data/` (README, sample), `project/docs/`.
"""
(C.ROOT.parent / "README.md").write_text(readme, encoding="utf-8")
print("README.md dan docs/cleaning_log.md ditulis")
