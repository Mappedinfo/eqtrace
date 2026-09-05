# Contributing

Use Python 3.11+ and uv. Run `make setup`, `make test`, and `make demo` before proposing a checker change. `make build` creates a wheel. CI repeats these checks in fresh environments.

Changes to accepted semantics should include a valid case, a meaningful invalid/control case, and any required rejection boundary. Do not turn solver unknowns, unsupported paths, incomplete data, or stale execution evidence into a pass. Preserve the distinction between declared meaning, static candidates, observed execution, real equivalence, and numerical sampling.

The Python core has no runtime dependencies. Engineering HTML embeds the pinned MIT-licensed Dagre browser bundle and its notices (see `code/src/eqtrace/web/vendor/README.md`). Z3 belongs to the explicit `proof` extra. NumPy is a demo dependency; Playwright is a browser-development dependency. Do not introduce external AI calls or credentials into the core path.

For UI changes, use Node.js 18+ for the offline geometry checks, install Chromium with `code/.venv/bin/python -m playwright install chromium`, start `make serve`, and run `make browser`. The browser checks cover desktop and 637px layouts, package expansion, focus, zoom, panning, and SVG export. The geometry checks exercise real imports, cycles, isolated nodes, and empty graphs in both directions. Inspect the resulting screenshots in `artifacts/browser` and `artifacts/engineering-browser`.

## Building the paper

`make test && make demo` generates the paper's count macros, case table, and observed dataset table. Then run `make paper`. The tracked `paper/eqtrace.pdf` is the released local compilation; temporary TeX files are ignored.

The paper uses XeLaTeX, latexmk, biber, biblatex APA, xeCJK, TikZ, algorithm, and algorithmicx/algpseudocode. Install these through TeX Live or MacTeX. Fonts are Libertinus Serif/Sans/Mono plus Noto Serif/Sans CJK SC (or their Noto SC names). The [template font setup](https://github.com/Mappedinfo/academic-templates/tree/main/fonts) documents installation. Do not substitute missing references or hand-enter experimental result counts to make a build pass.

## Release evidence

`make demo` updates synthetic evidence and offline demo snapshots. These are host-specific recorded observations; another environment must regenerate them for fresh verification. Review changed source excerpts, paths, logs, and dataset statistics before publishing a report from a private project. This repository's public examples are synthetic.

The manuscript, software source, and evidence are reviewed together. Self-application demonstrates a small closed loop but does not prove the checker itself.
