# Ticket: Section Classifier — Add "middle_matter" extraction (author/promo notes at chapter tails)

Status: Deferred (scope creep)

Priority: P2 (after current lf_components work)

Owner: TBD

Related: CLASSIFIER_PROLOGUE_EPILOGUE_TODO.md

Focus now: lf_components (do not implement yet)

## Summary

Introduce a new section_kind "middle_matter" in the upstream Section Classifier that extracts author/promo interstitials located only at chapter tails (end of a chapter before the next chapter header, or EOF). These blocks contain lines like "Remember to vote for…", "4600 Stones = …", Patreon/Discord/Instagram links, etc. Extract them deterministically into a separate artifact and trim them from the chapter span.

AI “system” tagging is out of scope for this ticket (handled by a separate preprocessor in LangFlow).

## Motivation (corpus examples)

- "For MVS artwork and updates follow on Instagram and Facebook: jksmanga"
- "My werewolf system Exclusive on P.a.t.r.e.o.n … (2 Chapters per month)"
- "Remember to vote … mass release … 4600 Stones … 4800 Stones …"
- Lone separators (\*\*\*, \*\*\*\*\*) must not be classified as middle_matter unless promo lines are present.

## Scope

- Add section_kind: middle_matter (tail-only within chapters)
- Detect/Extract author_note and promo-style lines at chapter tails; never at chapter start or mid-chapter
- Deterministic segmentation: stable IDs/offsets; original text is not mutated except for carving out the extracted tail window from the chapter’s range
- Emit middle_matter.jsonl alongside existing sections artifacts; update meta counts and coverage

## Out of scope

- AI “system” line tagging or transformation (separate preprocessor in LangFlow)
- Dialogue attribution/casting/style planning

## Inputs/Outputs (design)

- Input: normalized text per book (doc_id, text)
- Outputs (JSONL): toc.jsonl, front_matter.jsonl, chapters.jsonl, middle_matter.jsonl, back_matter.jsonl
- Section record fields: id, doc_id, section_kind, subtype_tags\[\], text, start_char, end_char, start_line, end_line, detection\[\], confidence, prev_section_id, next_section_id, order
- ID scheme: deterministic (e.g., `doc_id:start-end` or sha1(doc_id+start+end))

## Detection and extraction (tail-only)

1. Find hard chapter boundaries by headers (e.g., `^Chapter\\s+(?:\\d+|[IVXLC]+)\\b[:\\s].*`) and separators (`^\\s*([*\\-_])\\1{2,}\\s*$`).
1. For each chapter, define tail window: from the last narrative paragraph (>=120 chars or ends with .?! and not link-heavy) to chapter end (trim trailing blanks).
1. Candidate middle_matter block = smallest contiguous region in the tail window containing at least one promo/author-note signal; may include 0–2 blank lines and an adjacent separator line.
1. Extract candidate block as section_kind=middle_matter and shrink chapter end accordingly, if confidence ≥ threshold.

Required promo/author-note signals (case-insensitive):

- Phrases: remember to vote, mass release, stones, release schedule, two chapters today, rate/review, support me, donation/paypal, subscribe
- Platforms/links: patreon (incl. p.a.t.r.e.o.n), discord, instagram, facebook, twitter|x, webtoon, http(s)://, @handle
- Series-specific: "For MVS artwork and updates follow…"

Non-examples (stay in chapter):

- Scene breaks/separators alone (\*\*\*, -----, \_\_\_)
- In-universe system notices (e.g., "\[New quest received\]")

## Confidence scoring (deterministic)

Signals and weights (tunable defaults):

- promo lexicon present (required): +0.40
- tail position (inside tail window): +0.20
- separator adjacency (\*\*\* or similar immediately before): +0.10
- links/handles in lines: +0.05 each, capped at +0.20
- numeric CTAs ("4600 Stones", "2 extra Chapters"): +0.05 each, capped at +0.15
- line-count feature (non-blank lines in block):
  - 1–8 lines: +0.25
  - 9–12 lines: +0.10
  - 13–20 lines: +0.00
  - > 20 lines: −0.20
  - 0 lines: −0.50 (guard)
- short_line_ratio (≤120 chars): ≥0.75 → +0.10; 0.5–0.75 → +0.05

Threshold: classify as middle_matter if score ≥ 0.70. On ties with chapter, prefer chapter unless promo lexicon + tail position + line_count_score ≥ +0.10.

Config knobs:

- emit_middle_matter (default: true)
- drop_middle_matter_from_chapters (default: true)
- promo_keywords (override list)
- short_line_len (default: 120)
- allow_blank_lines_inside (default: 2)

## Acceptance criteria

- Only tail blocks with promo/author-note evidence become middle_matter; lone separators do not
- Extracted middle_matter does not overlap with chapters; coverage accounts for carved ranges
- middle_matter tagged with subtype(s): author_note; plus promo and/or release_note when appropriate
- Deterministic IDs and prev/next linkage preserved across artifacts
- Meta includes: chapters_total, chapters_with_middle_matter, middle_matter_count, avg_block_line_count, distribution buckets

## Test plan (unit)

- Between-chapters promo: Chapter N, tail promo lines (e.g., vote + stones), Chapter N+1 header → 1 middle_matter section; Chapter N end reduced; no overlaps
- Tail promo without separators → still extracted via lexicon/links
- Lone separator at tail → not extracted
- In-universe system bracket near tail → remains in chapter
- Line-count scoring: 1–8 lines → high confidence; >12 lines reduced; >20 lines penalized

## Impact

- Cleaner chapters for downstream spans pipeline; author/promo notes isolated
- Optional routing: drop, narrate separately, or audit

## Risks/Considerations

- Over-aggressive extraction on short narrative tails — mitigated by required lexicon
- Corpus variance in phrasing — mitigate with configurable keyword list

## Dependencies

- Files to touch when implemented: `src/abm/classifier/section_classifier.py`, `src/abm/classifier/classifier_cli.py`, tests under `tests/unit_tests/`
- Coordination: None immediately; out-of-scope AI “system” preprocessor lives in LangFlow

## Decision

Defer implementation. Capture design and acceptance now; resume after current lf_components priorities.
