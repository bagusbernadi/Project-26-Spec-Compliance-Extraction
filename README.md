[← Back to portfolio](https://bagusbernadi.github.io/)

# Project 26: Spec Compliance Extraction

**Status: Design (rancangan).** Halaman rancangan ada di [`index.html`](index.html). Ekstraksi, analisis, dashboard, dan angka hasil belum dikerjakan, sehingga bagian Analysis, Recommendation, dan Impact di bawah masih kosong.

**Tujuan:** membangun pipeline yang membaca batas spesifikasi dari dokumen PDF menjadi tabel terstruktur, lalu membandingkannya dengan hasil ukur produk, untuk menemukan parameter yang paling sering gagal atau paling dekat ke batas, sehingga pengendalian proses bisa difokuskan ke parameter yang paling berisiko.

| | |
|---|---|
| Kategori | Manufaktur (pabrik lampu LED) |
| Tingkat | Menengah–lanjut |
| Data | Simulasi: datasheet PDF dan hasil ukur dibuat sendiri (generator disertakan) |
| Tools | Python (pdfplumber, pypdf, pandas), LLM (Claude API), Pydantic, DuckDB + SQL, Excel, Streamlit + Plotly |

## 1. Problem

**Pertanyaan utama:** Berapa persen hasil uji yang memenuhi spesifikasi untuk setiap parameter, dan parameter mana yang paling sering gagal atau paling dekat ke batas?

Rancangan memecahnya menjadi 13 pertanyaan (8 Utama, 4 Pendukung, 1 Tambahan) dalam 5 tema: ekstraksi, compliance, revisi, dampak, dan validitas.

## 2. Data

- Sumber: data simulasi buatan sendiri, dibuat oleh `scripts/generate_docs.py` dan `scripts/generate_measurements.py` (Versi: v1; Tanggal dibuat: 28 Okt 2026; Seed: 26260302). Tidak memakai datasheet produsen atau data perusahaan.
- Konteks: lampu LED model 5W, 9W, dan 12W, masing-masing 3 revisi spec; 6 parameter (luminous flux, daya, efikasi, CCT, CRI, power factor).
- Ukuran (perkiraan): ±24 dokumen PDF; ±108.000 nilai hasil ukur (±18.000 unit × 6 parameter); gold set ±160 field berlabel manual.
- Rencana tabel: `dim_spec`, `extraction_eval`, `measurement`, `compliance_result`.
- Fakta yang sengaja ditanam: CRI model 12W dengan margin paling tipis, revisi batas luminous flux 9W di bulan ke-3, satuan dan simbol beragam, tabel terpotong halaman, satu PDF hasil scan, dan 2–3% hasil ukur kotor.

## 3. Analysis

Belum dikerjakan. LLM hanya dipakai untuk membaca dokumen, dan akurasinya diukur pada gold set. Putusan pass/fail dihitung dengan SQL berdasarkan revisi spec yang berlaku pada tanggal uji.

## 4. Recommendation

Belum dikerjakan. Output yang direncanakan: daftar parameter yang perlu pengendalian ketat, berdasarkan pass rate dan margin terhadap spec.

## 5. Impact

Belum dikerjakan. Rumus yang akan dipakai (semua hasil diberi label `estimated` dan `simulated`):

```
Menit dihemat per tahun = jumlah dokumen per tahun × menit pengecekan manual per dokumen
```

## Batasan yang sudah diketahui

- LLM bisa salah membaca dokumen; hasil selalu divalidasi skema dan diukur akurasinya.
- Gold set kecil, akurasi bisa berbeda pada format dokumen lain.
- PDF hasil scan hanya ditandai untuk review (tanpa OCR).
- Pass rate tinggi bisa menipu jika margin tipis, sehingga margin selalu ditampilkan.

## Struktur repository

```
index.html   Halaman rancangan project (bisa dibuka di browser atau lewat GitHub Pages)
README.md    Dokumen ini
```

Folder `docs/`, `extract/`, `data/`, `scripts/`, `sql/`, `notebooks/`, `dashboard/`, dan `outputs/` ditambahkan saat pengerjaan dimulai.
