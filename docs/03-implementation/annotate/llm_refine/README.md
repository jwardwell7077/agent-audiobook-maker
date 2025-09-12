# Stage B – LLM Refinement

> Resolve low-confidence dialogue/thought spans by querying a local or
> remote LLM and updating annotations deterministically.

The refinement module operates after Stage A heuristic attribution. It
selects spans that remain `Unknown` or below a confidence threshold,
asks an OpenAI-compatible endpoint for roster-constrained attribution,
then persists improvements to a new `combined_refined.json` along with a
Markdown summary.

![](../../../04-diagrams/architecture/stage_b_llm_refinement.mmd)

## Workflow

1. **Candidate extraction** – `LLMCandidatePreparer` walks the Stage A
   JSON and collects spans needing help.
2. **Cache lookup** – `LLMCache` checks a SQLite store for prior
   decisions using a hashed prompt key.
3. **LLM query** – `OpenAICompatClient` sends system/user prompts to the
   configured endpoint. Multiple votes are gathered to pick the highest
   confidence answer.
4. **Apply & review** – Improved spans are written back to the document.
   An optional `review_refined.md` summarises remaining `Unknown`
   counts.

## Usage

```bash
PYTHONPATH=src python -m abm.annotate.llm_refine \
  --tagged data/annotations/book/combined.json \
  --out-json data/annotations/book/combined_refined.json \
  --out-md data/annotations/book/review_refined.md \
  --endpoint http://127.0.0.1:11434/v1 \
  --model llama3.1:8b-instruct-q6_K \
  --manage-llm \
  --votes 3 \
  --skip-threshold 0.90
```

See [OPTIONS.md](OPTIONS.md) for a full argument list.

## Related Diagrams

- C4 Context: [../../../../diagrams/stage_b_llm_refine_c4_context.mmd](../../../../diagrams/stage_b_llm_refine_c4_context.mmd)
- C4 Container: [../../../../diagrams/stage_b_llm_refine_c4_container.mmd](../../../../diagrams/stage_b_llm_refine_c4_container.mmd)

---

*Part of [Annotation Pipeline Modules](../README.md)*
