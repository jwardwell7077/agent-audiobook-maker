"""ABM Casting Director for LangFlow (deprecated).

This legacy component assigned TTS voices to utterances. It has been
superseded by the spans-first pipeline and the `ABMSpanCasting` component.

We keep a minimal stub here to avoid LangFlow loader errors and to provide
an informative message in existing flows that still reference this node.
"""

from __future__ import annotations

from langflow.custom import Component
from langflow.io import BoolInput, DataInput, Output, StrInput
from langflow.schema import Data


class ABMCastingDirector(Component):
    display_name = "ABM Casting Director"
    description = "Deprecated. Use ABMSpanCasting (spans-first pipeline) instead."
    icon = "user-voice"
    name = "ABMCastingDirector"

    inputs = [
        DataInput(
            name="utterances_data",
            display_name="Utterances Data",
            info="Normalized utterances from ABM Results → Utterances",
            required=True,
        ),
        StrInput(
            name="voice_bank_path",
            display_name="Voice Bank Path",
            info="JSON file with voice definitions and optional speaker assignments",
            value="data/casting/voice_bank.json",
            required=False,
        ),
        StrInput(
            name="default_voice_id",
            display_name="Default Voice ID",
            info="Used for unknown/empty speakers if not found in bank",
            value="builtin:narrator_1",
            required=False,
        ),
        BoolInput(
            name="strict_mode",
            display_name="Strict Mode",
            info="If true, unknown speakers raise an error instead of using fallback",
            value=False,
            required=False,
        ),
    ]

    outputs = [
        Output(
            display_name="Enriched Utterances",
            name="enriched_utterances",
            method="assign_voices",
        ),
    ]

    def assign_voices(self) -> Data:
        # Deprecated: return an informative payload instead of performing work.
        msg = "ABMCastingDirector is deprecated. Please replace this node with ABMSpanCasting (spans-first pipeline)."
        self.status = msg
        return Data(
            data={
                "error": "deprecated_component",
                "message": msg,
                "voice_bank_path": self.voice_bank_path,
            }
        )
