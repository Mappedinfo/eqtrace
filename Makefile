PY = code/.venv/bin/python
EQ = $(PY) -m eqtrace
LATEXMK = latexmk -xelatex -interaction=nonstopmode -halt-on-error

all: test demo paper

setup:
	uv sync --project code --extra proof --all-groups --frozen

test:
	$(PY) -m pytest code/tests -q --junitxml=artifacts/tests.xml

demo: test
	$(EQ) check eqtrace.toml --out artifacts/equations
	$(EQ) check selfcheck.toml --out artifacts/selfcheck
	$(EQ) verify artifacts/selfcheck/report.json --project .
	$(PY) scripts/run_experiments.py
	$(EQ) trace examples/engineering/architecture.toml sequence-run
	$(EQ) architecture examples/engineering/architecture.toml --require-runs --out artifacts/engineering
	$(EQ) architecture architecture.toml --out artifacts/self-architecture
	$(PY) scripts/export_paper_evidence.py

paper:
	cd paper && $(LATEXMK) main.tex
	cp paper/main.pdf paper/eqtrace.pdf

serve:
	$(EQ) serve eqtrace.toml

browser:
	node scripts/check_graph_layout.cjs
	$(PY) scripts/check_browser.py
	$(PY) scripts/check_engineering_browser.py

build:
	uv build --project code

clean:
	cd paper && latexmk -C

.PHONY: all setup test demo paper serve browser build clean
