from __future__ import annotations

import os
from pydantic import BaseModel, Field


class Settings(BaseModel):
    log_level: str = Field(default=os.getenv("LOG_LEVEL", "INFO"))
    trace: bool = Field(default=os.getenv("TRACE", "0") == "1")
    output_dir: str = Field(default=os.getenv("OUTPUT_DIR", "./output"))
    fake_mode: bool = True  # always true for initial scaffold


def get_settings() -> Settings:
    return Settings()
