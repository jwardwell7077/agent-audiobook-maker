Public Sample Content (TODO)
---------------------------------

We intentionally do NOT include any real-book content in this repository history.

Goal: Add a small, truly public-domain sample book and derived artifacts to support demos/tests without legal risk.

Acceptance criteria:
- Source text is public-domain (e.g., Project Gutenberg) or authored by us under a permissive license.
- Include only minimal files needed for tests/examples (keep small, <5MB total).
- Avoid binary/media where possible; if audio is needed, generate short clips only.
- Ensure .gitignore and pre-commit guards allowlist only this sample path.

Proposed path layout (subject to change):
- data/books/PUBLIC_SAMPLE/
  - source_pdfs/ (if needed, keep tiny or provide a link-only reference)
  - source_text/
  - README.md (cite source, license)
- data/clean/PUBLIC_SAMPLE/
- data/annotations/PUBLIC_SAMPLE/
- data/renders/PUBLIC_SAMPLE/ (optional)
- data/stems/PUBLIC_SAMPLE/ (optional)

Next steps:
1) Select/confirm a public-domain text and license info.
2) Add a single-page or very short sample and minimal derived artifacts.
3) Update .gitignore and pre-commit allowlist to include only PUBLIC_SAMPLE.
4) Add a quick example in README/docs referencing the sample, not external IP.
