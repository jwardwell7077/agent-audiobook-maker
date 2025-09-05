# LangFlow — How to View the Redesign

- Start the server: `scripts/run_langflow.sh` (loads custom components from `src/abm/lf_components`).
- Open <http://127.0.0.1:7860>
- Import `examples/langflow/abm_spans_first_pipeline.v15.json`.
- Ensure data: `data/clean/<book>/classified/chapters.json` exists (e.g., mvs sample).
- Use ABMChapterLoader to point at the chapters and run the pipeline.
