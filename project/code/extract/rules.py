"""Ekstraksi spec dari PDF dengan aturan (pdfplumber + regex), dua tingkat:

- "rule_basic": hanya tabel berheader Parameter/Min/Max/Unit, label persis seperti format tabel standar, satuan apa adanya.
- "rule_full" : ditambah kamus sinonim label (singkatan), tabel lanjutan di halaman berikutnya (tanpa header), kalimat teks,
                normalisasi satuan (lumen -> lm, watt -> W, ...), dan satuan bawaan per parameter bila dokumen tidak menyebutnya.
PDF tanpa lapisan teks (hasil scan) tidak diproses (tanpa OCR, sesuai rancangan) dan masuk antrean review.
"""
from __future__ import annotations

import re

import pdfplumber

PARAMS = ["luminous_flux", "power", "efficacy", "cct", "cri", "power_factor"]
DEFAULT_UNIT = {"luminous_flux": "lm", "power": "W", "efficacy": "lm/W", "cct": "K", "cri": "Ra", "power_factor": ""}
BASIC_LABELS = {"Luminous flux": "luminous_flux", "Power consumption": "power", "Luminous efficacy": "efficacy", "CCT": "cct", "CRI": "cri", "Power factor": "power_factor"}
FULL_LABELS = [
    ("luminous_flux", r"^(luminous flux|flux)$"),
    ("power", r"^(power consumption|power|pwr)$"),
    ("efficacy", r"^(luminous efficacy|efficacy|eff\.?)$"),
    ("cct", r"^(cct|correlated colou?r temperature)$"),
    ("cri", r"^(cri( \(ra\))?|colou?r rendering index)$"),
    ("power_factor", r"^(power factor|pf)$"),
]
UNIT_NORM = {"lm": "lm", "lumen": "lm", "w": "W", "watt": "W", "lm/w": "lm/W", "lumen per watt": "lm/W", "k": "K", "kelvin": "K", "ra": "Ra", "cos phi": "", "": ""}
HEADER = ["Parameter", "Min", "Max", "Unit"]


def header_info(text: str) -> dict:
    m = re.search(r"LED Lamp (\d+W)", text)
    r = re.search(r"Document revision:\s*(Rev \d\.\d)\s*\|\s*Effective date:\s*(\d{4}-\d{2}-\d{2})", text)
    return {"model": m.group(1) if m else None, "revision": r.group(1) if r else None, "effective_date": r.group(2) if r else None}


def has_text_layer(pdf) -> bool:
    return any(len(p.chars) > 0 for p in pdf.pages)


def _num(s):
    s = (s or "").strip()
    if s in ("", "-", "–"):
        return None
    try:
        return float(s)
    except ValueError:
        return float("nan")


def _label_full(lab: str):
    lab = re.sub(r"\s+", " ", lab.strip().lower())
    for p, rx in FULL_LABELS:
        if re.match(rx, lab):
            return p
    return None


def _from_tables(pdf, full: bool):
    rows, prev_cols = [], False
    for pno, page in enumerate(pdf.pages, 1):
        for t in page.extract_tables():
            if not t:
                continue
            body = t
            if t[0] == HEADER:
                body, prev_cols = t[1:], True
            elif not (full and prev_cols and len(t[0]) == 4):    # tabel lanjutan tanpa header hanya dibaca oleh rule_full
                continue
            for lab, mn, mx, un in body:
                p = _label_full(lab) if full else BASIC_LABELS.get(lab)
                if p is None:
                    rows.append(dict(parameter=None, label_raw=lab, lower=_num(mn), upper=_num(mx), unit_raw=un or "", page=pno))
                    continue
                unit = (UNIT_NORM.get((un or "").strip().lower(), (un or "").strip()) if full else (un or "").strip())
                rows.append(dict(parameter=p, label_raw=lab, lower=_num(mn), upper=_num(mx), unit_raw=un or "", unit=unit, unit_source="dokumen" if (un or "").strip() else "bawaan", page=pno))
    return rows


def _from_sentences(pdf):
    out = []
    for pno, page in enumerate(pdf.pages, 1):
        text = " ".join((page.extract_text() or "").split("\n")[2:])
        for s in re.split(r"\.\s+(?=The )", text):
            s = s.strip().rstrip(".")
            m = re.match(r"The (?P<lab>[a-z ]+?) shall ", s)
            if not m:
                continue
            p = _label_full(m.group("lab"))
            lo = re.search(r"not be lower than ([\d.]+)\s*(.*?)(?= and shall|$)", s)
            hi = re.search(r"not exceed ([\d.]+)\s*(.*)$", s)
            un = (lo.group(2) if lo and lo.group(2) else (hi.group(2) if hi and hi.group(2) else "")).strip()
            un = un.split(" and shall")[0].strip()
            out.append(dict(parameter=p, label_raw=m.group("lab"), lower=float(lo.group(1)) if lo else None, upper=float(hi.group(1)) if hi else None, unit_raw=un,
                            unit=UNIT_NORM.get(un.lower(), un) if un else DEFAULT_UNIT.get(p, ""), unit_source="dokumen" if un else "bawaan", page=pno))
    return out


def extract(path, method: str):
    """Mengembalikan (info header, daftar baris, status). status: ok | no_text_layer."""
    with pdfplumber.open(path) as pdf:
        if not has_text_layer(pdf):
            return {"model": None, "revision": None, "effective_date": None}, [], "no_text_layer"
        info = header_info(pdf.pages[0].extract_text() or "")
        full = method == "rule_full"
        rows = _from_tables(pdf, full)
        if full and not rows:
            rows = _from_sentences(pdf)
    for r in rows:
        r.setdefault("unit", r.get("unit_raw", ""))
        r.setdefault("unit_source", "dokumen")
    return info, rows, "ok"
