# Aturan pass/fail dan revisi spec (Project 26)

**Parameter (6):** luminous_flux (lm), power (W), efficacy (lm/W), cct (K), cri (Ra), power_factor (tanpa satuan).

**Putusan per parameter.** Lolos jika nilai ≥ batas bawah (bila ada) dan ≤ batas atas (bila ada). Batas termasuk (nilai tepat di batas dinyatakan lolos). Putusan dihitung oleh SQL (`compliance_result`), tidak pernah oleh LLM.

**Putusan unit.** Unit lolos bila semua parameter yang diukur pada unit itu lolos (`unit_result`).

**Revisi yang berlaku.** Setiap hasil ukur dipasangkan dengan revisi spec model yang sama dengan `valid_from` terbesar yang tidak melewati tanggal uji (ASOF join). Bukan revisi terbaru.

**Margin.** Jarak nilai ke batas terdekat: `margin_abs` (satuan parameter), `margin_pct` (dibagi batas terdekat), `margin_sd` (dibagi simpangan baku parameter pada model itu). Negatif berarti gagal.

**Hampir gagal.** Lolos tetapi `margin_sd` < 1,0 (asumsi; sensitivitas 0,5 / 1,0 / 2,0 di `near_fail_sensitivity.csv`).

**Pass rate.** Jumlah lolos ÷ jumlah hasil ukur, dengan interval Wilson 95%. Kelompok dengan n < 30 tidak dilaporkan sebagai angka tegas.

**Dokumen perlu review.** Dokumen yang gagal validasi skema (parameter hilang, satuan tidak dikenal, batas bawah ≥ batas atas, atau tanpa lapisan teks) masuk `review_queue.csv`. Tidak ada OCR.

**Spec berbeda antar format untuk (model, revisi, parameter) yang sama** dicatat di `spec_conflicts.csv`; satu nilai dipilih bila semua format sepakat.
