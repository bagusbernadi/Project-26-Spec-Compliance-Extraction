# Data simulasi

- Versi data: v1
- Tanggal dibuat: 28 Okt 2026
- Seed: 26260302 (dokumen) dan 26260999 (pengukuran)
- Data tidak disimpan di repo. Dibuat ulang (hasil identik) dengan:

```
pip install numpy pandas openpyxl Faker reportlab Pillow   # sesuai impor skrip
python scripts/generate_docs.py
python scripts/generate_measurements.py
```

- Hasil di `data/sim/`: 24 PDF datasheet (1 PDF scan tanpa lapisan teks), `dim_spec_truth.csv`, `gold_set.csv` (160 field), `measurement.csv` (108.540 baris), `truth_compliance.csv`, ground truth.
- Uji determinisme: dijalankan 2x, SHA-256 semua berkas identik. Daftar hash ada di repo DataCenter, `simulasi/fingerprints/project-26.sha256`.
