# Ticket: Special Character Detection Profile — AI-System

Status: Proposed
Priority: P1-Next
Owner: TBD
Related: SECTION_CLASSIFIER_MIDDLE_MATTER_TICKET.md

## Goal

Define a minimal, deterministic detection profile for AI-system lines and apply it in-place so attribution/casting can voice them as a distinct character when desired.

## P0 Scope (strict and simple)

- Detection rule: Tag a span as ai_system only if the trimmed line matches `^<[^>\n]+>$` (a single angle-bracket block line like `<Skills>`, `<Stamina: 10>`).
- Ignore inline `<...>` inside narration; do not tag those.
- No new files; augment spans in-place: tags includes `ai_system`; optional subtype_tags [`status`, `menu`].
- Attribution: If `ai_system` tag present, set speaker_id to `ai_system`. Otherwise, leave speaker_id unset/unknown (no auto narrator).
- Casting: Deferred — tracked in `AI_SYSTEM_VOICE_CASTING_TODO.md`. No voice wiring in P0.

## Contract (additive fields)

- tags[]: add `ai_system` when detected
- subtype_tags[]: optional [`status`, `menu`]
- ai_system_confidence: 1.0 for matches, otherwise absent
- ai_system_reasons[]: e.g., ["angle_bracket_block"]
- ai_system_block_id: optional for grouping adjacent ai_system lines

## Grouping (optional)

- Assign a shared `ai_system_block_id` to adjacent ai_system lines when separated by ≤1 blank line and total ≤12 lines; keep per-line spans intact.

## Config

- enable_ai_system (default: true)
- system_speaker_id (default: `ai_system`)
- default_speaker_id (default: `unknown`)
- system_voice_id (default: `ai_system_default`) — Deferred use
- unknown_fallback_voice_id (optional, no default) — Deferred use

## Acceptance Criteria

- Only line-alone angle-bracket blocks are tagged; inline `<...>` is ignored.
- Spans are augmented in-place; offsets and ordering unchanged.
- speaker_id is set to `ai_system` only when tagged; otherwise remains unset/unknown.
- Casting uses system voice if configured; unknowns don’t get a voice unless an explicit fallback is configured.
- Deterministic across runs with the same input.

## Test Plan

- Tag `<Skills>`, `<Shop>`, `<0 skill points available>`, `<Stamina: 10>` lines with confidence 1.0 and subtypes [`menu`|`status`].
- Do not tag inline: `switched to the <Skills> tab.`
- Group consecutive bracket lines into one block_id (optional), retaining per-line spans.

## P1+ (not in P0)

- Additional signatures: square brackets `[Quest Updated]`, `System:` prefixes, all-caps short lines, stat blocks, SFX proximity.
- Confidence tuning and merge heuristics.

## Next Steps (proposed)

1) Implement detection in LangFlow preprocessor (regex match + tag injection)
2) Wire attribution rule (speaker_id = ai_system when tag present)
3) Wire casting mapping for `ai_system` voice
4) Add unit tests for detection, attribution, and casting behavior
5) Optional: add config toggles to pipeline CLI/flow
