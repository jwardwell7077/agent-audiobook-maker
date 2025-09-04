.PHONY: all format lint test tests test_watch integration_tests docker_tests help extended_tests

# Default target executed when no arguments are given to make.
all: help

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/
COMP_PATH ?= src

VENV_GUARD:=scripts/require_venv.sh

test:
	@$(VENV_GUARD)
	python -m pytest $(TEST_FILE)

integration_tests:
	@$(VENV_GUARD)
	python -m pytest tests/integration_tests

test_watch:
	@$(VENV_GUARD)
	python -m ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	@$(VENV_GUARD)
	python -m pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	@$(VENV_GUARD)
	python -m pytest --only-extended $(TEST_FILE)

# Quality gate: lint, docstrings, coverage
.PHONY: quality_gate
quality_gate:
	@$(VENV_GUARD)
	ruff format --check .
	ruff check .
	interrogate -v -f 100 -M src || (echo "Docstring coverage <100%" && exit 1)
	pytest -q --cov=$(COMP_PATH) --cov-branch --cov-fail-under=100

# Ensure no legacy 'src.' import prefixes remain
check_no_src_imports:
	./scripts/check_no_src_imports.sh

# CI-friendly test target forcing sqlite DB
test_ci:
	$(ACTIVATE) DATABASE_URL=sqlite:///./ci.db pytest -q


######################
# LINTING AND FORMATTING
######################

# Define a variable for Python and notebook files.
PYTHON_FILES=src/
MYPY_CACHE=.mypy_cache
lint format: PYTHON_FILES=.
lint_diff format_diff: PYTHON_FILES=$(shell git diff --name-only --diff-filter=d main | grep -E '\.py$$|\.ipynb$$')
lint_package: PYTHON_FILES=src
lint_tests: PYTHON_FILES=tests
lint_tests: MYPY_CACHE=.mypy_cache_test

lint lint_diff lint_package lint_tests:
	@$(VENV_GUARD)
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff format $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff check --fix $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m mypy --strict $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && python -m mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff:
	@$(VENV_GUARD)
	ruff format $(PYTHON_FILES)
	ruff check --select I --fix $(PYTHON_FILES)

spell_check:
	codespell --toml pyproject.toml

spell_fix:
	codespell --toml pyproject.toml -w

######################
# DATA SCAFFOLD
######################

DATA_DIRS=data/clean data/annotations data/ssml data/stems data/renders data/mlruns logs models

init_dirs:
	mkdir -p $(DATA_DIRS)

######################
# INGESTION DEMO
######################

# Example: make ingest BOOK=demo FILE=docs/CONTEXT.md
BOOK?=demo
FILE?=README.md

ingest: init_dirs
	python -m src.pipeline.ingestion.cli $(BOOK) $(FILE) data

pdf_to_text:
	@$(VENV_GUARD)
	# Deprecated: use ingest_pdf instead
	python -m abm.ingestion.ingest_pdf --help

######################
# DATABASE / ALEMBIC
######################

alembic_init:
	alembic init alembic

alembic_revision:
	alembic revision --autogenerate -m "auto"

alembic_upgrade:
	alembic upgrade head

######################
# VIRTUAL ENVIRONMENT
######################

PYTHON?=python3.11
VENV_DIR?=.venv
ACTIVATE=. $(VENV_DIR)/bin/activate;

venv:
	@echo "Creating venv in $(VENV_DIR) with interpreter $(PYTHON)";
	$(PYTHON) -m venv $(VENV_DIR)
	$(ACTIVATE) pip install --upgrade pip
	@echo "Run: source $(VENV_DIR)/bin/activate";

install: venv
	$(ACTIVATE) pip install -e .

install_dev: venv
	$(ACTIVATE) pip install -e .[dev]

install_pdf: venv
	$(ACTIVATE) pip install -e .[dev,pdf]

# Convenience target that ensures venv exists then runs full test suite
test_all: install_dev
	$(ACTIVATE) pytest -q

# Run API locally using uvicorn with reload
run_api:
	@$(VENV_GUARD)
	$(ACTIVATE) uvicorn api.app:app --reload --port 8000

######################
# DEV PIPELINE SHORTCUTS
######################

.PHONY: dev_mvs_txt dev_mvs_classify dev_mvs_chapterize dev_mvs_all test_quick test_all_optional

# Produce cleaned text from the local mvs PDF (dev only). Creates mvs.txt and mvs_nopp.txt.
dev_mvs_txt:
	@$(VENV_GUARD)
	$(ACTIVATE) python -m abm.ingestion.ingest_pdf \
		data/books/mvs/source_pdfs/MyVampireSystem_CH0001_0700.pdf \
		--out-dir data/clean/mvs --mode dev

# Run the classifier CLI on local mvs JSONL and write artifacts under data/clean/mvs/classified
dev_mvs_classify:
	@$(VENV_GUARD)
	$(ACTIVATE) python -m abm.classifier.classifier_cli \
		data/clean/mvs/mvs_ch_0001_0700_well_done.jsonl data/clean/mvs/classified

# Run the chapterizer CLI on local mvs text and emit chapters.json and readable variants
dev_mvs_chapterize:
	@echo "Chapterizer removed; see classifier outputs for chapter info."

