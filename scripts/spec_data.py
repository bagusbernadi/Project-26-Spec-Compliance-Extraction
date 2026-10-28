"""Spesifikasi kebenaran (truth) lampu LED simulasi: dipakai bersama oleh generate_docs.py dan generate_measurements.py."""
MODELS = ["5W", "9W", "12W"]
REVS = ["Rev 1.0", "Rev 2.0", "Rev 3.0"]
EFFECTIVE = {"Rev 1.0": "2026-03-01", "Rev 2.0": "2026-05-01", "Rev 3.0": "2026-07-01"}
PARAMS = ["luminous_flux", "power", "efficacy", "cct", "cri", "power_factor"]
UNIT = {"luminous_flux": "lm", "power": "W", "efficacy": "lm/W", "cct": "K", "cri": "Ra", "power_factor": ""}
# (min, max); None = tidak dibatasi
BASE = {
    "5W":  {"luminous_flux": (400, None), "power": (None, 5.5), "efficacy": (75, None), "cct": (6000, 7000), "cri": (80, None), "power_factor": (0.50, None)},
    "9W":  {"luminous_flux": (800, None), "power": (None, 9.5), "efficacy": (85, None), "cct": (6000, 7000), "cri": (80, None), "power_factor": (0.50, None)},
    "12W": {"luminous_flux": (1100, None), "power": (None, 12.5), "efficacy": (90, None), "cct": (6000, 7000), "cri": (80, None), "power_factor": (0.90, None)},
}
SPEC = {m: {r: dict(BASE[m]) for r in REVS} for m in MODELS}
for r in ("Rev 2.0", "Rev 3.0"):
    SPEC["9W"][r]["luminous_flux"] = (830, None)          # revisi batas luminous flux 9W mulai bulan ke-3 (Rev 2.0)
for m, v in (("5W", 78), ("12W", 92)):
    SPEC[m]["Rev 3.0"]["efficacy"] = (v, None)            # perubahan kecil di Rev 3.0
# rata-rata dan simpangan baku hasil ukur (margin CRI 12W paling tipis)
MEAS = {
    "5W":  {"luminous_flux": (440, 14), "power": (5.10, 0.12), "efficacy": (86, 2.5), "cct": (6500, 130), "cri": (84.0, 1.4), "power_factor": (0.62, 0.04)},
    "9W":  {"luminous_flux": (880, 22), "power": (8.90, 0.20), "efficacy": (100, 3.0), "cct": (6500, 130), "cri": (84.0, 1.4), "power_factor": (0.60, 0.04)},
    "12W": {"luminous_flux": (1190, 28), "power": (11.70, 0.25), "efficacy": (101, 3.0), "cct": (6500, 130), "cri": (81.8, 0.9), "power_factor": (0.95, 0.015)},
}


def rev_on(date_str):
    """Revisi spec yang berlaku pada tanggal uji (YYYY-MM-DD)."""
    cur = REVS[0]
    for r in REVS:
        if date_str >= EFFECTIVE[r]:
            cur = r
    return cur
