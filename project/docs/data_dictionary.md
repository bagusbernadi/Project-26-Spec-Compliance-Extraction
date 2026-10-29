# Kamus data (Project 26)

## dim_spec (satu baris = satu parameter, satu model, satu revisi)
`model` (5W/9W/12W), `revision` (Rev x.y), `valid_from` (tanggal berlaku), `parameter`, `lower_limit`, `upper_limit` (kosong = tanpa batas itu), `unit`, `source_doc`, `source_page`, `n_docs_agree`, `n_docs` (jumlah dokumen yang memuat spec ini dan yang sepakat). Kunci: (model, revision, parameter).

## measurement (satu baris = satu parameter dari satu unit)
`unit_id`, `test_date`, `model`, `parameter`, `value`, `unit`. Kunci: (unit_id, parameter). Tidak ada `lot_id` pada data simulasi, jadi analisis per lot (Q7) dilakukan per bulan.

## extraction_eval (satu baris = satu field hasil ekstraksi vs label manual)
`doc`, `model`, `revision`, `format` (tabel/teks/ringkas/terpotong/teks_scan), `parameter`, `field` (min/max/unit), `method` (rule_basic/rule_full/llm), `extracted_value`, `label_value`, `is_correct`, `error_type`.

## compliance_result (view SQL; satu baris = putusan satu parameter satu unit)
`unit_id`, `model`, `parameter`, `test_date`, `month`, `revision`, `lower_limit`, `upper_limit`, `value`, `margin_abs`, `margin_pct`, `margin_sd`, `result` (pass/fail). View `unit_result`: putusan per unit.

## Berkas hasil (results/)
Setiap CSV di `results/1-data-preparation`, `2-analysis`, `3-presentation` didokumentasikan di halaman laporan (Tabel 1.2c).
