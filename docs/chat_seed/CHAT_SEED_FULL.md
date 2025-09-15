# Chat SME Seed (MIN)

## Primer
Agent-Audiobook-Maker turns PDFs into chapterized JSON and multi-voice audio locally (Piper/XTTS). Staged pipeline ensures debuggable artifacts and reproducibility.

## Pipeline (Mermaid)
flowchart TD
  A[PDF]-->B[pdf_to_raw_text]; B-->C[raw_to_welldone]; C-->D[welldone_to_json]; D-->E[classifier_cli]; E-->F[voicecasting]; F-->G[render_chapter]; G-->H[album_norm]; H-->I[package_book]

## Modules (top 10)
- **abm.annotate** — see seed_pack/modules/abm.annotate.json
- **abm.audio** — see seed_pack/modules/abm.audio.json
- **abm.audit** — see seed_pack/modules/abm.audit.json
- **abm.classifier** — see seed_pack/modules/abm.classifier.json
- **abm.ingestion** — see seed_pack/modules/abm.ingestion.json
- **abm.llm** — see seed_pack/modules/abm.llm.json
- **abm.parse** — see seed_pack/modules/abm.parse.json
- **abm.profiles** — see seed_pack/modules/abm.profiles.json
- **abm.sidecar** — see seed_pack/modules/abm.sidecar.json
- **abm.voice** — see seed_pack/modules/abm.voice.json

## CLIs (sample)
- `python -m abm.annotate.annotate_cli`
- `python -m abm.annotate.bnlp_refine`
- `python -m abm.annotate.llm_prep_cli`
- `python -m abm.annotate.llm_refine`
- `python -m abm.audio.render_book`
- `python -m abm.audio.render_chapter`
- `python -m abm.audio.synthesis_export`
- `python -m abm.audit.__main__`