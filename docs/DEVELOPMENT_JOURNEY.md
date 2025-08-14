# Development Journey: Audio Book Maker MVP

This document chronicles the path from a bare template to a deterministic single‑book ingestion MVP, capturing milestones, decisions, trade‑offs, and periodic assessments. It complements `LESSONS_LEARNED.md` (tactical insights) by providing a higher‑level narrative and milestone framing.

## Vision (Initial)

Provide a reliable pipeline to ingest a long‑form novel PDF, parse a structured Table of Contents (TOC), split into chapters, persist artifacts, and enable deterministic chapter text hashing as a foundation for downstream audio rendering and enrichment.

Constraints:

- Focus on one canonical book (`SAMPLE_BOOK`).
- Optimize for correctness & determinism over feature breadth.
- Avoid premature generalization (multi‑book UX, scaling, distributed storage).

Success Criteria (MVP):

1. Structured TOC parser extracts ≥ expected chapter count with intro detection.
2. Per‑chapter JSON artifacts + volume manifest written deterministically.
3. Repeated purge + re‑ingest cycles produce identical SHA‑256 chapter hashes.
4. Failures (missing structured TOC) degrade safely (0 chapters + warnings) without fallback heuristics adding nondeterminism.
5. Regression test suite encodes and guards the canonical snapshot.

## Timeline of Key Milestones

| Date | Milestone | Summary / Impact |
|------|-----------|------------------|
| 2025-08-12 | Template bootstrap | Base LangGraph/FastAPI template cloned; initial API skeleton retained template wording. |
| 2025-08-13 | High‑fidelity extraction | Switched from PyPDF to PyMuPDF word-level extraction to recover lost spacing; improved TOC match reliability, enabling structured parsing. |
| 2025-08-13 | Structured TOC consolidation | Removed legacy fallback parsers (heading/simple/advanced); enforced single structured strategy with confidence thresholds & dedup. |
| 2025-08-13 | Post-processing pass | Added hyphen join heuristic + optional camel splitting env flag; improved readability & hash stability. |
| 2025-08-13 | Purge endpoint v1 | Implemented file + DB purge with dry-run; foundation for re‑ingest regression. |
| 2025-08-13 | Canonical ingest snapshot | First chapter hash snapshot captured; initial deterministic baseline attempt. |
| 2025-08-14 | Determinism regression surfaced | Hash mismatch between consecutive cycles (chapter 00020 then 00021) revealed floating point jitter in line grouping. |
| 2025-08-14 | Deterministic extraction fix | Introduced stable word ordering (rounded y + original index) & y‑quantization grouping; added targeted blood type spacing repair. |
| 2025-08-14 | Snapshot refresh & validation | Recomputed all chapter hashes after determinism fix; multi-cycle equality confirmed; regression test enhanced with diff previews. |
| 2025-08-14 | Documentation pass | Added Snapshot Hash Freeze rationale, Lessons Learned expansion, repo hygiene updates (.gitignore). |
| 2025-08-14 | MVP assessment | Formal evaluation of scope completion, gaps (docs, ignored fixtures), and prioritized action list. |

## Evolving Goals & Trade‑Offs

| Goal Evolution | Decision | Rationale |
|-----------------|----------|-----------|
| Multi‑strategy parsing → Single structured parser | Removed fallbacks | Reduced nondeterministic drift & complexity; easier to reason about failures. |
| Arbitrary multi‑book support | Deferred (basic discovery only) | Avoids premature indexing & pagination concerns; keeps snapshot narrative focused. |
| Full text diff storage for regression | Chose hash + preview | Hashes are compact & stable; preview only emitted on mismatch to reduce repo weight. |
| Generic spacing fixes | Targeted pattern (blood type) | Avoid over‑general splits that might alter semantics; minimal surgical change increases confidence. |
| Immediate CI artifact storage | Deferred | Avoid complexity; local deterministic hashing suffices pre‑scaling. |

## Architecture Snapshot (MVP)

