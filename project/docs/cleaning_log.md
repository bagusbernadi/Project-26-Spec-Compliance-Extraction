# Log cleaning hasil ukur

Mentah 108.540 baris, bersih 105.939 baris, bermasalah 2.700 (2,49%). Semua temuan sama dengan yang ditanam generator (`dirty_found_vs_planted.csv`).

| Aturan | Masalah | Ditemukan | Dibuang | Diperbaiki | Keputusan |
|---|---|---|---|---|---|
| R1 | Baris ganda (unit_id dan parameter sama, isi identik) | 540 | 540 | 0 | Dibuang; baris pertama dipertahankan |
| R2 | Nilai kosong | 981 | 981 | 0 | Dibuang; tidak ada dasar untuk menebak nilai |
| R3 | Nilai berupa teks N/A | 540 | 540 | 0 | Dibuang |
| R4 | Nilai sentinel -999 | 540 | 540 | 0 | Dibuang |
| R5 | Power dalam mW (nilai 1.000 kali lebih besar) | 99 | 0 | 99 | Dikonversi ke W (dibagi 1.000) |
| R6 | Satuan tidak sesuai kamus parameter (selain mW pada power) | 0 | 0 | 0 | Dibuang |
