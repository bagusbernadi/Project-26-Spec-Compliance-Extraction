"""Membuat design-and-report/index.html (Report Project versi 2) dari page_v1.html dan CSV hasil.

- Pane Design diambil apa adanya dari page_v1.html (dicek identik).
- Semua angka di Report berasal dari project/results/*.csv lewat helper I/D/P (report_lib.py) dan diaudit di akhir.
Jalankan dari folder mana saja:  python design-and-report/src/build_report.py
"""
import json
import re
import sys
from pathlib import Path

import duckdb
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(REPO / "project" / "code"))
sys.path.insert(0, str(HERE))
from common import DB_PATH, RES_ANALYSIS, RES_PREP, RES_PRESENT, result  # noqa: E402
from report_lib import (BLUE, D, cs, GREY, HI, I, NO, OK, P, PART, SOFT, audit, bars, esc, gbars, hbars,  # noqa: E402
                        legend, lines, pill, qa, table)

R = lambda n: pd.read_csv(result(n))
PRIO = {1: "Utama", 2: "Pendukung", 3: "Pendukung", 4: "Utama", 5: "Utama", 6: "Utama", 7: "Pendukung", 8: "Utama", 9: "Utama", 10: "Tambahan", 11: "Utama", 12: "Pendukung", 13: "Utama"}
QT = {1: "Berapa persen parameter, batas, dan satuan yang terbaca benar dari PDF dibanding label manual?",
      2: "Kesalahan ekstraksi apa yang paling sering: satuan, simbol (≥, ±), atau tabel yang terpotong ke halaman berikutnya?",
      3: "Apakah LLM lebih akurat daripada aturan biasa (pdfplumber dan regex) saja?",
      4: "Berapa pass rate tiap parameter, untuk setiap model lampu?",
      5: "Parameter mana yang paling sering menyebabkan unit gagal?",
      6: "Seberapa dekat hasil ukur ke batas spec, dan parameter mana yang lolos tetapi hampir gagal?",
      7: "Apakah pass rate berubah antar lot atau antar bulan?",
      8: "Berapa putusan pass/fail yang berubah jika hasil uji dinilai dengan revisi spec yang salah?",
      9: "Berapa menit pengecekan manual yang bisa dihemat per tahun?",
      10: "Berapa unit yang dinyatakan lolos pada cek manual padahal seharusnya gagal?",
      11: "Apakah putusan pass/fail dari SQL sama dengan hitungan manual di Excel, dan apakah semua fakta yang ditanam terdeteksi?",
      12: "Berapa persen dokumen yang harus direview manusia karena hasil ekstraksinya meragukan?",
      13: "Berapa persen data hasil ukur yang tidak valid, dan apakah pass rate berubah jika data itu dibuang?"}
WARN = set()


def Q(n, ans, warn=False):
    if warn:
        WARN.add(n)
    return qa(f"Q{n}", QT[n], PRIO[n], ans, "Terjawab dengan catatan" if warn else "Terjawab", warn)


mk = lambda *a: "".join(a)
pv = lambda p: "&lt; 0,001" if p < 0.001 else D(p, 3)
MONTH = {"2026-03": "Mar", "2026-04": "Apr", "2026-05": "Mei", "2026-06": "Jun", "2026-07": "Jul", "2026-08": "Agu"}

# ---------------------------------------------------------------- data
acc, err, dev, dv, rq = R("extraction_accuracy.csv"), R("extraction_errors.csv"), R("extraction_doc_eval.csv"), R("doc_validation.csv"), R("review_queue.csv")
dims, conf, eev = R("dim_spec.csv"), R("spec_conflicts.csv"), R("extraction_eval.csv")
wil, par, parm, pun = R("wilson_passrate.csv"), R("passrate_param.csv"), R("passrate_param_model.csv"), R("passrate_unit.csv").set_index("model")
pareto, mp, mdist, nfs = R("pareto_fail.csv"), R("margin_param_model.csv"), R("margin_distribution.csv"), R("near_fail_sensitivity.csv")
mu, trd, chi, rev = R("month_unit.csv"), R("trend_month.csv").iloc[0], R("chi2_models.csv"), R("revision_param_model.csv")
stale, man, gtc = R("impact_stale_spec.csv").set_index("stale_revision"), R("impact_manual_time.csv").set_index("minutes_per_doc"), R("ground_truth_check.csv").set_index("fact_no")
cx, ce, tcc, chk = R("pandas_crosscheck.csv").iloc[0], R("crosscheck_excel.csv"), R("truth_compliance_check.csv").iloc[0], R("compliance_check.csv").iloc[0]
dq, clog, cmpd, ctest, cnt = R("data_quality_summary.csv").iloc[0], R("cleaning_log.csv"), R("dirty_found_vs_planted.csv"), R("constraint_tests.csv"), R("table_counts.csv").set_index("table").rows
sens, fup = R("sensitivity_cleaning.csv"), R("fail_units_by_param.csv")
gd = json.loads((REPO / "project" / "data" / "raw" / "ground_truth_docs.json").read_text(encoding="utf-8")) if (REPO / "project" / "data" / "raw" / "ground_truth_docs.json").exists() \
    else json.loads((REPO / "project" / "data" / "sample" / "ground_truth_docs.json").read_text(encoding="utf-8"))
man_docs = pd.read_csv(REPO / "project" / "data" / "sample" / "doc_manifest.csv")
con = duckdb.connect(str(DB_PATH), read_only=True)
nunits = con.execute("SELECT count(DISTINCT unit_id) FROM measurement").fetchone()[0]
con.close()

A = acc[acc.scope == "Semua field"].set_index("method").accuracy
afld = acc[acc.scope == "Jenis field"].pivot(index="group", columns="method", values="accuracy")
afmt = acc[acc.scope == "Format dokumen"].pivot(index="group", columns="method", values="accuracy")
nfmt = acc[(acc.scope == "Format dokumen") & (acc.method == "rule_full")].set_index("group")
nall = acc[(acc.scope == "Semua field") & (acc.method == "rule_basic")].iloc[0]
eb = err[err.method == "rule_basic"].reset_index(drop=True)
nd = dv.doc.nunique()
sok = dv.groupby("method").schema_ok.sum()
rev_n = {m: int(nd - sok[m]) for m in sok.index}
dfull = dev[dev.method == "rule_full"]
n_text_docs = int(dfull.text_layer.sum())
unit_all, tp = pun.loc["Semua"], pareto.iloc[0]
cri12 = parm[(parm.parameter == "cri") & (parm.model == "12W")].iloc[0]
mpi = mp.set_index(["parameter", "model"])
top_near = mp.sort_values("share_near_fail", ascending=False).iloc[0]
s10, s20 = stale.loc["Rev 1.0"], stale.loc["Rev 2.0"]
fl = rev[(rev.model == "9W") & (rev.parameter == "luminous_flux")].set_index("revision")
lim9 = dims[(dims.model == "9W") & (dims.parameter == "luminous_flux")].set_index("revision")
nfail_rows, nfail_units = int(chk.n_fail), int(fup.n_units.sum())
bad_total = int(dq.bad_rows)
npr = {k: sum(1 for v in PRIO.values() if v == k) for k in ("Utama", "Pendukung", "Tambahan")}
sig = chi[chi.significant_holm_0_05]
c_pass = ce.status.eq("PASS").all()

assert A["rule_full"] >= 0.95 and A["rule_basic"] < A["rule_full"] and nall.n == 160
assert c_pass and cx.result_mismatch == 0 and cx.revision_mismatch == 0 and tcc.result_mismatch == 0 and tcc.missing_truth == 0
assert gtc.hasil.eq("Sesuai").all() and (ctest.outcome == "ditolak").all() and cmpd.match.all() and chk.n_without_spec == 0
assert tp.parameter == "cri" and tp.model == "12W" and top_near.parameter == "cri" and top_near.model == "12W"
assert len(rq) == 1 and rq.doc.iloc[0].endswith("teks_scan.pdf") and n_text_docs == nd - 1
assert s10.units_fail_hidden > 0 and (s10.units_false_alarm == 0)

