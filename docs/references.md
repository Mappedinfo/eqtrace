# Source and template provenance

Public primary sources checked on 2026-09-05:

- [Prove2Me about](https://prove2.me/about) and [paper v2](https://arxiv.org/abs/2608.28433v2): inspiration for explicit machine-checked evidence and trust boundaries. EqTrace uses no Prove2Me code and has no Lean backend.
- [Lean learning resources](https://lean-lang.org/learn/): primary link for Lean 4 and its published system paper.
- [I Heart LA](https://iheartla.github.io/) and [HeartDown](https://iheartla.github.io/heartdown/): established equation-to-code and executable-document work. EqTrace makes no priority claim for that idea.
- [SymPy parsing documentation](https://docs.sympy.org/latest/modules/parsing.html): LaTeX parsing ambiguity and incomplete-parse behavior; EqTrace implements its own restricted fully consuming parser.
- [Z3 arithmetic guide](https://microsoft.github.io/z3guide/docs/theories/Arithmetic/): real arithmetic and division-by-zero semantics; motivates explicit totality checks.
- [code2flow](https://github.com/scottrogowski/code2flow): candidate call graphs and their uncertainty.

Read-only local visual references were the Mappedinfo checkouts of [llm-viz](https://github.com/bbycroft/llm-viz) and [llm-architecture-svg](https://github.com/Mappedinfo/llm-architecture-svg). They informed calculation-linked inspection and separation of semantic graph data from rendering. No source code was copied from those projects.

The project was initialized with Copier from the `paper-with-code` template in [Mappedinfo/academic-templates](https://github.com/Mappedinfo/academic-templates). The initial template layout, font configuration, and Makefile were subsequently adapted to this software report. Python dependencies are pinned in `code/uv.lock`.

`paper/references.bib` contains project-local bibliographic entries verified against the primary sources above. The report is an AI-assisted software technical report, not a peer-reviewed claim of a new general verification method.
