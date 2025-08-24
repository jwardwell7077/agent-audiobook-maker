# Annotation Schema

Last updated: 2025-08-14

## Versioning Strategy

- Each enrichment pass produces a new schema *layer*; file versions encoded in filename suffix or header metadata.
- Hashing excludes volatile rationale text to preserve determinism for core fields.

## Prototype (v1 – Segmentation Only)

```jsonc
{
  "book_id": "SAMPLE_BOOK",
  "chapter_id": "SAMPLE_BOOK_CH0001",
  "utterance_idx": 0,
  "text": "Dialogue example...",
  "is_dialogue": true
}
```text

## Planned Enriched (v2 – Speaker / Emotion / QA)

```jsonc
{
  "book_id": "SAMPLE_BOOK",
  "chapter_id": "SAMPLE_BOOK_CH0001",
  "utterance_idx": 0,
  "text": "Dialogue example...",
  "start_char": 123,
  "end_char": 156,
  "is_dialogue": true,
  "speaker": "CHARACTER_NAME",
  "speaker_confidence": 0.93,
  "emotion": "neutral",
  "emotion_confidence": 0.81,
  "qa_flags": [],
  "hashes": { "text_sha256": "..." },
  "layer_versions": { "segmentation": 1, "speaker": 1, "emotion": 1 },
  "created_at": "2025-08-14T12:00:00Z"
}
```text

## Full Target (v4 – Prosody / SSML / TTS)

See `docs/CONTEXT.md` for comprehensive final target record including prosody, ssml, tts_profile_id, audio paths, duration, mastering status.

## Field Definitions

| Field                   | Type             | Layer        | Description                                |
| ----------------------- | ---------------- | ------------ | ------------------------------------------ |
| book_id                 | string           | all          | Book identifier (stable)                   |
| chapter_id              | string           | all          | Chapter identifier (stable)                |
| utterance_idx           | int              | all          | 0-based index within chapter               |
| text                    | string           | segmentation | Raw utterance text                         |
| is_dialogue             | bool             | segmentation | Heuristic dialogue detection               |
| start_char / end_char   | int              | segmentation | Character span offsets in chapter text     |
| speaker                 | string           | speaker      | Resolved speaker label or NARRATOR/UNKNOWN |
| speaker_confidence      | float            | speaker      | Confidence 0..1                            |
| emotion                 | string           | emotion      | Discrete emotion label                     |
| emotion_confidence      | float            | emotion      | Confidence 0..1                            |
| prosody                 | object           | prosody      | Pitch/rate/intensity suggestions           |
| qa_flags                | list[string]     | qa           | Automated quality issue flags              |
| ssml                    | string           | ssml         | Renderable SSML snippet                    |
| tts_profile_id          | string           | tts          | Voice profile mapping id                   |
| audio_stem_path         | string           | tts          | Path to rendered stem wav                  |
| duration_s              | float            | tts          | Stem duration seconds                      |
| hashes                  | object           | all          | Hashes (text + params) for caching         |
| layer_versions          | object           | all          | Version map per enrichment layer           |
| created_at / updated_at | string (ISO8601) | all          | Timestamps                                 |

## Hashing Guidance

| Hash Name         | Inputs                                             |
| ----------------- | -------------------------------------------------- |
| text_sha256       | Raw utterance text                                 |
| segmentation_hash | chapter.text_sha256 + segmentation params          |
| speaker_hash      | segmentation_hash + speaker params + model version |
| emotion_hash      | speaker_hash + emotion model version               |
| prosody_hash      | emotion_hash + prosody rules version               |
| ssml_hash         | prosody_hash + ssml template version               |

## Change Control

1. Propose field addition in PR description.
1. Update this doc and bump layer version (e.g., speaker:1→2).
1. Add migration or backfill logic if downstream expects presence.
1. Extend tests: serialization + hashing invariants.

## Excluding Fields From Deterministic Hash

- Rationale / LLM explanation text
- Transient performance metrics (latency_ms)

Keep deterministic subset small and stable; treat non-deterministic as optional enrichments.
