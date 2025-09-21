VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip

venv:
	python -m venv $(VENV)
	. $(VENV)/bin/activate; $(PIP) install -U pip
	. $(VENV)/bin/activate; $(PIP) install -e .

scan:
	. $(VENV)/bin/activate; $(PY) -m character_bible.cli scan --chapters data/chapters_pt1.json --chapters data/chapters_pt2.json --names data/top_names.txt --out scan_counts.json

draft:
	. $(VENV)/bin/activate; LLM_API_KEY=$$LLM_API_KEY LLM_BASE_URL=$$LLM_BASE_URL $(PY) -m character_bible.cli all --chapters data/chapters_pt1.json --chapters data/chapters_pt2.json --names data/top_names.txt --out character_bible.json

fmt:
	ruff check --fix .
	black .
