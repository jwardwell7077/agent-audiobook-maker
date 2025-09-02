# TODO: AI-System Voice Casting (Deferred)

Status: Deferred
Owner: TBD
Depends on: SPECIAL_CHARACTER_DETECTION_PROFILE_AI_SYSTEM.md (tags in-place)

Scope

- Map speaker_id `ai_system` to a concrete voice in `data/casting/voice_bank.json`.
- Add optional `unknown_fallback_voice_id` casting behavior.
- Do not change detection or attribution rules.

Steps

- [ ] Add `ai_system` voice entry to voice_bank.json (e.g., voice_id `ai_system_default`)
- [ ] Casting: if `speaker_id == ai_system` → pick configured voice; if missing → log warning
- [ ] Optional: implement `unknown_fallback_voice_id` for `speaker_id == unknown`
- [ ] Tests: ensure only ai_system gets mapped; unknown doesn’t unless fallback configured

Out of scope

- Detection rules and span tagging (handled by Special Character Detection Profile)
- Section classifier features
