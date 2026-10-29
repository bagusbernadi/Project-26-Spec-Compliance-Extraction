"""Project 26: datasheet PDF spesifikasi lampu LED (simulasi), gold set, dan spesifikasi kebenaran. Seed tetap.

3 model (5W, 9W, 12W) x 3 revisi x beberapa format = 24 PDF: tabel bersih, tabel terpotong halaman, teks, ringkas (simbol berbeda),
dan satu PDF hasil scan (hanya gambar, tanpa lapisan teks). Hasil (project/data/raw/docs/): *.pdf; project/data/raw/: dim_spec_truth.csv,
doc_manifest.csv, gold_set.csv (+-160 field berlabel), ground_truth_docs.json.
Jalankan: python project/code/1-data-preparation/python/01_generate_docs.py   (versi data: v1; butuh reportlab dan Pillow)
"""
import io
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from common import RAW_DIR  # noqa: E402
from spec_data import EFFECTIVE, MODELS, PARAMS, REVS, SPEC, UNIT  # noqa: E402

OUT = RAW_DIR
SEED = 26260302
DATA_VERSION = "v1"
GOLD_N = 160
rng = np.random.default_rng(SEED)
LABEL = {"tabel": dict(luminous_flux="Luminous flux", power="Power consumption", efficacy="Luminous efficacy", cct="CCT", cri="CRI", power_factor="Power factor"),
         "teks": dict(luminous_flux="luminous flux", power="power", efficacy="luminous efficacy", cct="correlated colour temperature", cri="colour rendering index", power_factor="power factor"),
         "ringkas": dict(luminous_flux="Flux", power="Pwr", efficacy="Eff.", cct="CCT", cri="CRI (Ra)", power_factor="PF")}
UNITS = {"tabel": dict(UNIT), "terpotong": dict(UNIT),
         "teks": dict(luminous_flux="lumen", power="watt", efficacy="lumen per watt", cct="kelvin", cri="", power_factor=""),
         "ringkas": dict(luminous_flux="lm", power="W", efficacy="lm/W", cct="K", cri="Ra", power_factor="cos phi")}
KINDS = {"Rev 1.0": ["tabel", "teks"], "Rev 2.0": ["tabel", "terpotong", "teks"], "Rev 3.0": ["tabel", "teks", "ringkas"]}
SCAN = ("9W", "Rev 2.0", "teks")          # satu-satunya PDF hasil scan


def fmt(v):
    return "-" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))


def lines_for(model, rev, kind):
    spec, u = SPEC[model][rev], UNITS[kind.replace("_scan", "")]
    k = kind.replace("_scan", "")
    out = []
    for p in PARAMS:
        lo, hi = spec[p]
        if k == "teks":
            parts = []
            if lo is not None: parts.append(f"shall not be lower than {fmt(lo)} {u[p]}".strip())
            if hi is not None: parts.append(f"shall not exceed {fmt(hi)} {u[p]}".strip())
            out.append(f"The {LABEL['teks'][p]} {' and '.join(parts)}.")
        else:
            out.append((LABEL.get(k, LABEL["tabel"])[p], fmt(lo), fmt(hi), u[p]))
    return out


