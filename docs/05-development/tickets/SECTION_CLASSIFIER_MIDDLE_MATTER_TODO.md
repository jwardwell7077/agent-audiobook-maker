# TODO: Section Classifier — middle_matter (tail-only)

Status: Deferred until lf_components focus completes Owner: TBD

## Steps

- [ ] Wire config flags (no behavior yet): emit_middle_matter=true, drop_middle_matter_from_chapters=true
- [ ] Implement tail-window finder within chapters
- [ ] Add promo lexicon and link/handle detectors (configurable)
- [ ] Implement deterministic scorer with line-count feature (1–8 lines rewarded)
- [ ] Extract block and shrink chapter when score ≥ 0.70
- [ ] Emit middle_matter.jsonl and update meta counters and prev/next linkage
- [ ] Unit tests: promo present, no separator; lone separator; system bracket near tail; long block penalty; line-count buckets
- [ ] CLI: add switch to include/exclude middle_matter in output
- [ ] Docs: update pipeline README and examples

## Notes

- Keep AI “system” tagging in separate LangFlow preprocessor
- Do not mutate original text; only adjust chapter range when extracting
