# Classifier: Prologue/Epilogue Handling (Reverted API)

Context:

- After reverting classifier to commit fa99ab7, unit test asserting Prologue/Epilogue support fails.
- Current reverted regex requires TOC items with an ordinal or dotted leaders; bare Prologue/Epilogue handling may differ from newer logic.

Observed:

- test_section_classifier_block::test_prologue_and_epilogue_supported was skipped.
- The reverted classifier matches Prologue/Epilogue headings in body but TOC parsing may require titles or dotted leaders.

Next Steps:

- Decide intended contract for Prologue/Epilogue in TOC:
  - Accept bare "Prologue" / "Epilogue" as TOC items? Or require titles / dotted leaders?
- If accepting bare entries, relax TOC regex to include ordinal-less entries within TOC window.
- Add coverage: positive and negative cases for Prologue/Epilogue in TOC and body.

References:

- src/abm/classifier/section_classifier.py (fa99ab7-style)
- tests/unit_tests/test_section_classifier_block.py

Owner: TBD Priority: Medium Status: Open (test skipped)
