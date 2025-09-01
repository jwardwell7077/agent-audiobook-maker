"""ABM LangFlow Components Package.

Primary components live under ``abm.lf_components.audiobook``. To maintain
compatibility with older runners/tests, we provide a few stable re-exports
that forward to the new modules.
"""

from abm.lf_components.audiobook import abm_chapter_loader as chapter_loader
from abm.lf_components.audiobook import (
	abm_chapter_loader as chapter_volume_loader,  # legacy name
)
from abm.lf_components.audiobook import (
	abm_utterance_jsonl_writer as utterance_jsonl_writer,
)

# Optional legacy names used by older tests; provide soft shims only if present.
try:
	from abm.lf_components.audiobook import abm_segment_dialogue_narration as segment_dialogue_narration  # type: ignore
except Exception:  # pragma: no cover - optional component not always present
	segment_dialogue_narration = None  # type: ignore

__all__: list[str] = [
	"chapter_loader",
	"chapter_volume_loader",
	"utterance_jsonl_writer",
	"segment_dialogue_narration",
]