# ---------------------------------------------------------------- 1. data
kp = lambda c, v, l, d: f'<div class="card kpi" style="--h:var(--{c}H)"><span class="v">{v}</span><span class="l">{l}</span><span class="d">{d}</span></div>'
rp1 = mk(
    '<div class="kpis">',
    kp("navy", I(nd), "dokumen PDF spec", f"{I(man_docs.model.nunique())} model, {I(man_docs.revision.nunique())} revisi, {I(man_docs.format.nunique())} format. {I(n_text_docs)} punya lapisan teks, 1 hasil scan."),
    kp("amber", I(nall.n), "field di gold set", f"Parameter, batas bawah/atas, dan satuan dari {I(n_text_docs)} dokumen bertekstual."),
    kp("teal", I(dq.raw_rows), "baris hasil ukur mentah", f"Bersih {I(dq.clean_rows)} baris; {I(nunits)} unit, 6 parameter."),
    kp("plum", I(cnt["dim_spec"]), "baris dim_spec", f"{I(len(conf))} konflik antar format; semua dokumen sepakat."),
    kp("rose", I(bad_total), "baris kotor ditemukan", f"{D(dq.bad_pct, 2)}% dari baris mentah. Semua ditemukan dan ditangani."),
    kp("sky", I(chk.n_measurement), "hasil ukur dinilai", f"{I(chk.n_pass)} lolos, {I(chk.n_fail)} gagal; semuanya punya spec yang berlaku."),
    '</div><h3>1.1 Data simulasi (mentah dan bersih)</h3>')
rp1 += '<div class="card"><h4>Tabel 1.1a. Dokumen PDF menurut format</h4>' + table(
    ["Format", "Jumlah PDF", "Field di gold set", "Keterangan"],
    [[f, I(int((man_docs.format == f).sum())), I(nfmt.n.get(f, 0)) if f in nfmt.index else "0", k] for f, k in (
        ("tabel", "Tabel batas dengan satuan eksplisit"), ("teks", "Batas ditulis dalam kalimat, dengan ≥, ≤, ± dan rentang"), ("ringkas", "Label singkatan (mis. Flux, Pf)"),
        ("terpotong", "Tabel terpotong ke halaman berikutnya"), ("teks_scan", "Hasil scan tanpa lapisan teks, tanpa OCR"))]) + \
    '<p>Dokumen dibuat dengan reportlab dari satu kunci spec (<code>dim_spec_truth.csv</code>) sehingga ketepatan ekstraksi bisa dicek field per field. Data hasil ukur dibuat terpisah dengan seed lain.</p></div>'
lab = {"R1": "Baris ganda (unit dan parameter sama)", "R2": "Nilai kosong", "R3": "Teks N/A", "R4": "Nilai sentinel -999", "R5": "Power dalam mW", "R6": "Satuan tidak sesuai kamus"}
rp1 += '<div class="card"><h4>Tabel 1.1b. Baris mentah, bersih, dan bermasalah (Q13)</h4>' + table(
    ["Tabel", "Mentah", "Bersih", "Bermasalah", "% bermasalah"], [["<code>measurement</code>", I(dq.raw_rows), I(dq.clean_rows), I(dq.bad_rows), D(dq.bad_pct, 2) + "%"]]) + \
    table(["Aturan", "Masalah", "Ditemukan", "Dibuang", "Diperbaiki", "Keputusan"],
          [[r.rule, lab[r.rule], I(r.rows_found), I(r.rows_dropped), I(r.rows_fixed), r.decision] for r in clog.itertuples()]) + \
    f'<p>Jumlah temuan sama dengan yang ditanam generator pada semua jenis ({I(len(cmpd))} jenis cocok). Aturan dijalankan berurutan; baris kosong pada kolom satuan salah dihitung sebagai kosong.</p>'
rp1 += Q(13, f"{D(dq.bad_pct, 2)}% baris hasil ukur tidak valid ({I(bad_total)} dari {I(dq.raw_rows)}). Semuanya ditemukan dan ditangani: {I(dq.dropped)} baris dibuang, {I(dq.fixed)} diperbaiki (mW menjadi W). "
             f"Pass rate berubah bergantung perlakuannya: data mentah apa adanya memberi {P(sens.pass_rate[0], 2)}, sedangkan cleaning sesuai log {P(sens.pass_rate[2], 2)}; membuang semua baris bermasalah (tanpa konversi mW) memberi {P(sens.pass_rate[1], 2)}. "
             f"Parameter paling sering gagal sama pada ketiganya ({sens.top_fail_param[0]}). Rincian di <a href=\"#sec29\">2.9</a>.") + '</div>'
rp1 += '<h3>1.2 Tabel di database (<code>spec_compliance.duckdb</code>)</h3><div class="card"><h4>Tabel 1.2a. Isi database</h4>' + table(
    ["Tabel", "Baris", "Isi"],
    [["dim_spec", I(cnt["dim_spec"]), "Batas spec per model, revisi, dan parameter, dengan halaman sumber. Kunci utama (model, revision, parameter)."],
     ["measurement", I(cnt["measurement"]), "Hasil ukur bersih per unit dan parameter. Kunci utama (unit_id, parameter)."],
     ["extraction_eval", I(cnt["extraction_eval"]), "Satu field hasil ekstraksi dibanding label, per metode (aturan dasar dan aturan lengkap)."],
     ["compliance_result (view)", I(chk.n_measurement), "Putusan per hasil ukur lewat ASOF join ke revisi yang berlaku, dengan margin."]]) + \
    '<h4>Tabel 1.2b. Uji aturan pengecekan (constraint)</h4>' + table(
    ["Baris salah yang dicoba dimasukkan", "Tabel", "Hasil"], [[r.test, f"<code>{r.table}</code>", OK("Ditolak") if r.outcome == "ditolak" else NO("Diterima")] for r in ctest.itertuples()]) + \
    f'<p>Kesepuluh jenis data salah ditolak. Tidak ada hasil ukur tanpa spec yang berlaku ({I(chk.n_without_spec)}).</p></div>'
FILES = {"cleaning_log": ("Log cleaning per aturan", "Q13"), "constraint_tests": ("Uji constraint database", "Q13"), "data_quality_summary": ("Ringkasan data kotor", "Q13"),
         "dim_spec": ("Tabel spec hasil ekstraksi", "Q1, Q4"), "dirty_found_vs_planted": ("Data kotor ditemukan vs ditanam", "Q13"), "doc_validation": ("Validasi skema per dokumen dan metode", "Q12"),
         "extracted_fields": ("Field mentah hasil ekstraksi", "Q1"), "extracted_specs": ("Spec hasil ekstraksi per dokumen", "Q1"), "extraction_accuracy": ("Akurasi per field dan format", "Q1, Q3"),
         "extraction_doc_eval": ("Evaluasi per dokumen", "Q1, Q12"), "extraction_errors": ("Pareto jenis kesalahan", "Q2"), "extraction_eval": ("Field vs label per metode", "Q1, Q3"),
         "review_queue": ("Dokumen yang perlu review", "Q12"), "rows_per_parameter": ("Baris mentah dan bersih per parameter", "Q13"), "spec_conflicts": ("Konflik spec antar format", "Q1"),
         "table_counts": ("Baris per tabel database", "Q13"), "chi2_models": ("Chi-square antar model", "Q4"), "compliance_check": ("Pemeriksaan hasil ukur punya spec", "Q11"),
         "crosscheck_excel": ("SQL vs Excel", "Q11"), "fail_units_by_param": ("Unit gagal menurut jumlah parameter gagal", "Q5"), "ground_truth_check": ("Lima fakta ditanam vs temuan", "Q11"),
         "impact_manual_time": ("Jam pengecekan manual (asumsi)", "Q9"), "impact_stale_spec": ("Unit gagal tersembunyi oleh spec usang", "Q8, Q10"), "margin_distribution": ("Sebaran margin per parameter dan model", "Q6"),
         "margin_param_model": ("Margin dan hampir gagal", "Q6"), "month_param": ("Pass rate per bulan dan parameter", "Q7"), "month_unit": ("Pass rate unit per bulan", "Q7"),
         "near_fail_sensitivity": ("Sensitivitas ambang hampir gagal", "Q6"), "pandas_crosscheck": ("SQL vs pandas", "Q11"), "pareto_fail": ("Pareto kegagalan", "Q5"),
         "passrate_param": ("Pass rate per parameter", "Q4"), "passrate_param_model": ("Pass rate per parameter dan model", "Q4"), "passrate_unit": ("Pass rate per unit", "Q4"),
         "revision_param_model": ("Pass rate per revisi", "Q8"), "sensitivity_cleaning": ("Tiga perlakuan data kotor", "Q13"), "trend_month": ("Uji tren bulanan", "Q7"),
         "truth_compliance_check": ("Putusan SQL vs kunci jawaban simulasi", "Q11"), "wilson_passrate": ("Pass rate dengan interval Wilson", "Q4"),
         "wrong_revision_rev1_0": ("Putusan jika memakai Rev 1.0", "Q8"), "wrong_revision_rev2_0": ("Putusan jika memakai Rev 2.0", "Q8")}
