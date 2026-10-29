"""Skema Pydantic hasil ekstraksi (langkah 2 rancangan). Bentuk yang wajib dipenuhi sebelum data masuk database."""
from __future__ import annotations

import re
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

PARAMS = ("luminous_flux", "power", "efficacy", "cct", "cri", "power_factor")
KNOWN_UNITS = {"luminous_flux": {"lm"}, "power": {"W"}, "efficacy": {"lm/W"}, "cct": {"K"}, "cri": {"Ra"}, "power_factor": {""}}
MODELS = ("5W", "9W", "12W")


class SpecRow(BaseModel):
    """Satu parameter spec dari satu dokumen."""
    parameter: str
    lower: Optional[float] = None
    upper: Optional[float] = None
    unit: str = ""
    page: int = Field(ge=1)

    @field_validator("parameter")
    @classmethod
    def known_parameter(cls, v):
        if v not in PARAMS:
            raise ValueError(f"parameter tidak dikenal: {v}")
        return v

    @model_validator(mode="after")
    def check(self):
        if self.unit not in KNOWN_UNITS[self.parameter]:
            raise ValueError(f"satuan {self.unit!r} tidak dikenal untuk {self.parameter}")
        if self.lower is None and self.upper is None:
            raise ValueError("batas bawah dan atas sama-sama kosong")
        if self.lower is not None and self.upper is not None and not self.lower < self.upper:
            raise ValueError("batas bawah harus lebih kecil dari batas atas")
        return self


class SpecDoc(BaseModel):
    """Satu dokumen spec: header dan 6 parameter."""
    model: str
    revision: str
    effective_date: str
    rows: list[SpecRow]

    @field_validator("model")
    @classmethod
    def known_model(cls, v):
        if v not in MODELS:
            raise ValueError(f"model tidak dikenal: {v}")
        return v

    @field_validator("revision")
    @classmethod
    def rev_format(cls, v):
        if not re.fullmatch(r"Rev \d\.\d", v):
            raise ValueError(f"format revisi salah: {v}")
        return v

    @field_validator("effective_date")
    @classmethod
    def date_format(cls, v):
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
            raise ValueError(f"format tanggal salah: {v}")
        return v

    @model_validator(mode="after")
    def all_parameters(self):
        got = [r.parameter for r in self.rows]
        missing = [p for p in PARAMS if p not in got]
        if missing:
            raise ValueError("parameter belum terbaca: " + ", ".join(missing))
        if len(got) != len(set(got)):
            raise ValueError("parameter ganda")
        return self
