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
	python -m abm.ingestion.pdf_to_text_cli $(FILE) $(OUT)

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
	$(ACTIVATE) python -m abm.ingestion.pdf_to_text_cli \
		data/books/mvs/source_pdfs/MyVampireSystem_CH0001_0700.pdf \
		data/clean/mvs/mvs.txt --preserve-form-feeds --dev

# Run the classifier CLI on local mvs text and write artifacts under data/clean/mvs/classified
dev_mvs_classify:
	@$(VENV_GUARD)
	$(ACTIVATE) python -m abm.classifier.classifier_cli \
		data/clean/mvs/mvs.txt data/clean/mvs/classified

# Run the chapterizer CLI on local mvs text and emit chapters.json and readable variants
dev_mvs_chapterize:
	@$(VENV_GUARD)
	$(ACTIVATE) python -m abm.structuring.chapterizer_cli \
		data/clean/mvs/mvs.txt data/clean/mvs/chapters.json --dev

# One-shot: pdf->text --dev, classifier, chapterizer --dev
dev_mvs_all: dev_mvs_txt dev_mvs_classify dev_mvs_chapterize

# Fast unit tests only
test_quick:
	@$(VENV_GUARD)
	$(ACTIVATE) pytest -q tests/unit_tests

# All tests including optional ones when env is set
test_all_optional:
	@$(VENV_GUARD)
	ABM_E2E_MVS=$${ABM_E2E_MVS:-0} $(ACTIVATE) pytest -q


######################
# LANGFLOW
######################

.PHONY: langflow
langflow:
	@$(VENV_GUARD)
	./scripts/run_langflow.sh
	
.PHONY: langflow-import-segments
langflow-import-segments:
	./scripts/import_segments_flow.sh

.PHONY: segment
segment:
	@$(VENV_GUARD)
	$(ACTIVATE) python -m src.abm.langflow_runner mvs --stem segments_dev


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