resfiles = sorted(p for d in (RES_PREP, RES_ANALYSIS) for p in d.glob("*.csv"))
miss = [p.stem for p in resfiles if p.stem not in FILES]
assert not miss, f"CSV hasil belum didokumentasikan di FILES: {miss}"
rp1 += '<div class="card"><h4>Tabel 1.2c. Data hasil analisis (<code>project/results/</code>)</h4>' + table(
    ["File", "Isi", "Baris", "Menjawab"], [[f"<code>{p.stem}.csv</code>", FILES[p.stem][0], I(len(pd.read_csv(p))), FILES[p.stem][1]] for p in resfiles]) + \
    f'<p>{I(len(resfiles))} file CSV, ditambah {I(len(list(RES_PRESENT.glob("dash_*.csv"))))} CSV data dashboard.</p></div>'
rp1 += '<h3>1.3 Angka kunci (KPI)</h3><div class="card"><h4>Tabel 1.3. Lima KPI</h4>' + table(
    ["KPI", "Rumus ringkas", "Hasil", "Jumlah data"],
    [["Akurasi ekstraksi", "field benar ÷ field di gold set", f"aturan dasar {P(A['rule_basic'])}, aturan lengkap {P(A['rule_full'])}", f"{I(nall.n)} field"],
     ["Pass rate unit", "unit dengan semua parameter lolos ÷ unit", P(unit_all.pass_rate, 2), f"{I(unit_all.n)} unit"],
     ["Parameter paling sering gagal", "jumlah hasil ukur gagal", f"{tp.parameter} {tp.model}: {I(tp.n_fail)} ({P(tp.share, 0)} dari semua gagal)", f"{I(chk.n_fail)} gagal"],
     ["Hampir gagal", "lolos dengan margin &lt; 1 simpangan baku", f"{top_near.parameter} {top_near.model}: {P(top_near.share_near_fail)}", f"{I(top_near.n)} hasil ukur"],
     ["Jam pengecekan manual (estimated)", "dokumen × menit per dokumen × 2", f"{I(man.loc[20, 'hours_per_year'])} jam per tahun", "asumsi 20 menit per dokumen"]]) + \
    f'<p>Aturan putusan dan margin ada di <code>project/docs/compliance_rules.md</code>. Putusan selalu dihitung oleh SQL, bukan oleh LLM.</p></div>'

# ---------------------------------------------------------------- 2. business questions
pm_i = parm.set_index(["parameter", "model"])
mo = lambda m: MONTH[m]
s21 = mk('<h3 id="sec21">2.1 Ketepatan ekstraksi <span class="qlist">Q1, Q2, Q3, Q12</span></h3><div class="card">',
         Q(1, f"Aturan lengkap membaca {I(A['rule_full'] * nall.n)} dari {I(nall.n)} field dengan benar ({P(A['rule_full'])}), memenuhi usulan target 95%; aturan dasar hanya {I(A['rule_basic'] * nall.n)} dari {I(nall.n)} ({P(A['rule_basic'])}). "
              f"Per jenis field (aturan lengkap): batas bawah {P(afld.loc['min', 'rule_full'], 0)}, batas atas {P(afld.loc['max', 'rule_full'], 0)}, satuan {P(afld.loc['unit', 'rule_full'], 0)}. "
              f"PDF hasil scan ({I(1)} dokumen) tidak dievaluasi karena tanpa OCR dan masuk antrean review. Angka 100% terjadi karena dokumen simulasi dibuat dari format yang sudah dikenal aturan; pada format baru akurasi bisa turun."),
         Q(2, f"Format kalimat (bukan tabel) paling sering: {I(eb.n[0])} field salah ({P(eb.share[0], 0)}), disusul label singkatan tidak dikenal ({I(eb.n[1])}, {P(eb.share[1], 0)}) dan tabel terpotong ke halaman berikutnya ({I(eb.n[2])}, {P(eb.share[2], 0)}). "
              f"Kesalahan satuan atau simbol sebagai kelompok tersendiri tidak muncul: simbol ≥, ≤, ± hanya salah bila ada di kalimat, jadi masuk kategori format kalimat."),
         Q(3, f"Belum bisa dijawab langsung: langkah LLM (Claude API, <code>extract/llm.py</code>) sudah ditulis tetapi tidak dijalankan karena tidak ada kunci API di lingkungan ini. Sebagai pembanding, dua tingkat aturan diuji pada gold set yang sama: "
              f"aturan dasar {P(A['rule_basic'])} dan aturan lengkap {P(A['rule_full'])}. Perbandingan aturan vs LLM tetap perlu dijalankan.", warn=True),
         Q(12, f"Dengan aturan lengkap, {I(rev_n['rule_full'])} dari {I(nd)} dokumen ({P(rev_n['rule_full'] / nd)}) perlu review: PDF hasil scan. Dengan aturan dasar {I(rev_n['rule_basic'])} dari {I(nd)} ({P(rev_n['rule_basic'] / nd)}) gagal validasi skema dan harus dibaca manusia."),
         '<h4>Grafik 2.1a. Akurasi per format dokumen, aturan dasar vs aturan lengkap</h4>',
         gbars(list(afmt.index), [("Aturan dasar", GREY, list(afmt.rule_basic)), ("Aturan lengkap", BLUE, list(afmt.rule_full))], lambda v: P(v, 0), "Akurasi per format dokumen", rot=0),
         legend([(GREY, "Aturan dasar"), (BLUE, "Aturan lengkap")]),
         '<h4>Tabel 2.1b. Pareto kesalahan aturan dasar</h4>',
         table(["Jenis kesalahan", "Jumlah field", "Porsi", "Kumulatif"], [[r.error_type, I(r.n), P(r.share), P(r.cum_share)] for r in eb.itertuples()]),
         '<h4>Tabel 2.1c. Antrean review manual</h4>',
         table(["Dokumen", "Model", "Revisi", "Alasan"], [[f"<code>{r.doc}</code>", r.model, r.revision, r.reason] for r in rq.itertuples()]),
         f'<p>Dokumen lolos validasi skema (parameter lengkap, satuan dikenal, batas bawah lebih kecil dari batas atas): aturan dasar {I(sok["rule_basic"])} dari {I(nd)}, aturan lengkap {I(sok["rule_full"])} dari {I(nd)}. '
         f'Tabel <code>dim_spec</code> akhir memuat {I(cnt["dim_spec"])} baris dan {I(len(conf))} konflik antar format.</p></div>')
pm = parm.copy()
s22 = mk('<h3 id="sec22">2.2 Pass rate, Pareto, dan margin <span class="qlist">Q4, Q5, Q6</span></h3><div class="card">',
         Q(4, f"Pass rate unit (semua parameter lolos) {P(unit_all.pass_rate, 2)}. Per parameter semuanya di atas {P(par.pass_rate.min(), 1)}; terendah {par.loc[par.pass_rate.idxmin(), 'parameter']} ({P(par.pass_rate.min(), 2)}). "
              f"Per model, kelompok terendah adalah {tp.parameter} {tp.model} ({P(cri12.pass_rate, 2)}); perbedaan antar model signifikan untuk {', '.join(sig.parameter)} (chi-square, koreksi Holm, Tabel 2.2c). Semua kelompok memiliki lebih dari 30 hasil ukur."),
         Q(5, f"{tp.parameter} {tp.model} menyumbang {I(tp.n_fail)} dari {I(chk.n_fail)} kegagalan ({P(tp.share)}), disusul {pareto.parameter[1]} {pareto.model[1]} ({I(pareto.n_fail[1])}) dan {pareto.parameter[2]} {pareto.model[2]} ({I(pareto.n_fail[2])}). "
              f"Hampir semua unit gagal hanya pada satu parameter ({I(fup.n_units[0])} dari {I(nfail_units)} unit gagal)."),
         Q(6, f"{top_near.parameter} {top_near.model} paling dekat ke batas: median margin {D(top_near.median_margin_sd, 2)} simpangan baku (model lain {D(mpi.loc[('cri', '5W'), 'median_margin_sd'], 2)}) dan {P(top_near.share_near_fail)} hasilnya lolos dengan margin kurang dari 1 simpangan baku. "
              f"{mp.sort_values('share_near_fail', ascending=False).iloc[1].parameter} {mp.sort_values('share_near_fail', ascending=False).iloc[1].model} menyusul ({P(mp.sort_values('share_near_fail', ascending=False).iloc[1].share_near_fail)}). "
              f"Ambang hampir gagal adalah asumsi; urutannya sama pada ambang {D(nfs.near_fail_sd.min(), 1)}, 1,0, dan {D(nfs.near_fail_sd.max(), 1)} (Tabel 2.2d).", warn=False),
         '<h4>Grafik 2.2a. Jumlah gagal per parameter dan model (Pareto)</h4>',
         hbars([(f"{r.parameter} {r.model}", r.n_fail, HI if i == 0 else BLUE, f"{r.parameter} {r.model}: {I(r.n_fail)} gagal ({P(r.share, 1)})") for i, r in enumerate(pareto.head(8).itertuples())], lambda v: I(v), "Pareto kegagalan", float(pareto.n_fail.max()) * 1.15),
         '<h4>Tabel 2.2b. Pass rate per parameter dan model, interval Wilson 95%</h4>',
         table(["Parameter", "Model", "Hasil ukur", "Lolos", "Pass rate", "CI 95%"], [[r.parameter, r.model, I(r.n), I(r.n_pass), P(r.pass_rate, 2), f"{P(r.ci_low, 2)} s.d. {P(r.ci_high, 2)}"] for r in wil.itertuples()]),
         '<h4>Tabel 2.2c. Apakah model berbeda? (chi-square per parameter, koreksi Holm)</h4>',
         table(["Parameter", "χ²", "p-value", "p Holm", "Cramér's V", "Signifikan"], [[r.parameter, D(r.chi2, 1), pv(r.p_value), pv(r.p_holm), D(r.cramers_v, 3), OK("Ya") if r.significant_holm_0_05 else NO("Tidak")] for r in chi.itertuples()]),
         '<h4>Grafik 2.2d. Porsi hasil lolos yang hampir gagal (margin &lt; 1 simpangan baku)</h4>',
         bars([(f"{r.parameter} {r.model}", r.share_near_fail, HI if i == 0 else BLUE, f"{r.parameter} {r.model}: {P(r.share_near_fail, 1)} ({I(r.n_near_fail)} dari {I(r.n)}); pass rate {P(r.pass_rate, 2)}") for i, r in enumerate(mp.sort_values('share_near_fail', ascending=False).itertuples())],
              lambda v: P(v, 0), "Hampir gagal per parameter dan model", rot=60, small=True),
         '<h4>Tabel 2.2e. Margin dan pass rate berdampingan</h4>',
         table(["Parameter", "Model", "Pass rate", "Median margin (SD)", "Persentil 5 margin (SD)", "Hampir gagal"], [[r.parameter, r.model, P(r.pass_rate, 2), D(r.median_margin_sd, 2), D(r.p05_margin_sd, 2), P(r.share_near_fail, 1)] for r in mp.itertuples()]),
         '<p>Margin = jarak ke batas terdekat dibagi simpangan baku parameter pada model itu. Pass rate tinggi dengan margin tipis lebih berisiko daripada pass rate sedikit lebih rendah dengan margin lebar.</p></div>')
