# SSML data requirements checklist

This checklist ensures we have all the data needed to assemble effective SSML for TTS. It maps each requirement to where it exists today (Done), is partially present (Planned), or is missing (Gap), with the producing component and field names.

## Legend

- Done = implemented and emitted in current pipeline
- Planned = design/docs exist and fields are easy to add; component scheduled
- Gap = not planned; needs decision

## Core text and structure

- [x] Utterance text (plain) — Done
  - Source: ABMSpanIterator/Spans → `text_norm` (dialogue/narration); Aggregator/Normalizer → `text`, `full_text`
- [x] Dialogue vs narration role — Done
  - Source: ABMDialogueClassifier → `classification`; Aggregator → `classification`
- [x] Ordering/IDs for deterministic assembly — Done
  - Source: BlockIterator → `book_id`, `chapter_id`, `utterance_idx`
- [ ] Sentence/phrase segmentation for intra-utterance breaks — Planned
  - Component: ABMProsodyGenerator (planned) → `segments[]` with suggested `break` lengths

## Speaker and voice mapping

- [x] Speaker name/id + confidence — Done
  - Source: ABMSpeakerAttribution → `character_name`, `character_id`, confidence; Aggregator normalizes and sets narrator fallback
- [x] Voice registry (character→voice mapping) — Planned (data file scaffold added)
  - File: `data/casting/voice_bank.json` (schema + sample narrator)
  - Fields: `voice_id|voice_name`, `provider`, `locale`, `rate`, `pitch`, `volume`, `style`, `style_degree`
- [ ] Resolved voice selection on each utterance — Planned
  - Component: ABMVoiceResolver (future) → enrich utterances with `voice.*` from voice bank and character profiles

## Prosody and expressiveness

- [ ] Emotion label + intensity — Planned
  - Component: ABMEmotionClassifier (planned) → `emotion`, `emotion_confidence`
- [ ] Prosody hints (rate/pitch/volume deltas) — Planned
  - Component: ABMProsodyGenerator (planned) → `prosody.{rate,pitch,volume}`
- [ ] Emphasis/whisper/say-as/phoneme exceptions — Planned
  - Component: ABMSSMLAssembler (planned) → token-level hints: `emphasis`, `say_as`, `phonemes`

## Language and formatting

- [ ] Language/locale per utterance — Planned
  - Source: voice bank default `default_locale` with override per character/utterance
- [ ] SSML-safe sanitization/escaping — Planned
  - Utility: SSML sanitizer (future) → `text_ssml_safe`
- [ ] Numbers, dates, acronyms normalization — Planned
  - Utility: Text normalizer (future) → `normalization.applied_rules[]`

## Assembly and output

- [ ] SSML assembly component — Planned
  - Component: ABMSSMLAssembler → outputs `<speak>...</speak>` per utterance/chapter; writes `.ssml` alongside JSONL
- [x] JSONL artifact for utterances — Done
  - Component: ABMAggregatedJsonlWriter → `output/utterances.jsonl` + meta

## Minimal field contract for SSML readiness (current vs. target)

Current minimal contract we already emit per utterance:

- id: `book_id`, `chapter_id`, `utterance_idx`
- text: `text` (with `full_text` fallback)
- role: `classification` (dialogue/narration)
- speaker: `character_name`, `character_id`, `attribution_confidence`
- context: `context_before`, `context_after`

Target additions for high-quality SSML (to be added by planned components):

- voice: `voice_id|voice_name`, `locale` (from voice bank/resolver)
- emotion: `emotion`, `emotion_confidence`
- prosody: `prosody.rate`, `prosody.pitch`, `prosody.volume`
- breaks: `segments[].break_ms` or inline break hints
- formatting: `text_ssml_safe`, normalization metadata

## Next steps

1. Implement ABMVoiceResolver to attach `voice.*` per utterance using `voice_bank.json` and narrator default.
1. Implement ABMEmotionClassifier to add `emotion` labels (optional for v1 SSML).
1. Implement ABMProsodyGenerator to create `segments` and prosody deltas.
1. Implement ABMSSMLAssembler to produce SSML strings/files with proper escaping.
1. Add `locale` default (e.g., `en-US`) to env/config and propagate to utterances if not set by voice.

This plan keeps current outputs stable and adds SSML fields as non-breaking, optional enrichments.
