"""Compatibility shim for ABMChunkIterator.

This module preserves the old name by re-exporting ABMBlockIterator as ABMChunkIterator.
Prefer importing ABMBlockIterator from abm_block_iterator going forward.
"""

from __future__ import annotations

from abm.lf_components.audiobook.abm_block_iterator import ABMBlockIterator as ABMChunkIterator

__all__ = ["ABMChunkIterator"]