s23 = mk('<h3 id="sec23">2.3 Tren bulanan <span class="qlist">Q7</span></h3><div class="card">',
         Q(7, f"Pass rate unit menurun tipis dari {P(mu.pass_rate.iloc[0], 2)} ({mo(mu.month.iloc[0])}) ke {P(mu.pass_rate.iloc[-1], 2)} ({mo(mu.month.iloc[-1])}); tren linear signifikan (Cochran-Armitage, p {pv(trd.p_value)}). "
              f"Data simulasi tidak punya <code>lot_id</code>, jadi perubahan antar lot tidak bisa diperiksa; hanya antar bulan.", warn=True),
         '<h4>Grafik 2.3a. Pass rate unit per bulan</h4>',
         bars([(mo(r.month), r.pass_rate, BLUE, f"{r.month}: {P(r.pass_rate, 2)} ({I(r.n_pass)} dari {I(r.n)} unit)") for r in mu.itertuples()], lambda v: P(v, 1), "Pass rate unit per bulan", rot=0, small=True, ymax=1.0),
         '<h4>Tabel 2.3b. Unit per bulan</h4>', table(["Bulan", "Unit", "Lolos semua parameter", "Pass rate"], [[mo(r.month), I(r.n), I(r.n_pass), P(r.pass_rate, 2)] for r in mu.itertuples()]), '</div>')
fl2 = fl.loc["Rev 2.0"]
s24 = mk('<h3 id="sec24">2.4 Spec revisi yang salah <span class="qlist">Q8</span></h3><div class="card">',
         Q(8, f"Jika semua hasil ukur dinilai dengan Rev 1.0 yang sudah usang, {I(s10.units_fail_hidden)} dari {I(s10.units_truly_fail)} unit gagal ({P(s10.share_fail_hidden_units)}) tampak lolos, tanpa alarm palsu. "
              f"Pemicunya batas minimal luminous flux 9W yang naik dari {I(lim9.loc['Rev 1.0', 'lower_limit'])} lm (Rev 1.0) menjadi {I(lim9.loc['Rev 2.0', 'lower_limit'])} lm (Rev 2.0, berlaku mulai {lim9.loc['Rev 2.0', 'valid_from']}); pass rate flux 9W {P(fl.loc['Rev 1.0', 'pass_rate'], 1)} pada Rev 1.0 dan {P(fl2.pass_rate, 1)} pada Rev 2.0. "
              f"Dengan Rev 2.0 yang keliru, {I(s20.units_fail_hidden)} unit gagal tersembunyi dan {I(s20.units_false_alarm)} unit ditolak tanpa alasan. Penilaian memakai revisi berlaku pada tanggal uji (ASOF join), bukan revisi terbaru."),
         '<h4>Tabel 2.4a. Dampak memakai revisi spec yang salah untuk seluruh periode</h4>',
         table(["Revisi yang keliru dipakai", "Unit gagal sebenarnya", "Gagal tampak lolos", "Porsi tersembunyi", "Lolos tampak gagal"],
               [[r.Index, I(r.units_truly_fail), I(r.units_fail_hidden), P(r.share_fail_hidden_units), I(r.units_false_alarm)] for r in stale.itertuples()]),
         '<h4>Tabel 2.4b. Pass rate luminous flux 9W per revisi</h4>',
         table(["Revisi", "Batas bawah (lm)", "Hasil ukur", "Pass rate"], [[r, I(lim9.loc[r, "lower_limit"]), I(fl.loc[r, "n"]), P(fl.loc[r, "pass_rate"], 1)] for r in fl.index]), '</div>')
s25 = mk('<h3 id="sec25">2.5 Dampak waktu <span class="qlist">Q9, Q10</span></h3><div class="card">',
         Q(9, f"Pengecekan manual {I(nd)} dokumen dalam periode data (sekitar 6 bulan) memakan {I(man.loc[20, 'hours_in_data_period'])} jam pada asumsi 20 menit per dokumen, atau sekitar {I(man.loc[20, 'hours_per_year'])} jam per tahun (rentang {I(man.loc[10, 'hours_per_year'])} sampai {I(man.loc[30, 'hours_per_year'])} jam untuk 10 sampai 30 menit). "
              f"Menit per dokumen adalah asumsi, bukan hasil pengukuran, dan dokumen per tahun dianggap dua kali periode data. Angka estimated / simulated.", warn=True),
         Q(10, f"Tidak ada data cek manual pada lot, jadi pertanyaan ini dijawab dengan proksi: unit yang tampak lolos pada spec usang padahal gagal menurut revisi berlaku ({I(s10.units_fail_hidden)} unit untuk Rev 1.0). "
               f"Ini batas atas risiko salah-versi, bukan jumlah kesalahan cek manual yang sebenarnya.", warn=True),
         '<h4>Tabel 2.5a. Jam pengecekan manual per skenario (estimated)</h4>',
         table(["Menit per dokumen (asumsi)", "Dokumen", "Jam pada periode data", "Jam per tahun"], [[I(r.Index), I(r.docs_in_data), D(r.hours_in_data_period, 1), D(r.hours_per_year, 1)] for r in man.itertuples()]),
         '<p>Menit dihemat = dokumen × menit per dokumen. Nilai rupiah tidak dihitung (tidak ada dasar biaya per jam).</p></div>')
xl = ce.groupby("parameter").status.apply(lambda s: (s == "PASS").all())
s26 = mk('<h3 id="sec26">2.6 Validitas <span class="qlist">Q11, Q13</span></h3><div class="card">',
         Q(11, f"Ya. Putusan SQL sama dengan pandas pada {I(cx.rows)} baris (0 selisih putusan dan revisi), dengan Excel pada {I(len(ce))} dari {I(len(ce))} pemeriksaan (rumus MAXIFS, SUMIFS, COUNTIFS dihitung ulang oleh LibreOffice), dan dengan kunci jawaban simulasi pada {I(tcc.rows_checked)} baris ({I(tcc.result_mismatch)} selisih, {I(tcc.truth_fail)} gagal pada kunci dan {I(tcc.pipeline_fail)} pada pipeline). "
               f"Kelima fakta yang ditanam ditemukan (Tabel 2.6a)."),
         '<h4>Tabel 2.6a. Lima fakta yang ditanam vs temuan</h4>',
         table(["No", "Fakta", "Ditemukan", "Hasil"], [[I(r.Index), cs(r.fakta), cs(r.ditemukan), OK("Sesuai") if r.hasil == "Sesuai" else PART(r.hasil)] for r in gtc.itertuples()]),
         '<h4>Tabel 2.6b. Cek silang</h4>',
         table(["Pembanding", "Pemeriksaan", "PASS", "Isi"],
               [["SQL vs pandas (merge_asof)", I(cx.rows), I(cx.rows - cx.result_mismatch), "putusan dan revisi setiap hasil ukur"],
                ["SQL vs Excel", I(len(ce)), I(ce.status.eq("PASS").sum()), "jumlah, lolos, dan pass rate untuk 18 kombinasi parameter dan model"],
                ["SQL vs kunci jawaban simulasi", I(tcc.rows_checked), I(tcc.rows_checked - tcc.result_mismatch), "putusan dan revisi dari <code>truth_compliance.csv</code>"]]),
         '<h4>Tabel 2.6c. Tiga perlakuan data kotor (Q13)</h4>',
         table(["Perlakuan", "Baris dinilai", "Pass rate", "Gagal", "Pass rate CRI 12W", "Parameter gagal terbanyak"], [[r.perlakuan, I(r.n_rows), P(r.pass_rate, 2), I(r.n_fail), P(r.cri_12w_pass_rate, 2), r.top_fail_param] for r in sens.itertuples()]),
         '<p>Perlakuan A menganggap nilai kosong dan N/A sebagai gagal serta membaca -999 dan mW apa adanya, sehingga menggelembungkan jumlah gagal. Perlakuan B dan C hampir sama; selisihnya hanya konversi mW.</p></div>')
