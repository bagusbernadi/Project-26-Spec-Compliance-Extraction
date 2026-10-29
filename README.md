# Project 26: Spec Compliance Extraction

Membaca batas spesifikasi dari PDF datasheet lampu LED menjadi tabel terstruktur, mencocokkannya dengan hasil ukur produksi, lalu mencari parameter yang paling sering gagal atau paling dekat ke batas. **Data simulasi** buatan sendiri; hasilnya menguji metode, bukan kondisi pabrik.

- Rancangan dan laporan (halaman web): `design-and-report/index.html`
- Dashboard: `streamlit run code/3-presentation/streamlit/app.py` (dari folder `project/`; belum di-deploy)
- Infografik: `project/results/3-presentation/infographic.png`

## Masalah
Batas spec ada di PDF dan disalin manual ke Excel. Salah salin, salah satuan, atau memakai revisi lama mengubah putusan lolos/gagal.

## Data
24 PDF datasheet simulasi (3 model x 3 revisi, 5 format, 1 hasil scan) dan 108.540 baris hasil ukur mentah (18.000 unit). 2.700 baris (2,49%) kotor, semuanya ditemukan dan ditangani (105.939 baris bersih). Seed tetap, hasil identik setiap dijalankan (`project/data/README.md`).

## Temuan
- **Ekstraksi:** akurasi aturan dasar 46,9%, aturan lengkap 100,0% pada gold set 160 field. Aturan dasar gagal pada format kalimat, label singkatan, dan tabel terpotong. Dokumen lolos validasi skema: 9 dari 24 (dasar) dan 23 dari 24 (lengkap); 1 PDF hasil scan masuk antrean review (tanpa OCR). Langkah LLM tersedia di `extract/llm.py` tetapi belum dijalankan (tidak ada kunci API).
- **Compliance:** 98,59% unit lolos semua parameter (17.746 dari 18.000). cri 12W adalah penyumbang gagal terbesar (93 dari 255, 36%).
- **Margin:** cri 12W paling dekat ke batas (12,3% hasil lolos dengan margin kurang dari 1 simpangan baku).
- **Revisi spec:** dinilai dengan Rev 1.0 yang sudah usang, 54 dari 254 unit gagal (21,3%) tampak lolos.
- **Antar model:** perbedaan pass rate signifikan (chi-square, koreksi Holm) untuk cri, power_factor, luminous_flux. Tren bulanan menurun tipis (Cochran-Armitage, p 0,007).
- **Validasi:** SQL sama dengan pandas (105.939 baris), dengan Excel (54 dari 54 PASS), dan dengan kunci jawaban simulasi (0 selisih).

## Rekomendasi
1. Pantau cri 12W lebih dulu.
2. Selalu nilai hasil uji dengan revisi spec yang berlaku pada tanggal uji (ASOF join), bukan revisi terbaru.
3. Baca PDF hasil scan secara manual atau tambahkan OCR; PDF dengan format baru perlu masuk gold set.
4. Tampilkan margin di samping pass rate.

## Dampak (estimated, simulated)
Pengecekan manual sekitar 16 jam per tahun pada asumsi 20 menit per dokumen (rentang 8 sampai 24 jam untuk 10 sampai 30 menit). Menit per dokumen adalah asumsi.

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
