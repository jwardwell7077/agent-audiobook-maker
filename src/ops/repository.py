from __future__ import annotations

from dagster import Definitions
from .assets import chapters_clean, chapter_annotations

all_assets = [chapters_clean, chapter_annotations]

defs = Definitions(assets=all_assets)