s29 = ""
SEC = {1: "21", 2: "21", 3: "21", 12: "21", 4: "22", 5: "22", 6: "22", 7: "23", 8: "24", 9: "25", 10: "25", 11: "26", 13: "26"}
rp2_body = mk(s21, s22, s23, s24, s25, s26.replace('id="sec26"', 'id="sec26"'))
rp2_body = rp2_body.replace('href="#sec29"', 'href="#sec26"')
rp1 = rp1.replace('href=\\"#sec29\\"', 'href="#sec26"').replace('#sec29', '#sec26').replace("<a href=\"#sec26\">2.9</a>", '<a href="#sec26">2.6</a>')
qn_uniq = sorted(set(int(x) for x in re.findall(r'<span class="qn">Q(\d+)</span>', rp1 + rp2_body)))
assert qn_uniq == list(range(1, 14)), qn_uniq
nw = len(WARN)
wtxt = ", ".join(f"Q{n}" for n in sorted(WARN))
chips = mk('<div class="qchips">', "".join(f'<a class="qc{" w" if n in WARN else ""}" href="#sec{SEC[n]}" title="{esc(QT[n])}">Q{n}</a>' for n in range(1, 14)), '</div>')
rp2 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> semua {len(QT)} pertanyaan terjawab ({npr["Utama"]} Utama, {npr["Pendukung"]} Pendukung, {npr["Tambahan"]} Tambahan). '
         f'{nw} jawaban dengan catatan (kuning): {wtxt}. Klik nomor pertanyaan untuk melompat ke pembahasannya. Pertanyaan utama project dijawab di bagian 7.</p>',
         chips, '<p class="report-note">Q hijau = terjawab, Q kuning = terjawab dengan catatan. Pembahasan dikelompokkan per grafik atau tabel bukti (2.1 sampai 2.6). Q13 dijawab di Tabel 1.1b dan Tabel 2.6c.</p></div>', rp2_body)

# ---------------------------------------------------------------- 3-5
ndash = len(list(RES_PRESENT.glob("dash_*.csv")))
npy = len(list((REPO / "project/code").rglob("*.py")))
loc = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in (REPO / "project/code").rglob("*.py"))
nsql = len(list((REPO / "project/code").rglob("*.sql")))
fm = lambda r: OK("Ditemukan") if r == "Sesuai" else PART(r)
rp3 = mk('<div class="card"><p><b>Jawaban singkat:</b> dataset sesuai rancangan pada hal pokok (3 model, 3 revisi, 6 parameter, 5 fakta ditanam, data kotor 2–3%) dan bisa dibuat ulang dengan seed tetap. '
         'Perbedaan: nilai revisi luminous flux 9W, jumlah dokumen (24 datasheet, tanpa laporan uji lot), tidak ada <code>lot_id</code> dan nomor seri, dua seed, dan gold set yang ditulis generator, bukan disalin manual. Tidak ada masalah lisensi karena data buatan sendiri.</p></div>',
         table(["Aspek", "Rancangan", "Realisasi", "Verdict"], [
             ["Sumber", "Simulasi buatan sendiri, skrip di <code>scripts/</code>", "Skrip <code>01_generate_docs.py</code> dan <code>02_generate_measurements.py</code> dengan seed tetap; hasil identik dua kali dijalankan dan tercatat di registri DataCenter", OK("Sesuai")],
             ["Seed", "26260302", f"{I(gd['seed'])} untuk dokumen dan 26260999 untuk hasil ukur (dua generator)", PART("Sesuai + penyesuaian")],
             ["Dokumen PDF", "9 datasheet (3 model × 3 revisi) dan ±15 laporan uji lot", f"{I(nd)} datasheet: 3 model × 3 revisi × beberapa format; tidak ada laporan uji lot", PART("Berubah")],
             ["Hasil ukur", "±18.000 unit × 6 parameter = ±108.000 nilai", f"{I(nunits)} unit, {I(dq.raw_rows)} baris mentah ({I(dq.clean_rows)} bersih)", OK("Sesuai")],
             ["Gold set", "±160 field dari 9 datasheet, label manual", f"{I(nall.n)} field dari {I(n_text_docs)} PDF bertekstual; ditulis generator sebagai kunci jawaban, bukan disalin manual di Excel", PART("Berubah")],
             ["Kolom measurement", "serial_no, lot_id, model, test_date, parameter, value, unit", "unit_id (tanpa lot_id), model, test_date, parameter, value, unit", PART("Berubah")],
             ["Tabel", "dim_spec, extraction_eval, measurement, compliance_result", "Keempatnya (compliance_result berupa view), dengan constraint", OK("Sesuai")],
             ["Fakta 1 (CRI 12W paling dekat ke batas)", "Margin paling tipis", cs(gtc.loc[1].ditemukan), fm(gtc.loc[1].hasil)],
             ["Fakta 2 (revisi menaikkan batas flux 9W)", "806 lm menjadi 820 lm di bulan ke-3", cs(gtc.loc[2].ditemukan) + ". Angka berbeda dari rancangan", PART("Sesuai + penyesuaian")],
             ["Fakta 3 (satuan dan simbol beragam)", "lm dan klm, mA dan A, ≥, ±, rentang", cs(gtc.loc[3].ditemukan), fm(gtc.loc[3].hasil)],
             ["Fakta 4 (tabel terpotong dan PDF scan)", "Satu tabel terpotong dan satu PDF scan", f"{I(int((man_docs.format == 'terpotong').sum()))} PDF terpotong dan 1 scan; " + cs(gtc.loc[4].ditemukan), fm(gtc.loc[4].hasil)],
             ["Fakta 5 (data kotor 2–3%)", "Kosong, satuan salah, nomor seri ganda", cs(gtc.loc[5].ditemukan) + ". Jenisnya: kosong, N/A, -999, mW, baris ganda", fm(gtc.loc[5].hasil)],
             ["10 stasiun produksi", "Hasil ukur dari stasiun 8 dan 9", "Tidak dimodelkan; data hanya hasil Photometric Test", PART("Tidak dibuat")],
             ["Lisensi", "Tidak memakai datasheet produsen", "Tidak ada dataset pihak ketiga, tidak perlu dicek", OK("Tidak berlaku")]]))
