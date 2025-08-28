"""LangFlow wrapper component to run the two-agent pipeline programmatically.

This component invokes the orchestration function in ``abm_two_agent_runner`` and
returns the aggregated results as a Data payload for wiring to downstream nodes.

Import strategy is resilient to scanning contexts by attempting the package import
first and falling back to a dynamic import.
"""

from __future__ import annotations

import importlib

from langflow.custom import Component
from langflow.io import BoolInput, IntInput, MessageTextInput, Output
from langflow.schema import Data


def _get_runner():
    """Return the pipeline run function with a resilient import strategy.

    Import order:
    1) abm.lf_components.audiobook.abm_two_agent_runner (package import)
    2) abm_two_agent_runner (compatibility shim at repo/src)
    3) Dynamic import of abm.lf_components.audiobook.abm_two_agent_runner

    Kept as a function to avoid triggering imports during LangFlow's scan.
    """
    # 1) Preferred when installed as a package or PYTHONPATH includes repo/src
    try:
        from abm.lf_components.audiobook.abm_two_agent_runner import run as run_pipeline  # type: ignore

        return run_pipeline
    except Exception:
        pass

    # 2) Try compatibility shim at src/abm_two_agent_runner.py
    try:
        from abm_two_agent_runner import run as run_pipeline  # type: ignore

        return run_pipeline
    except Exception:
        pass

    # 3) Fallback dynamic import (avoids top-level import at module load time)
    return importlib.import_module("abm.lf_components.audiobook.abm_two_agent_runner").run


class ABMTwoAgentRunner(Component):
    display_name = "ABM Two-Agent Runner"
    description = "Run the end-to-end two-agent pipeline for a chapter"
    icon = "play"
    name = "ABMTwoAgentRunner"

    inputs = [
        MessageTextInput(name="book", display_name="Book Key", value="mvs"),
        IntInput(name="chapter", display_name="Chapter (1-based)", value=1),
        MessageTextInput(name="base_dir", display_name="Repo Root (optional)", value=""),
        IntInput(name="batch_size", display_name="Batch Size", value=10),
        IntInput(name="start_chunk", display_name="Start Chunk", value=1),
        IntInput(name="max_chunks", display_name="Max Chunks (0=all)", value=10),
        BoolInput(name="dialogue_priority", display_name="Dialogue Priority", value=True),
    ]

    outputs = [
        Output(name="aggregated_results", display_name="Aggregated Results", method="execute_pipeline"),
    ]

    def execute_pipeline(self) -> Data:
        """Execute the runner and return aggregated results as Data."""
        run_pipeline = _get_runner()
        base_dir = self.base_dir or None
        results = run_pipeline(
            book=self.book,
            chapter=self.chapter,
            base_dir=base_dir,
            batch_size=self.batch_size,
            start_chunk=self.start_chunk,
            max_chunks=self.max_chunks,
            dialogue_priority=self.dialogue_priority,
        )
        return Data(data=results)
