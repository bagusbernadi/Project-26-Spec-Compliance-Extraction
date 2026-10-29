"""Ekstraksi spec dengan LLM (Claude API) dan keluaran terstruktur sesuai skema Pydantic.

TIDAK DIJALANKAN saat project ini dibuat: sandbox pembuatan project tidak punya ANTHROPIC_API_KEY dan tidak bisa menjangkau API.
Kode ini disertakan agar langkah rancangan "LLM dengan output terstruktur" bisa dijalankan sendiri:

    export ANTHROPIC_API_KEY=...        # lalu
    python project/code/1-data-preparation/python/04_extract_specs.py --llm

Hasilnya ditulis ke data/raw/llm_cache/<nama pdf>.json (satu panggilan per dokumen) dan dibaca oleh 05_evaluate_extraction.py sebagai metode "llm"
bila berkasnya ada. Yang dikirim hanya teks dokumen spec simulasi, bukan data perusahaan.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

import pdfplumber

from .schema import SpecDoc

MODEL_NAME = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5-5")
PROMPT = (
    "Kamu membaca datasheet spesifikasi lampu LED. Ambil model lampu, nomor revisi, tanggal berlaku, dan batas bawah (lower), batas atas (upper), "
    "dan satuan untuk enam parameter: luminous_flux, power, efficacy, cct, cri, power_factor. Gunakan satuan baku: lm, W, lm/W, K, Ra, dan string kosong untuk "
    "power_factor. Tanda '-' berarti tidak ada batas (null). Isi 'page' dengan nomor halaman tempat baris itu tertulis. Jangan menebak: jika tidak tertulis, "
    "jangan buat barisnya. Jawab hanya lewat alat yang disediakan."
)


def pdf_text(path: Path) -> str:
    with pdfplumber.open(path) as pdf:
        return "\n".join(f"[halaman {i}]\n{p.extract_text() or ''}" for i, p in enumerate(pdf.pages, 1))


def extract_one(path: Path, client) -> dict:
    tool = {"name": "simpan_spec", "description": "Menyimpan hasil ekstraksi spec", "input_schema": SpecDoc.model_json_schema()}
    msg = client.messages.create(model=MODEL_NAME, max_tokens=2000, system=PROMPT, tools=[tool], tool_choice={"type": "tool", "name": "simpan_spec"},
                                 messages=[{"role": "user", "content": pdf_text(path)}])
    data = next(b.input for b in msg.content if b.type == "tool_use")
    SpecDoc.model_validate(data)         # bentuk salah langsung tertangkap sebelum masuk database
    return data


def run_all(pdf_dir: Path, cache_dir: Path) -> int:
    import anthropic                     # pip install anthropic
    client = anthropic.Anthropic()
    cache_dir.mkdir(parents=True, exist_ok=True)
    n = 0
    for p in sorted(pdf_dir.glob("*.pdf")):
        out = cache_dir / (p.stem + ".json")
        if out.exists():
            continue
        with pdfplumber.open(p) as pdf:
            if not any(len(pg.chars) for pg in pdf.pages):
                continue                 # hasil scan: tanpa OCR
        out.write_text(json.dumps(extract_one(p, client), ensure_ascii=False, indent=1), encoding="utf-8")
        n += 1
    return n


def cache_to_fields(cache_dir: Path):
    """Mengubah JSON hasil LLM menjadi tabel field (kolom sama dengan extracted_fields.csv, method = llm). Kosong bila belum pernah dijalankan."""
    import pandas as pd
    rows = []
    for p in sorted(Path(cache_dir).glob("*.json")) if Path(cache_dir).exists() else []:
        for r in json.loads(p.read_text(encoding="utf-8"))["rows"]:
            for fld, val in (("min", r.get("lower")), ("max", r.get("upper")), ("unit", r.get("unit", ""))):
                rows.append(dict(doc=p.stem + ".pdf", method="llm", parameter=r["parameter"], field=fld, value=val, page=r.get("page"), unit_source="dokumen"))
    return pd.DataFrame(rows, columns=["doc", "method", "parameter", "field", "value", "page", "unit_source"])