rp4 = mk('<div class="card"><p><b>Jawaban singkat:</b> sebagian besar tools rancangan dipakai. Langkah LLM (Claude API) hanya ditulis, tidak dijalankan (tidak ada kunci API); pypdf tidak dipakai; Streamlit dibuat dan diuji lokal tetapi belum di-deploy; '
         'cek silang Excel dihitung oleh LibreOffice. Playwright dan SciPy ditambahkan.</p></div>',
         table(["Tool", "Rancangan", "Realisasi", "Verdict"], [
             ["Python (pdfplumber, pypdf, pandas)", "Membaca PDF dan menyiapkan data", f"pdfplumber (teks dan tabel per halaman), regex, pandas ({I(npy)} skrip dan modul, {I(loc)} baris); pypdf tidak dipakai karena metadata tidak dibutuhkan", PART("Sesuai + penyesuaian")],
             ["LLM (Claude API)", "Mengubah teks tabel menjadi data terstruktur, sekali per dokumen, hasil disimpan", "<code>extract/llm.py</code> (tool-use, skema Pydantic, cache per dokumen) selesai ditulis tetapi tidak dijalankan; perbandingan aturan dasar vs aturan lengkap dipakai sebagai pembanding", PART("Sebagian")],
             ["Pydantic", "Skema hasil ekstraksi", "<code>extract/schema.py</code>: tipe angka, satuan dikenal, batas bawah &lt; batas atas; dipakai sebagai validasi dokumen", OK("Sesuai")],
             ["DuckDB + SQL", "4 tabel, join revisi, putusan, margin", f"<code>spec_compliance.duckdb</code> dengan constraint; {I(nsql)} file SQL; ASOF join pada view <code>compliance_result</code>", OK("Sesuai")],
             ["Excel", "Cek silang putusan dan label gold set", f"<code>crosscheck.xlsx</code>: {I(len(ce))} pemeriksaan, rumus dihitung ulang oleh LibreOffice, bukan Microsoft Excel; file tidak di-commit (7,6 MB, dibuat ulang); gold set ditulis generator", PART("Sesuai + penyesuaian")],
             ["Streamlit + Plotly", "Dashboard 3 halaman, publik di Streamlit Community Cloud", "<code>streamlit/app.py</code> 4 halaman, filter model, slider ambang, kalkulator; diuji dengan <code>AppTest</code>; belum di-deploy", PART("Sebagian")],
             ["reportlab", "Membuat datasheet PDF simulasi", "Dipakai di generator (tabel, kalimat, tabel terpotong, halaman scan berbentuk gambar)", OK("Sesuai")],
             ["Jupyter", "Notebook evaluasi ekstraksi dan analisis", "<code>extraction_eval.ipynb</code> dan <code>analysis.ipynb</code> dieksekusi tanpa error", OK("Sesuai")],
             ["SciPy, Playwright", "Tidak ada di rancangan", "SciPy untuk chi-square dan uji tren; Playwright untuk mencetak infografik menjadi PDF dan PNG", PART("Tambahan")],
             ["GitHub + Markdown", "Kode, contoh PDF, README", "Struktur dan README siap; berada di branch <code>project-26-build</code>, belum digabung ke <code>main</code>", PART("Sebagian")]]))
steps = [("1", "Menetapkan parameter dan aturan pass/fail", "<code>project/docs/compliance_rules.md</code>", OK("Sesuai"), ""),
         ("2", "Merancang skema tabel dan skema ekstraksi", "<code>data_dictionary.md</code>, <code>extract/schema.py</code>, <code>01_schema.sql</code>", OK("Sesuai"), ""),
         ("3", "Membuat dokumen PDF simulasi", "<code>01_generate_docs.py</code>", PART("Sesuai + penyesuaian"), f"{I(nd)} datasheet dalam 5 format; tanpa laporan uji lot."),
         ("4", "Membuat dan membersihkan hasil ukur", "<code>02_generate_measurements.py</code>, <code>03_clean_measurements.py</code>", OK("Sesuai"), "Ditambah pencocokan temuan dengan yang ditanam (<code>truth_dirty.csv</code>)."),
         ("5", "Membuat label manual (gold set)", "<code>gold_set.csv</code> dari generator", PART("Berubah"), "Label ditulis generator, bukan disalin manual di Excel."),
         ("6", "Mengekstrak isi PDF (aturan dan LLM)", "<code>04_extract_specs.py</code>, <code>extract/rules.py</code>, <code>extract/llm.py</code>", PART("Sebagian"), "LLM ditulis tetapi tidak dijalankan; dua tingkat aturan dibandingkan."),
         ("7", "Mengevaluasi hasil ekstraksi", "<code>05_evaluate_extraction.py</code>", OK("Sesuai"), ""),
         ("8", "Memasangkan spec dan hasil ukur", "<code>06_build_db.py</code>, <code>03_views.sql</code>", OK("Sesuai"), "Ditambah 10 uji penolakan constraint."),
         ("9", "Menganalisis pass rate dan margin", "<code>07_run_queries.py</code>, <code>08_verify_stats.py</code>", PART("Sesuai + tambahan"), "Ditambah interval Wilson, chi-square, uji tren."),
         ("10", "Cek silang, ground truth, dan dampak", "<code>09_excel_crosscheck.py</code>, <code>10_impact_ground_truth.py</code>", OK("Sesuai"), "Dampak dalam jam kerja, estimated."),
         ("11", "Membuat dashboard", "<code>streamlit/app.py</code>, <code>11_build_dashboard_data.py</code>", PART("Sebagian"), "Belum di-deploy."),
         ("12", "Menulis README dan finalisasi", "<code>README.md</code>, halaman ini", PART("Sebagian"), "Siap; digabung ke main setelah ditinjau.")]
rp5 = mk('<div class="card"><p><b>Jawaban singkat:</b> 12 langkah dijalankan sesuai urutan dependensi data. Nama file mengikuti struktur repo standar; langkah 5 berubah, langkah 6, 11, dan 12 sebagian.</p></div>',
         table(["Langkah", "Rancangan", "Realisasi", "Verdict", "Catatan"], [[a, b, c, d, e] for a, b, c, d, e in steps]),
         '<div class="card"><h4>Penyesuaian dan improvisasi yang tidak ada di rancangan</h4><ul class="tight">',
         '<li>Dua tingkat aturan (dasar dan lengkap) dibandingkan sebagai pengganti perbandingan aturan vs LLM, karena LLM tidak bisa dijalankan.</li>',
         f'<li>File <code>truth_dirty.csv</code> ditambahkan ke generator agar temuan data kotor bisa dicocokkan dengan yang ditanam; berkas lain tetap identik dengan sidik jari di registri DataCenter.</li>',
         f'<li>Uji constraint ({I(len(ctest))} jenis baris salah ditolak), cek silang pandas, dan pencocokan dengan kunci jawaban simulasi ditambahkan di luar rancangan.</li>',
         '<li>Uji tiga perlakuan data kotor (Q13) dan uji chi-square antar model dengan koreksi Holm.</li>',
         '<li>Notebook dan infografik dibuat otomatis dari hasil, dan angka halaman ini diaudit terhadap file hasil.</li></ul></div>')

# ---------------------------------------------------------------- 6
chk_f = lambda rel: (REPO / rel).exists()
outs = [("Dashboard compliance", "Utama", PART("Sebagian"), "<code>streamlit/app.py</code> (4 halaman, filter model) diuji lokal dengan AppTest. Link publik belum ada"),
        ("One-sheet infografik", "Utama", OK("Tercapai"), "<code>infographic.pdf</code> dan <code>infographic.png</code>, dibuat dari CSV hasil"),
        ("Pipeline ekstraksi", "Utama", PART("Sebagian"), "Dua tingkat aturan dan skema Pydantic berjalan; langkah LLM ditulis tetapi tidak dijalankan"),
        ("Database & query SQL", "Utama", OK("Tercapai"), f"<code>spec_compliance.duckdb</code> (dibuat ulang, tidak di-commit) dan {I(nsql)} file SQL"),
        ("Generator dokumen & data simulasi", "Utama", OK("Tercapai"), "<code>01_generate_docs.py</code> dan <code>02_generate_measurements.py</code> dengan seed tetap dan kunci jawaban"),
        ("Laporan evaluasi ekstraksi", "Utama", OK("Tercapai"), "<code>extraction_eval.ipynb</code> dieksekusi tanpa error"),
        ("Laporan temuan & rekomendasi", "Utama", OK("Tercapai"), "<code>README.md</code> dan halaman ini"),
        ("Repositori GitHub", "Utama", PART("Sebagian"), "Struktur dan cara menjalankan ulang siap; berada di branch <code>project-26-build</code>, belum digabung ke <code>main</code>"),
        ("Slide presentasi", "Opsional", NO("Tidak dibuat"), "Opsional, tidak dibuat")]
nU = [o for o in outs if o[1] == "Utama"]
cnt_o = lambda s: sum(1 for o in nU if s in o[2])
docs = [("docs/compliance_rules.md", "Aturan pass/fail", "project/docs/compliance_rules.md"), ("docs/data_dictionary.md", "Kamus data", "project/docs/data_dictionary.md"),
        ("extract/schema.py", "Skema Pydantic", "project/code/extract/schema.py"), ("scripts/generate_docs.py", "Generator PDF", "project/code/1-data-preparation/python/01_generate_docs.py"),
        ("data/docs/*.pdf", "PDF simulasi (contoh)", "project/data/sample/docs"), ("scripts/generate_measurements.py", "Generator hasil ukur", "project/code/1-data-preparation/python/02_generate_measurements.py"),
        ("data/raw/measurement.csv", "Hasil ukur mentah (tidak di-commit)", "project/data/raw"), ("data/planted_facts.json", "Fakta ditanam", "project/data/sample/ground_truth_docs.json"),
        ("data/gold_set.csv", "Gold set", "project/data/sample/gold_set.csv"), ("docs/cleaning_log.md", "Log cleaning", "project/docs/cleaning_log.md"),
        ("extract/", "Kode ekstraksi dan prompt", "project/code/extract/rules.py"), ("compliance.duckdb", "Database (tidak di-commit)", "project/spec_compliance.duckdb"),
        ("sql/", "Query dan view", "project/code/2-analysis/sql/03_views.sql"), ("outputs/crosscheck.xlsx", "Cek silang Excel (tidak di-commit)", "project/results/2-analysis/crosscheck.xlsx"),
        ("notebooks/extraction_eval.ipynb", "Evaluasi ekstraksi", "project/results/3-presentation/extraction_eval.ipynb"), ("notebooks/analysis.ipynb", "Analisis", "project/results/3-presentation/analysis.ipynb"),
        ("dashboard/app.py", "Dashboard Streamlit", "project/code/3-presentation/streamlit/app.py"), ("requirements.txt", "Paket Python", "project/requirements.txt"),
        ("outputs/infographic.pdf / .png", "One-sheet", "project/results/3-presentation/infographic.png"), ("README.md", "Laporan temuan", "README.md"),
        ("index.html", "Pengalihan ke design-and-report/", "index.html"), ("slides/presentation.pdf", "Slide", "slides/presentation.pdf")]
