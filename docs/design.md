# Architecture and MVP scope

EqTrace's question is whether a reviewable, local check can link a paper's method to independently authored source and actual execution without formalizing an entire research software stack at once.

The implementation has two layers sharing source bindings and reports:

1. The engineering layer scans explicit Python codebases and CSV/JSONL datasets. A manifest groups files into hierarchical semantic blocks, declares virtual interfaces, selects named flows, and specifies runs. Bounded runtime instrumentation records calls, lines, array shapes, and declared output write events. The audit checks freshness and observed interfaces.
2. The scalar layer binds labeled LaTeX equations or straight-line pseudocode to pure Python functions. It lowers both to an ordered expression IR and separately checks structure, real equivalence, and sampled execution. Selected leaves attach to engineering blocks by verified source membership.

The offline workbenches and JSON outputs are views of those reports. Human or AI explanations do not generate evidence states. The live equation editor checks temporary pairs through the same checker.

## Acceptance demonstrated by this repository

- Bidirectional minimal Python, LaTeX, pseudocode, SVG/Mermaid/JSON computation graphs.
- Ordered operation and source-location inspection without auto-overwriting inputs.
- Real-domain proof, numeric execution, and provenance as distinct fields.
- Multi-file blocks across codebases, nested blocks, virtual interfaces, and multiple flows.
- Observed dataset-to-LaTeX summaries and required-run freshness checks.
- Synthetic sequence preprocessing, frozen attention, regression-head training/adaptation, and evaluation.
- Authored fault corpus, focused regression tests, browser checks, and self-application.

See [trust.md](trust.md) for boundaries. The next research step is an independent multi-project evaluation and selected tensor/operator contracts. Generic whole-program verification, automatic scientific meaning inference, Lean certification, GPU tracing, and collaborative hosted editing are outside this release.
