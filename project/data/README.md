# Data simulasi

- Versi data: v1; tanggal dibuat: 28 Okt 2026; jenis: simulasi murni (tidak ada dataset pihak ketiga, tidak ada masalah lisensi).
- Seed: 26260302 (dokumen PDF) dan 26260999 (hasil ukur).
- Data mentah tidak di-commit (`data/raw/`, `data/clean/`). Dibuat ulang dengan hasil identik, dari folder `project/`:

```
pip install -r requirements.txt
python code/1-data-preparation/python/01_generate_docs.py
python code/1-data-preparation/python/02_generate_measurements.py
```

- Hasil di `data/raw/`: 24 PDF datasheet di `docs/` (1 PDF hasil scan tanpa lapisan teks), `doc_manifest.csv`, `gold_set.csv` (160 field), `dim_spec_truth.csv`, `measurement.csv` (108.540 baris), `truth_compliance.csv`, `truth_dirty.csv`, `ground_truth_docs.json`, `ground_truth_meas.json`.
- `data/sample/` (di-commit): 24 PDF, gold set, kunci spec, manifest, dan ground truth, cukup untuk menjalankan ekstraksi tanpa membuat ulang data.
- Uji determinisme: generator dijalankan dua kali, SHA-256 semua berkas identik. Daftar hash ada di repo DataCenter, `simulasi/fingerprints/project-26.sha256`.
- `truth_dirty.csv` ditambahkan setelah registri DataCenter dibuat (mencatat baris kotor yang ditanam). Berkas lain tetap identik dengan sidik jari di registri; registri perlu diperbarui untuk berkas baru ini.