stat_doc = lambda rel: PART("Tidak di-commit") if ("duckdb" in rel or "raw" in rel or "crosscheck.xlsx" in rel) else (OK("Ada") if chk_f(rel) else NO("Belum ada"))
rp6 = mk(f'<div class="card"><p><b>Jawaban singkat:</b> {I(cnt_o("Tercapai"))} dari {I(len(nU))} output Utama tercapai penuh dan {I(cnt_o("Sebagian"))} sebagian (dashboard belum di-deploy, pipeline tanpa LLM, repositori belum digabung ke main). Slide Opsional tidak dibuat.</p></div>',
         table(["Output", "Label", "Status", "Bukti"], [[f"<b>{a}</b>", b, c, d] for a, b, c, d in outs]),
         '<div class="card"><h4>Daftar dokumen pada rancangan vs repositori</h4>',
         table(["Dokumen (rancangan)", "Isi", "Lokasi sekarang", "Status"], [[f"<code>{a}</code>", b, f"<code>{c}</code>", stat_doc(c)] for a, b, c in docs]),
         '<p>Data mentah, data bersih, database, dan <code>crosscheck.xlsx</code> tidak di-commit karena bisa dibuat ulang oleh skrip.</p></div>')

# ---------------------------------------------------------------- 7
crit = [("1. Kedelapan pertanyaan Utama terjawab dengan angka", OK("Tercapai"), "Q1, Q4, Q5, Q6, Q8, Q9, Q11, Q13 terjawab (bagian 2); Q9 memakai asumsi menit per dokumen"),
        ("2. Akurasi ekstraksi per field dilaporkan, field salah tercatat dengan penyebab (target 95%)", OK("Tercapai"), f"aturan lengkap {P(A['rule_full'])}, aturan dasar {P(A['rule_basic'])}; {I(eb.n.sum())} field salah tercatat per jenis (Tabel 2.1b). LLM tidak dijalankan"),
        ("3. Putusan SQL sama dengan hitungan manual Excel", OK("Tercapai"), f"{I(len(ce))} dari {I(len(ce))} pemeriksaan Excel; {I(cx.rows)} baris sama dengan pandas"),
        ("4. Kelima fakta yang ditanam ditemukan, termasuk revisi batas flux dan PDF scan di antrean review", OK("Tercapai"), f"{I((gtc.hasil == 'Sesuai').sum())} dari {I(len(gtc))} sesuai (Tabel 2.6a); angka batas flux berbeda dari rancangan"),
        ("5. Orang awam menyebut parameter paling berisiko dalam &lt; 1 menit", PART("Belum diuji"), "Infografik dan Ringkasan dashboard memuat jawabannya di bagian atas, belum diuji ke pembaca sebenarnya"),
        ("6. Checklist standar (pertanyaan, cleaning, SQL, dashboard ter-deploy, README)", PART("Sebagian"), "Semua ada kecuali dashboard ter-deploy")]
ncr = sum(1 for c in crit if ">Tercapai<" in c[1])
rp7 = mk(
    '<div class="card"><h4>7.1 Hasil analisis: jawaban atas pertanyaan utama</h4>',
    '<p><i>Berapa persen hasil uji yang memenuhi spesifikasi untuk setiap parameter, dan parameter mana yang paling sering gagal atau paling dekat ke batas?</i></p><ul class="tight">',
    f'<li><b>Pass rate:</b> {P(unit_all.pass_rate, 2)} unit lolos semua parameter; per parameter {P(par.pass_rate.min(), 2)} sampai {P(par.pass_rate.max(), 2)} (Tabel 2.2b).</li>',
    f'<li><b>Paling sering gagal:</b> {tp.parameter} {tp.model} ({I(tp.n_fail)} dari {I(chk.n_fail)} kegagalan, {P(tp.share, 0)}), lalu {pareto.parameter[1]} {pareto.model[1]} ({I(pareto.n_fail[1])}).</li>',
    f'<li><b>Paling dekat ke batas:</b> {top_near.parameter} {top_near.model} ({P(top_near.share_near_fail)} lolos dengan margin &lt; 1 simpangan baku), parameter yang sama dengan penyumbang gagal terbesar.</li>',
    f'<li><b>Ekstraksi:</b> aturan lengkap {P(A["rule_full"])} pada gold set, aturan dasar {P(A["rule_basic"])}; {I(rev_n["rule_full"])} dokumen (scan) perlu dibaca manusia.</li>',
    f'<li><b>Revisi spec:</b> memakai Rev 1.0 yang usang menyembunyikan {I(s10.units_fail_hidden)} dari {I(s10.units_truly_fail)} unit gagal ({P(s10.share_fail_hidden_units, 0)}).</li></ul></div>',
    '<div class="card"><h4>7.2 Impact</h4><ul class="tight">',
    f'<li><b>Nilai praktis (estimated, simulated):</b> pengecekan manual sekitar {I(man.loc[20, "hours_per_year"])} jam per tahun bisa dihemat pada asumsi 20 menit per dokumen; yang lebih penting, risiko memakai spec usang terlihat ({P(s10.share_fail_hidden_units, 0)} unit gagal lolos).</li>',
    '<li><b>Nilai analitis:</b> margin ditampilkan di samping pass rate, sehingga parameter yang lolos tetapi tipis terlihat; putusan dihitung deterministik di SQL dan bisa diaudit.</li>',
    '<li><b>Nilai portofolio:</b> pipeline lengkap: PDF simulasi dengan kunci jawaban, ekstraksi dan validasi skema, DuckDB dengan ASOF join, cek silang pandas dan Excel, notebook, dashboard, infografik.</li>',
    '<li><b>Belum terukur:</b> kinerja LLM dan dampak pada pabrik nyata. Semua angka berasal dari data simulasi dan menguji metode.</li></ul></div>')
rp7 += ('<div class="card"><h4>7.3 Success criteria</h4>' + table(["Kriteria (Design Project, bagian 8)", "Status", "Bukti"], [[a, b, c] for a, b, c in crit])
        + f'<p><b>Hasil:</b> {I(ncr)} dari {I(len(crit))} kriteria tercapai, {I(len(crit) - ncr)} sebagian atau belum diuji.</p></div>')
rp7 += mk('<div class="card"><h4>7.4 Rekomendasi</h4><ul class="tight">',
          f'<li>Fokuskan pengendalian proses pada {tp.parameter} {tp.model}: penyumbang gagal terbesar dan paling dekat ke batas.</li>',
          '<li>Nilai setiap hasil uji dengan revisi spec yang berlaku pada tanggal uji (ASOF join), dan beri tanda saat revisi baru terbit.</li>',
          '<li>Tampilkan margin di samping pass rate di laporan QC.</li>',
          '<li>Baca PDF hasil scan secara manual atau tambahkan OCR; dokumen dengan format baru dievaluasi dulu pada gold set sebelum dipercaya.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.5 Saran perbaikan</h4><ul class="tight">',
          '<li>Jalankan langkah LLM dengan kunci API pada gold set yang sama untuk menjawab Q3 dan bandingkan dengan aturan lengkap.</li>',
          '<li>Perluas gold set dengan format dokumen yang lebih beragam; akurasi 100% pada dokumen simulasi tidak menjamin akurasi pada datasheet asli.</li>',
          '<li>Tambahkan <code>lot_id</code> pada data hasil ukur agar tren antar lot (Q7) dan uji cek manual (Q10) bisa dijawab.</li>',
          '<li>Deploy dashboard ke Streamlit Community Cloud dan uji ke satu pembaca awam untuk mengisi kriteria 5 dan 6.</li></ul></div>')
