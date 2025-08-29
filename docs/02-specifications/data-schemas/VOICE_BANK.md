# Voice Bank Specification

Path: `data/casting/voice_bank.json`

## Purpose

Defines character→voice mappings for SSML/TTS. The voice bank provides provider-specific voice info (id/name), defaults (e.g., narrator), and tuning parameters (rate/pitch/volume/style) to ensure consistent voice selection during SSML assembly.

## File structure

Top-level keys:

- `_schema`: Human-readable description of the structure (informational).
- `defaults`: Reusable voice profiles (e.g., narrator baseline).
- `characters`: Character mappings to profiles.

## Voice profile fields

- `voice_id` (string): Provider-specific ID (e.g., Azure voice short name, ElevenLabs voice ID).
- `voice_name` (string): Human-readable reference.
- `provider` (string): One of `azure`, `aws-polly`, `elevenlabs`, `coqui`, `local`.
- `locale` (string): BCP‑47 tag (e.g., `en-US`).
- `rate` (string): Relative speaking rate (e.g., `+0%`, `-10%`, `fast`).
- `pitch` (string): Relative pitch (e.g., `+0st`, `-2st`).
- `volume` (string): Relative volume (e.g., `+0dB`, `soft`).
- `style` (string): Voice style preset, if supported (e.g., `narration`, `conversational`).
- `style_degree` (number): 0..1 intensity for the style (provider-dependent).
- `tags` (array): Free-form labels to aid selection (e.g., `neutral`, `calm`).
- `fallback` (string|null): Alternate `voice_id` to use if the primary is unavailable.

## Characters section

Each entry maps a character to a profile, either by:

- Inline profile
- Reference to a default profile

Example:

```json
{
  "characters": {
    "narrator": { "by_id": "narrator", "profile": "defaults.narrator" },
    "quinn": {
      "by_name": "Quinn",
      "profile": {
        "voice_id": "azure:en-US-GuyNeural",
        "voice_name": "Guy",
        "provider": "azure",
        "locale": "en-US",
        "rate": "+0%",
        "pitch": "+0st",
        "volume": "+0dB",
        "style": "conversational",
        "style_degree": 0.6,
        "tags": ["youthful", "confident"],
        "fallback": null
      }
    }
  }
}
```

Notes:

- Prefer `by_id` when you have a stable `character_id`; otherwise use `by_name`.
- You can keep team-wide baselines in `defaults` and reference them via `"profile": "defaults.<key>"`.

## How it’s used (planned)

The planned component `ABMVoiceResolver` will:

1. For each utterance, try `character_id` → `characters[<id>]`.
2. If missing, try normalized `character_name` → `characters[<lowername>]` (project convention).
3. If still missing, fall back to `defaults.narrator`.
4. Attach `voice.*` fields to the utterance payload for SSML assembly.

## Provider considerations

- Azure: `voice_id` can be the ShortName (e.g., `en-US-GuyNeural`), `style`/`style_degree` supported on select voices.
- AWS Polly: styles limited; use `rate/pitch/volume` via SSML `<prosody>`.
- ElevenLabs/Coqui: primarily `voice_id`; `rate/pitch/volume` may be approximated or ignored—keep values but expect backend mapping.

## Conventions and validation

- Keep `locale` consistent with the text language; default to `en-US` if unspecified.
- Use relative `rate/pitch/volume` where possible; assembler will translate to provider-specific SSML/parameters.
- Add tags to help future automatic selection (e.g., by emotion or narrative role).

## How to add a new character voice

1. Choose a `character_id` (preferred) or confirm canonical `character_name`.
2. Add an entry under `characters` with either an inline `profile` or a reference to a `defaults` profile.
3. Ensure `locale` and `provider` align with your TTS backend.

## Relation to SSML assembly

- Resolver attaches `voice.*` to utterances.
- SSML assembler will generate `<voice>` (or provider equivalent) and `<prosody>` using `rate/pitch/volume/style`.
- If fields are absent, assembler falls back gracefully to the narrator default.

---
See also: `SSML_DATA_REQUIREMENTS.md` for the full checklist and pipeline placement.
