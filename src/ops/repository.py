"""Dagster repository definition bundling project assets."""

from __future__ import annotations

from dagster import Definitions

from .assets import chapter_annotations, chapters_clean

all_assets = [chapters_clean, chapter_annotations]

defs = Definitions(assets=all_assets)
