# Ingestion v2 Documentation Integration Checklist

This checklist helps integrate the updated ingestion pipeline docs into the project documentation on a separate branch.

## Files to add

- Add/keep: `docs/INGESTION_PIPELINE_V2.md` (this is the primary reference)

## Docs index updates

- Update `docs/README.md` (or the top-level `README.md`) to reference the new ingestion v2 document.
- If there are older ingestion specs (e.g., `PDF_TO_TEXT_SPEC.md`, `TXT_TO_JSON_SPEC.md`), add deprecation notes and links to v2.

## CLI references

- Replace old examples of `--mode both|dev` with `--mode dev|prod`.
- Note that `--emit-jsonl` is deprecated and behavior is controlled by `--mode`.
- Call out that prod mode writes no artifacts and relies on a DB insert stub for now.

## Behavior notes

- Emphasize that dev:
  - writes raw, well_done.txt, ingest meta, JSONL + JSONL meta
  - also triggers a DB insert stub
- Emphasize that prod:
  - writes no artifacts
  - triggers a DB insert stub using in-memory data

## Future-proofing

- Leave a TODO reference to replace the stub with a real Postgres insertion service when DB is ready.
- Consider a follow-up doc section describing JSONL schema expectations for downstream consumers.

## Optional enhancements

- Add a short “troubleshooting” section for common ingestion issues.
- Expose advanced well-done options (e.g., `split_headings`) via CLI flags and update docs accordingly when implemented.

---

After updating indices and cross-links, run a quick local smoke test and ensure paths and command examples match the current repository layout.
