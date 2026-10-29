"""Langkah 13: membuat dan menjalankan dua notebook dari CSV hasil: extraction_eval.ipynb (Q1-Q3, Q12) dan analysis.ipynb (Q4-Q13)."""
import sys
from pathlib import Path

import nbformat as nbf
from nbclient import NotebookClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import common as C  # noqa: E402

M, K = nbf.v4.new_markdown_cell, nbf.v4.new_code_cell
SETUP = K("""from pathlib import Path
import pandas as pd, numpy as np, matplotlib.pyplot as plt
ROOT = Path.cwd()
while not (ROOT / 'results').exists():
    ROOT = ROOT.parent
R = lambda f: pd.read_csv(next((ROOT / 'results' / d / f) for d in ('1-data-preparation', '2-analysis', '3-presentation') if (ROOT / 'results' / d / f).exists()))
pd.options.display.float_format = '{:.4f}'.format
plt.rcParams.update({'figure.figsize': (9, 3.6), 'axes.spines.top': False, 'axes.spines.right': False})
BLUE, GREY, ORANGE = '#1A73E8', '#9AA0A6', '#E8710A'""")

ext = [
    M("# Project 26: Evaluasi ekstraksi spec dari PDF\n\nQ1 akurasi per field, Q2 jenis kesalahan, Q3 aturan dasar vs aturan lengkap (LLM belum dijalankan: tidak ada kunci API di lingkungan ini), Q12 dokumen yang perlu review. "
      "Gold set: 160 field dari 24 PDF simulasi. Semua tabel dibaca dari `results/`."), SETUP,
    M("## Q1. Akurasi per field dan format dokumen"),
    K("a = R('extraction_accuracy.csv'); a.pivot_table(index=['scope', 'group'], columns='method', values='accuracy')"),
    K("f = a[a.scope == 'Format dokumen'].pivot(index='group', columns='method', values='accuracy')\nf.plot.bar(color=[GREY, BLUE], rot=0); plt.ylabel('akurasi'); plt.title('Akurasi per format dokumen'); plt.show()"),
    M("## Q2. Kesalahan paling sering (aturan dasar)"),
    K("e = R('extraction_errors.csv'); e"),
    K("plt.bar(e.error_type, e.n, color=BLUE); plt.xticks(rotation=15); plt.ylabel('jumlah field salah'); plt.show()"),
    M("## Q3. Aturan dasar vs aturan lengkap\nKeduanya memakai pdfplumber dan regex; aturan lengkap menambah pembacaan kalimat, label singkatan, dan tabel yang terpotong. Langkah LLM (`extract/llm.py`) tersedia tetapi belum dijalankan."),
    K("R('extraction_doc_eval.csv').groupby('method').agg(dokumen=('doc', 'count'), lolos_skema=('schema_ok', 'sum'), cocok_kunci=('exact_vs_truth', 'sum'))"),
    M("## Q12. Dokumen yang perlu review manusia"),
    K("display(R('review_queue.csv')); R('doc_validation.csv').groupby('method').agg(dokumen=('doc', 'count'), perlu_review=('schema_ok', lambda s: (~s).sum()))"),
    M("## Hasil akhir: tabel dim_spec"),
    K("display(R('dim_spec.csv').head(18)); print(len(R('dim_spec.csv')), 'baris;', len(R('spec_conflicts.csv')), 'konflik antar format')"),
]
ana = [
    M("# Project 26: Analisis compliance\n\nQ4–Q13. Putusan lolos/gagal dihitung dengan aturan pasti di SQL (ASOF join ke revisi spec yang berlaku pada tanggal uji). Data adalah simulasi buatan sendiri."), SETUP,
    M("## Q4. Pass rate per parameter dan model (interval Wilson 95%)"),
    K("w = R('wilson_passrate.csv'); w"),
    M("## Q5. Pareto kegagalan"),
    K("p = R('pareto_fail.csv').head(8); plt.barh(p.parameter + ' ' + p.model, p.n_fail, color=BLUE); plt.gca().invert_yaxis(); plt.xlabel('jumlah gagal'); plt.show()"),
    M("## Q6. Margin ke batas spec (dalam simpangan baku) dan hasil hampir gagal"),
    K("display(R('margin_param_model.csv')); R('near_fail_sensitivity.csv').pivot_table(index='near_fail_sd', values='n_near_fail', aggfunc='sum')"),
    M("## Q7. Tren bulanan"),
    K("m = R('month_unit.csv'); plt.bar(m.month, m.pass_rate * 100, color=BLUE); plt.ylim(97, 100); plt.ylabel('pass rate unit (%)'); plt.show(); R('trend_month.csv')"),
    M("## Q8. Dampak revisi spec yang salah"),
    K("display(R('revision_param_model.csv').query(\"model == '9W' and parameter == 'luminous_flux'\")); R('impact_stale_spec.csv')"),
    M("## Q9. Waktu pengecekan manual (estimated)"),
    K("R('impact_manual_time.csv')"),
    M("## Q10. Unit gagal yang tampak lolos (proxy: spec usang)\nTidak ada data cek manual pada lot; proksinya adalah penilaian dengan revisi lama."),
    K("R('impact_stale_spec.csv')[['stale_revision', 'units_truly_fail', 'units_fail_hidden', 'share_fail_hidden_units']]"),
    M("## Q11. Validasi: SQL vs pandas vs Excel vs kunci jawaban simulasi, dan lima fakta yang ditanam"),
    K("print(R('pandas_crosscheck.csv').to_string()); b = R('crosscheck_excel.csv'); print(f'Excel: {(b.status == \"PASS\").sum()} dari {len(b)} PASS'); display(R('truth_compliance_check.csv')); R('ground_truth_check.csv')"),
    M("## Q13. Kualitas data hasil ukur"),
    K("display(R('cleaning_log.csv')); display(R('data_quality_summary.csv')); R('dirty_found_vs_planted.csv')"),
    M("## Beda antar model (chi-square, koreksi Holm)"),
    K("R('chi2_models.csv')"),
]
for name, cells in (("extraction_eval", ext), ("analysis", ana)):
    nb = nbf.v4.new_notebook(cells=cells, metadata={"kernelspec": {"name": "python3", "display_name": "Python 3", "language": "python"}})
    NotebookClient(nb, timeout=300, kernel_name="python3", resources={"metadata": {"path": str(C.ROOT)}}).execute()
    nbf.write(nb, C.RES_PRESENT / f"{name}.ipynb")
    errs = [o for c in nb.cells if c.cell_type == "code" for o in c.get("outputs", []) if o.output_type == "error"]
    print(name, len(nb.cells), "sel;", len(errs), "error")
    assert not errs
