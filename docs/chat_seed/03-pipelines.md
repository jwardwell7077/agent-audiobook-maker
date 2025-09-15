# Pipelines

Use the Parler-TTS engine by preferring it on the command line. Provide a
seed for deterministic synthesis:

```
... --prefer-engine parler --parler-model parler-tts/parler-tts-mini-v1 --parler-seed 1234
```

Voice board quick script (renders all catalog voices to `tmp/voiceboard`):

```python
import soundfile as sf, yaml
from pathlib import Path
from abm.voice.engines import ParlerEngine

cat = yaml.safe_load(Path("data/voices/parler_catalog.yaml").read_text())
engine = ParlerEngine()
for name, meta in cat["voices"].items():
    y = engine.synthesize_to_array(
        "The quick brown fox...",
        name,
        description=meta["description"],
    )
    sf.write(Path("tmp/voiceboard")/f"{name}.wav", y, 48000)
```
