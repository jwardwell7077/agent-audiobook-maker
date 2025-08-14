.PHONY: all format lint test tests test_watch integration_tests docker_tests help extended_tests

# Default target executed when no arguments are given to make.
all: help

# Define a variable for the test file path.
TEST_FILE ?= tests/unit_tests/

test:
	python -m pytest $(TEST_FILE)

integration_tests:
	python -m pytest tests/integration_tests 

test_watch:
	python -m ptw --snapshot-update --now . -- -vv tests/unit_tests

test_profile:
	python -m pytest -vv tests/unit_tests/ --profile-svg

extended_tests:
	python -m pytest --only-extended $(TEST_FILE)

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
	python -m ruff check .
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff format $(PYTHON_FILES) --diff
	[ "$(PYTHON_FILES)" = "" ] || python -m ruff check --select I $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || python -m mypy --strict $(PYTHON_FILES)
	[ "$(PYTHON_FILES)" = "" ] || mkdir -p $(MYPY_CACHE) && python -m mypy --strict $(PYTHON_FILES) --cache-dir $(MYPY_CACHE)

format format_diff:
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

PYTHON?=python
VENV_DIR?=.venv
ACTIVATE=. $(VENV_DIR)/bin/activate;

venv:
	$(PYTHON) -m venv $(VENV_DIR)
	$(ACTIVATE) pip install --upgrade pip

install: venv
	$(ACTIVATE) pip install -e .

install_dev: venv
	$(ACTIVATE) pip install -e .[dev]

install_pdf: venv
	$(ACTIVATE) pip install -e .[dev,pdf]


######################
# HELP
######################

help:
	@echo '----'
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