# One-shot: pdf->text --dev, classifier, chapterizer --dev
dev_mvs_all: dev_mvs_txt dev_mvs_classify

# Fast unit tests only
test_quick:
	@$(VENV_GUARD)
	$(ACTIVATE) pytest -q tests/unit_tests

# All tests including optional ones when env is set
test_all_optional:
	@$(VENV_GUARD)
	ABM_E2E_MVS=$${ABM_E2E_MVS:-0} $(ACTIVATE) pytest -q


######################
# ARTIFACT CLEAN + GENERIC INGEST/CLASSIFY TASKS (no src edits)
######################

.PHONY: clean_artifacts clean_artifacts_apply ingest_pdf classify_well_done ingest_and_classify

# Clean generated artifacts under data/clean/<book>
# Usage: make clean_artifacts BOOK=mvs WHAT=all DRY_RUN=true
BOOK?=mvs
WHAT?=all             # classified | ingest | all
DRY_RUN?=true         # true | false
clean_artifacts:
	bash scripts/clean_artifacts.sh $(BOOK) --what=$(WHAT) --dry-run=$(DRY_RUN)

# Apply cleanup quickly
clean_artifacts_apply:
	bash scripts/clean_artifacts.sh $(BOOK) --what=$(WHAT) --dry-run=false

# Ingest a PDF to raw/well_done + JSONL (wrapper around existing CLI)
# Usage: make ingest_pdf PDF=path/to/book.pdf OUT_DIR=data/clean/<book> MODE=dev
PDF?=data/books/mvs/source_pdfs/mvs_ch_0001_0700.pdf
OUT_DIR?=data/clean/mvs
MODE?=dev
ingest_pdf:
	@$(VENV_GUARD)
	$(ACTIVATE) python scripts/ingest_nodb.py $(PDF) $(OUT_DIR)

# Classify a well_done.jsonl into sections under classified/
# Usage: make classify_well_done WELL_DONE=path/to/*_well_done.jsonl OUT_DIR=data/clean/<book>/classified
# Classify a well_done.jsonl into sections under classified/
# Usage: make classify_well_done WELL_DONE=path/to/*_well_done.jsonl OUT_DIR=data/clean/<book>/classified
WELL_DONE?=$(OUT_DIR)/mvs_ch_0001_0700_well_done.jsonl
CLASSIFIED_OUT?=$(OUT_DIR)/classified
classify_well_done:
	@$(VENV_GUARD)
	$(ACTIVATE) python -m abm.classifier.classifier_cli $(WELL_DONE) $(CLASSIFIED_OUT)

# Convenience combo: ingest then classify using variables above
ingest_and_classify: ingest_pdf classify_well_done


######################
# LANGFLOW
######################

.PHONY: langflow
langflow:
	@$(VENV_GUARD)
	./scripts/run_langflow.sh

.PHONY: langflow_start_bg
langflow_start_bg:
	@$(VENV_GUARD)
	chmod +x scripts/langflow_start_bg.sh; ./scripts/langflow_start_bg.sh

.PHONY: langflow_stop
langflow_stop:
	chmod +x scripts/langflow_stop.sh; ./scripts/langflow_stop.sh
	
.PHONY: langflow-import-segments
langflow-import-segments:
	./scripts/import_segments_flow.sh

.PHONY: segment
segment:
	@echo "segment target deprecated: langflow_runner removed. Use LangFlow UI or tools/run_flow.py."


######################
# HELP
######################

help:
	@echo '----'
	@echo 'dev_setup                   - create .venv and install minimal dev tools'
	@echo 'venv                         - create virtual environment (.venv)'
	@echo 'install                      - install base package editable'
	@echo 'install_dev                  - install dev extras'
	@echo 'install_pdf                  - install dev + pdf extras'
	@echo 'format                       - run code formatters'
	@echo 'lint                         - run linters'
	@echo 'test                         - run unit tests'
	@echo 'tests                        - run unit tests'
	@echo 'test TEST_FILE=<test_file>   - run all tests in file'
	@echo 'test_watch                   - run unit tests in watch mode'
	@echo 'make install                 - install base + test deps (uv or pip)'
	@echo 'make lint                    - ruff checks'
	@echo 'make type                    - mypy checks'
	@echo 'make itest                   - run LangFlow REST flow via tools/run_flow.py'
	@echo 'docs_link_check              - scan docs/ for broken local links'


# Lightweight helpers for the components/ tooling pack
.PHONY: install lint type itest
install:
	uv pip install -e . || pip install -e .
	uv pip install pytest ruff mypy requests || pip install pytest ruff mypy requests

lint:
	ruff check .
	ruff format --check .

type:
	mypy .

itest:
	python tools/run_flow.py


# Minimal KISS dev setup
.PHONY: dev_setup
dev_setup:
	python3.11 -m venv .venv || python3 -m venv .venv
	. .venv/bin/activate; pip install -U pip
	. .venv/bin/activate; pip install -r requirements-dev.txt
	@echo 'Activate with: source .venv/bin/activate'

# Docs utilities
.PHONY: docs_link_check
docs_link_check:
	@$(VENV_GUARD)
	python scripts/check_docs_links.py