- Extraction Layer: PyMuPDF prioritized; fallback chain present but rarely invoked. Deterministic ordering & line grouping.
- Parser Layer: Structured TOC regex (TOC header + lines + headings) with dedup & intro extraction.
- Post-Processing: Hyphen join, targeted spacing fix, optional camel split, anomaly warnings.
- Persistence: Chapter JSON (id, title, text, hash, meta), volume manifest with structural stats & warnings.
- API Surface: Ingest (single/batch), purge, job-based ingest progress, chapter listing/detail, experimental annotations & TTS rendering.
- Testing: Canonical snapshot (hash stability), structural volume comparison, purge regression, integration endpoints.

## Determinism Strategy

1. Stabilize token ordering (sort by rounded y, then x, then original index).
2. Group lines by quantized y buckets (y quantum = 1.0 point) to negate micro jitter.
3. Normalize lines (rstrip) and join with consistent page separators (form feed boundary maintained).
4. Apply idempotent post-processing transforms.
5. Snapshot chapter hashes after confirming stability across two independent ingest cycles.

## Assessments

### MVP Completion Audit (2025-08-14)

- Core ingest pipeline stable & deterministic.
- Regression guardrails operational (purge → re‑ingest equality test).
- Structured parser performance acceptable for target book; risk of failure on unstructured PDFs intentionally accepted.
- Primary gap: Snapshot + canonical fixture risk due to `.gitignore` excluding required test data. Needs immediate remediation before tagging MVP.
- Secondary gaps: README still template-biased; environment flags undocumented; multi-PDF & experimental endpoints not contextualized.

### Risk Register (Active)

| Risk | Impact | Mitigation Status |
|------|--------|-------------------|
| Ignored snapshot fixture | Undetected regressions | Add .gitignore negation & recommit (P0). |
| Undocumented env vars | Misconfiguration / hidden behavior | Add README table (P1). |
| Overgrown `api/app.py` | Future maintainability | Plan modularization post-MVP (P3). |
| Duplicate blood type logic | Subtle double-normalization | Consolidate transform (P2). |
| Multi-PDF metadata counting bug (suspected) | Inaccurate analytics | Verify/fix & add test (P2). |

## Prioritized Action Backlog (from MVP Assessment)

P0: Snapshot fixture tracking fix (.gitignore negation) + recommit.

P1: README overhaul (purpose, architecture, endpoints, env vars, purge & snapshot procedure, fixture setup).

P2: Consolidate spacing fix; add post‑processing unit tests; verify multi-PDF metadata; add re‑ingest idempotency test.

P3: API modularization; config dataclass; hash regeneration helper script; optional artifact diff tooling.

## Snapshot Regeneration Protocol (Canonical Book)

1. Purge artifacts + DB (POST /purge delete_files=true delete_db=true).
2. Ingest canonical PDF twice; assert all chapter hashes identical.
3. Derive new `chapters_sha256.json` (exclude volume JSON) & validate via tests.
4. Update README Snapshot section with date + rationale.
5. Single commit: snapshot + docs + diary note.

## Experimental Features (Present but Not Core MVP)

- Annotations pipeline (`/chapters/{book}/{chapter}/annotations`): segmentation + optional coref/emotion/QA toggles.
- TTS rendering (`/chapters/{book}/{chapter}/render`): synthesizes stems & aggregates audio; currently baseline/no quality policy.
- Background job ingestion with progress metrics.

These remain undocumented in main README until stabilized; either promote post‑MVP or mark clearly as experimental.

## Lessons Applied Early

- Determinism must precede snapshotting; retrofitting determinism invalidates prior hashes and burdens version history.
- Surgical normalization beats broad heuristics for early pipelines (reduces unintended text mutation vectors).
- Storing *hashes + structured metrics* sufficed for early integrity checks; full text storage can be deferred until diff needs outweigh repo size concerns.

## Looking Ahead

Short term: Close P0/P1 gaps and tag MVP.

Mid term: Expand to multi-book ingestion with selective hash snapshotting and diff tooling.

Long term: Introduce scalable storage (object store), advanced parsing fallback, and quality metrics for ingestion confidence scoring.

---
Last updated: 2025-08-14
