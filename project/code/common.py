"""Pengaturan bersama untuk semua skrip Project 26. Semua jalur relatif terhadap folder project/."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # folder project/
CODE = ROOT / "code"
DATA = ROOT / "data"
RAW_DIR = DATA / "raw"                                 # data simulasi mentah (tidak di-commit)
DOCS_PDF = RAW_DIR / "docs"                            # 24 PDF simulasi (tidak di-commit; contoh kecil di data/sample/)
CLEAN_DIR = DATA / "clean"                             # hasil ukur bersih (tidak di-commit)
SAMPLE_DIR = DATA / "sample"                           # contoh kecil yang di-commit (PDF, gold set, kebenaran spec)
DB_PATH = ROOT / "spec_compliance.duckdb"
SQL_PREP = CODE / "1-data-preparation" / "sql"
SQL_ANALYSIS = CODE / "2-analysis" / "sql"
HTML_DIR = CODE / "3-presentation" / "html"
RES_PREP = ROOT / "results" / "1-data-preparation"
RES_ANALYSIS = ROOT / "results" / "2-analysis"
RES_PRESENT = ROOT / "results" / "3-presentation"
DOCS_DIR = ROOT / "docs"
for _d in (RAW_DIR, CLEAN_DIR, SAMPLE_DIR, RES_PREP, RES_ANALYSIS, RES_PRESENT, DOCS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

SEED_DOCS, SEED_MEAS = 26260302, 26260999              # seed generator (nilai yang sama ada di skrip generator)
DATA_VERSION, DATA_DATE = "v1", "28 Okt 2026"
PARAMS = ["luminous_flux", "power", "efficacy", "cct", "cri", "power_factor"]
MODELS = ["5W", "9W", "12W"]
LATEST_REV = "Rev 3.0"

# Ukuran dan batas yang tidak didefinisikan rancangan (asumsi, diuji sensitivitasnya; lihat docs/compliance_rules.md)
NEAR_FAIL_SD = 1.0                                     # "hampir gagal": lolos, jarak ke batas terdekat < 1 simpangan baku
NEAR_FAIL_SCENARIOS = [0.5, 1.0, 2.0]
TARGET_PASS_RATE = 0.95                                # garis target pada simulasi rancangan (bagian 3 Design)
MANUAL_MIN_PER_DOC = 20                                # menit pengecekan manual per dokumen (asumsi, estimated)
MANUAL_MIN_SCENARIOS = [10, 20, 30]
DOCS_PER_YEAR_FACTOR = 2                               # data mencakup sekitar 6 bulan, dikali 2 menjadi setahun (asumsi)
MIN_N_PER_GROUP = 30                                   # jumlah unit minimum per kelompok untuk pass rate


def result(name):
    """Cari CSV hasil di folder hasil per tahap."""
    for d in (RES_PREP, RES_ANALYSIS, RES_PRESENT):
        p = d / name
        if p.exists():
            return p
    raise FileNotFoundError(name)


def chdir_root():
    os.chdir(ROOT)
