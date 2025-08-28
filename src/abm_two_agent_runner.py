"""Compatibility shim for LangFlow scan-time imports.

Provides `abm_two_agent_runner.run` by re-exporting the actual implementation
from `abm.lf_components.audiobook.abm_two_agent_runner`.
"""

from __future__ import annotations

from abm.lf_components.audiobook.abm_two_agent_runner import run  # re-export

__all__ = ["run"]
