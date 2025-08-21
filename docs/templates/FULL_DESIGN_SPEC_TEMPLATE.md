# COMPONENT_NAME — Full Design Spec

Status: Draft
Owner: OWNER
Last updated: YYYY-MM-DD

## Overview

- Purpose and scope
- Assumptions and constraints

## Diagrams

- Architecture (Mermaid)
- UML (class or sequence)
- Data diagram (ERD/class) if applicable
- FSM (if applicable)

## Contracts

- Inputs (types, shapes, file paths)
- Outputs (types, shapes, file paths)
- Invariants and guarantees
- Error modes and edge cases

## Requirements

1. <Requirement 1>
2. <Requirement 2>

Quality requirements (keep these by default):

1. R-STYLE: Code is 100% lint compliant (formatter + linter) with zero errors/warnings.
	- Passes: ruff format, ruff check (no disables beyond justified file-local comments).
2. R-DOCS: 100% Google-style docstrings for all public modules/classes/functions.
	- Measured by a docstring coverage tool (e.g., interrogate) at 100% for the component.
3. R-COVERAGE: 100% unit test coverage (statements/branches) for this component’s code path.
	- Measured via pytest-cov; define the package/path under test in this spec.

## Task Plan

- [ ] Step 1
- [ ] Step 2

## Test Plan (pytest)

- Map tests 1:1 to Requirements (happy path + at least one edge case)
- Fixture/data strategy
- Coverage: enforce 100% for the component path (pytest-cov), and validate docstring coverage at 100%.

## Out of Scope

- Deferred items

## Open Questions

- TBD