def build_pdf(path, model, rev, kind):
    st = getSampleStyleSheet()
    head = [Paragraph(f"LED Lamp {model} - Product Specification", st["Title"]), Paragraph(f"Document revision: {rev} | Effective date: {EFFECTIVE[rev]}", st["Normal"]), Spacer(1, 8 * mm)]
    k = kind.replace("_scan", "")
    if kind.endswith("_scan"):                       # PDF hasil scan: teks digambar sebagai gambar
        img = Image.new("L", (1240, 1754), 255); dr = ImageDraw.Draw(img); f = ImageFont.load_default(size=28)
        y = 100
        for ln in [f"LED Lamp {model} - Product Specification", f"Document revision: {rev}   Effective date: {EFFECTIVE[rev]}", ""] + lines_for(model, rev, k):
            dr.text((90, y), ln, fill=0, font=f); y += 52
        buf = io.BytesIO(); img.save(buf, "PNG")
        c = canvas.Canvas(str(path), pagesize=A4, invariant=1); from reportlab.lib.utils import ImageReader
        c.drawImage(ImageReader(io.BytesIO(buf.getvalue())), 0, 0, width=A4[0], height=A4[1]); c.save(); return
    doc = SimpleDocTemplate(str(path), pagesize=A4, invariant=1, title=f"LED {model} {rev}", author="simulasi")
    if k == "teks":
        body = head + [Paragraph(ln, st["Normal"]) for ln in lines_for(model, rev, k)]
    else:
        rows = lines_for(model, rev, k)
        hdr = [("Parameter", "Min", "Max", "Unit")]
        style = TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey), ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey)])
        if k == "terpotong":                        # tabel terpotong halaman: 3 baris di halaman 1, sisanya di halaman 2 tanpa header
            body = head + [Table(hdr + rows[:3], style=style), Paragraph("(continued on next page)", st["Italic"]), PageBreak(), Table(rows[3:], style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.grey)]))]
        else:
            body = head + [Table(hdr + rows, style=style)]
    doc.build(body)


(OUT / "docs").mkdir(parents=True, exist_ok=True)
manifest, truth_rows = [], []
for m in MODELS:
    for rev in REVS:
        for kind in KINDS[rev]:
            if (m, rev, kind) == SCAN: kind = "teks_scan"
            name = f"LED_{m}_{rev.replace(' ', '')}_{kind}.pdf"
            build_pdf(OUT / "docs" / name, m, rev, kind)
            manifest.append([name, m, rev, EFFECTIVE[rev], kind, "scan (tanpa lapisan teks)" if kind.endswith("_scan") else "teks"])
for m in MODELS:
    for rev in REVS:
        for p in PARAMS:
            lo, hi = SPEC[m][rev][p]
            truth_rows.append([m, rev, EFFECTIVE[rev], p, lo, hi, UNIT[p]])
truth = pd.DataFrame(truth_rows, columns=["model", "revision", "effective_date", "parameter", "limit_min", "limit_max", "unit"])
M = pd.DataFrame(manifest, columns=["file", "model", "revision", "effective_date", "format", "text_layer"])
# gold set: +-160 field berlabel dari dokumen yang punya lapisan teks
fields = [[r.file, r.model, r.revision, t.parameter, fld, getattr(t, "limit_" + fld) if fld != "unit" else t.unit]
          for r in M[M.text_layer == "teks"].itertuples() for t in truth[(truth.model == r.model) & (truth.revision == r.revision)].itertuples() for fld in ("min", "max", "unit")]
F = pd.DataFrame(fields, columns=["file", "model", "revision", "parameter", "field", "value"])
F = F[F.value.notna() & (F.value.astype(str) != "")]
G = F.iloc[sorted(rng.choice(len(F), GOLD_N, replace=False))].reset_index(drop=True)
truth.to_csv(OUT / "dim_spec_truth.csv", index=False)
M.to_csv(OUT / "doc_manifest.csv", index=False)
G.to_csv(OUT / "gold_set.csv", index=False)
(OUT / "ground_truth_docs.json").write_text(json.dumps({"seed": SEED, "version": DATA_VERSION, "n_pdf": len(M), "by_format": M["format"].value_counts().sort_index().to_dict(),
    "gold_fields": len(G), "facts": ["revisi batas luminous flux 9W di Rev 2.0 (berlaku 2026-05-01): 800 -> 830 lm", "satuan dan simbol beragam antar format",
    "tabel terpotong halaman pada format 'terpotong'", "satu PDF hasil scan: LED_9W_Rev2.0_teks_scan.pdf"]}, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"{len(M)} PDF, gold set {len(G)} field, spec truth {len(truth)} baris")