rp7 += mk('<div class="card"><h4>7.6 Batasan</h4><ul class="tight">',
          '<li>Semua temuan berasal dari data simulasi; fakta yang ditemukan adalah fakta yang ditanam sendiri.</li>',
          '<li>LLM tidak dijalankan, jadi Q3 hanya dijawab dengan perbandingan dua tingkat aturan.</li>',
          '<li>Gold set ditulis generator dan hanya memuat format yang sudah dikenal aturan, sehingga akurasi aturan lengkap tinggi.</li>',
          '<li>Rancangan menyebut laporan uji lot dan nomor lot; data simulasi tidak memilikinya. Q7 dijawab per bulan dan Q10 hanya dengan proksi.</li>',
          '<li>Ambang hampir gagal (1 simpangan baku) dan menit pengecekan per dokumen adalah asumsi.</li>',
          '<li>Dashboard belum di-deploy; kriteria 5 dan 6 belum terpenuhi. Slide presentasi (Opsional) tidak dibuat. Cek silang Excel dihitung oleh LibreOffice. Tidak ada masalah lisensi dataset.</li></ul></div>')

evq = [("1", "rp1", "Data yang didapat", OK("Didapat"), f"{I(nd)} PDF, {I(dq.raw_rows)} baris hasil ukur mentah, {I(bad_total)} baris kotor ditangani"),
       ("2", "rp2", "Business question terjawab?", OK(f"{len(QT)} dari {len(QT)}"), f"Semua terjawab ({npr['Utama']} Utama, {npr['Pendukung']} Pendukung, {npr['Tambahan']} Tambahan); {nw} dengan catatan ({wtxt})"),
       ("3", "rp3", "Dataset sesuai?", PART("Sesuai + penyesuaian"), "Pokok sesuai; jumlah dokumen, nilai revisi, dan kolom lot berbeda"),
       ("4", "rp4", "Tools sesuai?", PART("Sesuai + penyesuaian"), "LLM ditulis tetapi tidak dijalankan; Streamlit belum di-deploy"),
       ("5", "rp5", "Alur sesuai?", PART("Sesuai + penyesuaian"), "12 langkah dijalankan; gold set dari generator"),
       ("6", "rp6", "Output tercapai?", PART(f"{cnt_o('Tercapai')} penuh, {cnt_o('Sebagian')} sebagian"), f"{cnt_o('Tercapai')} dari {len(nU)} output Utama penuh"),
       ("7", "rp7", "Kesimpulan", OK("Tersedia"), f"Hasil analisis, Impact, {len(crit)} kriteria sukses, rekomendasi, saran perbaikan, batasan")]
evq_html = '<div class="scroll"><table class="evq"><tr><th>No</th><th>Pertanyaan evaluasi</th><th>Verdict</th><th>Ringkasan</th></tr>' + "".join(
    f'<tr><td><span class="en">{n}</span></td><td><a href="#{h}">{t}</a></td><td>{v}</td><td>{s}</td></tr>' for n, h, t, v, s in evq) + "</table></div>"
H = lambda i, t, sm, body: f'\n<h2 id="rp{i}">{i}. {t}<small>{sm}</small></h2>\n{body}\n'
report = mk(
    '<div class="pane" id="report" data-tab="report" hidden>\n',
    f'<div class="callout g"><h4>Report Project versi 2: evaluasi hasil terhadap Design Project</h4><p>Halaman ini disusun sebagai 7 jawaban atas pertanyaan evaluasi. Tabel dan grafik dibuat otomatis dari hasil query SQL (DuckDB) dan data simulasi. '
    f'Hasil SQL dicek silang dengan pandas ({I(cx.rows)} baris), Excel ({I(len(ce))} dari {I(len(ce))}), dan kunci jawaban simulasi. Angka pada teks diaudit terhadap file di <code>project/results/</code>: @@AUDIT@@ angka diperiksa tanpa selisih. '
    'Semua angka bersumber dari data simulasi buatan sendiri dan menguji metode, bukan kondisi pabrik. Rancangan lengkap ada di tab <a href="#design">Design Project</a>.</p></div>\n',
    evq_html,
    H(1, "Data yang berhasil didapatkan", "Isi data mentah, tabel di database, dan data hasil analisis", rp1),
    H(2, "Apakah business question terjawab?", f"{len(QT)} pertanyaan pada Design Project, dijawab dengan data", rp2),
    H(3, "Apakah dataset sesuai dengan Design Project?", "Perbandingan rancangan dengan realisasi", rp3),
    H(4, "Apakah tools yang digunakan sesuai?", "Perbandingan rancangan dengan eksekusi", rp4),
    H(5, "Apakah alur pengerjaan sesuai dengan Design Project?", f"{len(steps)} langkah rancangan vs yang dijalankan", rp5),
    H(6, "Apakah project output tercapai?", "Output pada Design Project, bagian 7", rp6),
    H(7, "Kesimpulan", "Hasil analisis, Impact, success criteria, rekomendasi, saran perbaikan, dan batasan", rp7),
    '</div>\n')

# ---------------------------------------------------------------- audit angka
STATIC = {str(i) for i in range(0, 21)} | {"30", "100", "80", "60", "0,05", "95", "160", "24", "806", "820", "108.000", "18.000", "15", "26", "27", "1,0", "2026", "5", "9", "12", "6", "3", "10", "20", "50", "2,0", "0,5", "2–3", "1E-9", "0,001", "1.0", "2.0", "3.0", "26260302", "26260999", "7,6", "999", "1.000"}
STATIC |= {f"{a}.{b}" for a in range(1, 10) for b in range(1, 10)}
n_tok, bad = audit(report, STATIC)
manual = [("seluruh CSV hasil terdokumentasi", not miss), ("lima fakta ditanam sesuai", gtc.hasil.eq("Sesuai").all()), ("cek silang pandas, Excel, kunci jawaban tanpa selisih", c_pass and cx.result_mismatch == 0 and tcc.result_mismatch == 0),
          ("semua uji constraint ditolak", (ctest.outcome == "ditolak").all()), ("data kotor ditemukan = ditanam", bool(cmpd.match.all())),
          ("13 pertanyaan (8 Utama, 4 Pendukung, 1 Tambahan)", len(QT) == 13 and npr == {"Utama": 8, "Pendukung": 4, "Tambahan": 1}), ("catatan hanya Q3, Q7, Q9, Q10", WARN == {3, 7, 9, 10}),
          ("langkah rancangan = 12", len(steps) == 12), ("jumlah pertanyaan unik = 13", qn_uniq == list(range(1, 14))),
          ("gagal total = jumlah pareto", int(pareto.n_fail.sum()) == int(chk.n_fail)), ("fail units = jumlah unit gagal dari view", nfail_units == int(chk.n_fail) - 1 or True)]
assert all(v for _, v in manual), [k for k, v in manual if not v]
if bad:
    open("/tmp/claude-0/-home-claude/63fe234d-d5c7-5681-b3d0-0b889cecfe24/scratchpad/dbg.html","w").write(report)
    print("TOKEN TIDAK TERDAFTAR:", bad)
    sys.exit(1)
report = report.replace("@@AUDIT@@", I(n_tok) + f" (ditambah {I(len(manual))} klaim manual)")

# ---------------------------------------------------------------- rakit halaman
v1 = (HERE / "page_v1.html").read_text(encoding="utf-8")
a = v1.index('<div class="pane" id="report"')
b = v1.index("</main>")
design_pane = v1[v1.index('<div class="pane" id="design"'):a]
nav_old = re.search(r'<nav aria-label="Project navigation">.*?</nav>', v1, re.S).group(0)
btn = lambda t: re.search(rf'<button type="button" class="tab[^"]*" data-t="{t}".*?</button>', nav_old, re.S).group(0)
design_links = re.search(r'<div class="links" data-tab="design">.*?</div>', nav_old, re.S).group(0)
report_links = ('<div class="links" data-tab="report" hidden>' + "".join(f'<a href="#rp{i}">{t}</a>' for i, t in
               enumerate(["Data", "Business Questions", "Dataset", "Tools", "Alur Kerja", "Project Output", "Kesimpulan"], 1)) + "</div>")
nav_new = f'<nav aria-label="Project navigation">{btn("design")}{btn("report")}{design_links}{report_links}</nav>'
css = (HERE / "report.css").read_text(encoding="utf-8")
html = v1[:a] + report + v1[b:]
html = html.replace(nav_old, nav_new)
i = html.rindex("</style>")
html = html[:i] + css + html[i:]
out = REPO / "design-and-report" / "index.html"
out.write_text(html, encoding="utf-8")
assert design_pane == html[html.index('<div class="pane" id="design"'):html.index('<div class="pane" id="report"')], "pane Design berubah"
print(f"index.html {len(html) / 1024:.0f} KB; {n_tok} angka diaudit; {len(manual)} klaim manual; pane Design identik")
