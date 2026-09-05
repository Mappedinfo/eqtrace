LATEXMK = latexmk -xelatex -interaction=nonstopmode -halt-on-error

all: experiments figures paper

experiments:
	python3 scripts/run_experiments.py

figures:
	python3 scripts/plot_results.py

paper:
	cd paper && $(LATEXMK) main.tex

test:
	cd code && uv run pytest

clean:
	cd paper && latexmk -C

.PHONY: all experiments figures paper test clean
