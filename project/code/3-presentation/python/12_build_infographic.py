"""Langkah 12: one-sheet infografik (PDF dan PNG) dari CSV hasil. Dibuat sebagai HTML lalu dicetak dengan Chromium (Playwright)."""
import sys
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "code"))
sys.path.insert(0, str(ROOT.parent / "design-and-report" / "src"))
import common as C  # noqa: E402
from report_lib import BLUE, GREY, HI, SOFT, bars, hbars  # noqa: E402

R = lambda f: pd.read_csv(next(d / f for d in (C.RES_PREP, C.RES_ANALYSIS) if (d / f).exists()))
acc = R("extraction_accuracy.csv"); a = acc[acc.scope == "Semua field"].set_index("method").accuracy
unit = R("passrate_unit.csv").set_index("model").loc["Semua"]
par = R("passrate_param.csv"); par_m = R("margin_param_model.csv"); pareto = R("pareto_fail.csv")
stale = R("impact_stale_spec.csv").set_index("stale_revision").loc["Rev 1.0"]
man = R("impact_manual_time.csv").set_index("minutes_per_doc")
rq = R("review_queue.csv"); nd = R("doc_validation.csv").doc.nunique()
pc = lambda v, d=1: f"{v * 100:.{d}f}".replace(".", ",") + "%"
fi = lambda v: f"{v:,.0f}".replace(",", ".")
top = par_m.sort_values("share_near_fail", ascending=False).iloc[0]
tp = pareto.iloc[0]
par["per10k"] = par.n_fail / par.n * 10000
par = par.sort_values("per10k", ascending=False)
chart1 = bars([(r.parameter, r.per10k, HI if i == 0 else BLUE, f"{r.parameter}: {r.per10k:.0f} gagal per 10.000 hasil ukur (pass rate {pc(r.pass_rate, 2)})") for i, r in enumerate(par.itertuples())],
              lambda v: fi(v), "Gagal per 10.000 hasil ukur", h=240, rot=20, small=True)
chart2 = hbars([(f"{r.parameter} {r.model}", r.n_fail, HI if i == 0 else BLUE, f"{r.parameter} {r.model}: {fi(r.n_fail)} gagal ({pc(r.share, 1)} dari semua gagal)") for i, r in enumerate(pareto.head(6).itertuples())],
               fi, "Pareto parameter gagal", float(pareto.n_fail.max()) * 1.15)
ex = acc[acc.scope == "Format dokumen"].pivot(index="group", columns="method", values="accuracy")
chart3 = bars([(f"{g} {m}", ex.loc[g, m], col, f"{g}, {m}: {pc(ex.loc[g, m], 0)}") for g in ex.index for m, col in (("rule_basic", GREY), ("rule_full", BLUE))],
              lambda v: pc(v, 0), "Akurasi ekstraksi per format dokumen", h=240, rot=35, small=True, ymax=1.0)
html = f"""<!doctype html><html lang="id"><head><meta charset="utf-8"><title>Infografik Project 26</title><style>
@page{{size:1100px 1500px;margin:0}}*{{box-sizing:border-box}}body{{margin:0;font:16px/1.5 "Source Sans 3",Calibri,Arial,sans-serif;color:#202124;background:#F8F9FA;width:1156px;padding:28px}}
h1{{margin:0;font-size:30px;color:#174EA6}}.sub{{color:#5F6368;margin:2px 0 18px}}.row{{display:grid;gap:14px;margin-bottom:14px}}.r3{{grid-template-columns:repeat(3,1fr)}}.r2{{grid-template-columns:1fr 1fr}}
.c{{background:#fff;border:1px solid #DADCE0;border-radius:16px;padding:16px 20px}}.k b{{display:block;font-size:38px;line-height:1.1;color:#1A73E8}}.k span{{color:#5F6368;font-size:14px}}
h3{{margin:0 0 6px;font-size:18px;color:#174EA6}}svg{{width:100%;height:auto}}svg text{{fill:#5F6368;font-size:12px}}.v{{background:#E6F4EA;border:1px solid #A8DAB5;color:#0D652D}}
.w{{background:#FEF7E0;border:1px solid #FDD663;font-size:14px}}.f{{color:#5F6368;font-size:13px;margin-top:10px}}</style></head><body>
<h1>{tp.parameter.upper()} pada lampu {tp.model} paling sering gagal; {pc(unit.pass_rate, 1)} unit lolos semua parameter</h1>
<div class="sub">Project 26: Spec Compliance Extraction (lampu LED). Data simulasi Mar–Agu 2026; putusan lolos/gagal dihitung dengan aturan pasti, bukan oleh LLM.</div>
<div class="row r3"><div class="c k"><b>{pc(a['rule_basic'], 0)} → {pc(a['rule_full'], 0)}</b><span>akurasi ekstraksi spec dari PDF: aturan dasar → aturan lengkap (160 field gold set)</span></div>
<div class="c k"><b>{pc(tp.share, 0)}</b><span>dari {fi(pareto.n_fail.sum())} kegagalan berasal dari {tp.parameter} {tp.model}</span></div>
<div class="c k"><b>{pc(stale.share_fail_hidden_units, 0)}</b><span>unit gagal tampak lolos bila dinilai dengan spec Rev 1.0 yang sudah usang ({fi(stale.units_fail_hidden)} dari {fi(stale.units_truly_fail)})</span></div></div>
<div class="row"><div class="c v"><b>Kesimpulan:</b> pantau {tp.parameter} {tp.model} lebih dulu, dan pastikan setiap hasil uji dinilai dengan revisi spec yang berlaku pada tanggal uji. {len(rq)} dari {nd} dokumen (hasil scan) perlu dibaca manusia. Hasil ini membuktikan metode pada data simulasi, bukan kondisi pabrik.</div></div>
<div class="row r2"><div class="c"><h3>Gagal per 10.000 hasil ukur (tiap parameter)</h3>{chart1}</div><div class="c"><h3>Parameter dan model paling sering gagal</h3>{chart2}</div></div>
<div class="row r2"><div class="c"><h3>Akurasi ekstraksi per format dokumen</h3>{chart3}</div>
<div class="c w"><h3>Perhatikan</h3>Parameter {top.parameter} model {top.model} paling dekat ke batas: {pc(top.share_near_fail, 1)} hasilnya lolos dengan margin &lt; 1 simpangan baku. Penghematan pengecekan manual: sekitar {fi(man.loc[20, 'hours_per_year'])} jam per tahun pada asumsi 20 menit per dokumen (estimated). Langkah LLM disediakan di kode tetapi belum dijalankan pada data ini.</div></div>
<div class="f">Sumber: project/results (extraction_accuracy.csv, passrate_param.csv, pareto_fail.csv, margin_param_model.csv, impact_stale_spec.csv, impact_manual_time.csv). Semua angka berasal dari data simulasi buatan sendiri.</div></body></html>"""
out = C.RES_PRESENT
tmp = out / "infographic.html"
tmp.write_text(html, encoding="utf-8")
from playwright.sync_api import sync_playwright  # noqa: E402

with sync_playwright() as p:
    b = p.chromium.launch(); pg = b.new_page(viewport={"width": 1156, "height": 1000})
    pg.goto(tmp.as_uri()); pg.wait_for_timeout(500)
    h = pg.evaluate("document.body.scrollHeight")
    pg.set_viewport_size({"width": 1156, "height": h}); pg.screenshot(path=str(out / "infographic.png"))
    pg.pdf(path=str(out / "infographic.pdf"), width="1156px", height=f"{h + 4}px", print_background=True)
    b.close()
tmp.unlink()
print("infographic.png/pdf", h)
