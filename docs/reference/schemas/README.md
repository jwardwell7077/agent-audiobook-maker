# Reference schemas

Core artifacts and their roles in the pipeline:

- Chapter (JSON): structured representation of a single chapter’s annotated spans used by planning and rendering.
- Segment (JSON): the atomic unit of synthesis; contains text, role (narration/dialog/thought), timing hints, and engine/voice fields when planned.
- Casting plan (JSON): per-chapter synthesis plan produced by planning tools; lists segments in order with synthesis parameters and expected pauses/crossfades.
- Book config (JSON): metadata for packaging (album/title/artist), output formats, and optional chapter titling.

Schema maturity
- These definitions are stabilized through usage in the codebase and tests. As we evolve the pipeline, we’ll formalize JSON Schema files under version control and validate artifacts in CI.
