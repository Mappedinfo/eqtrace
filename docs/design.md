# MVP contract

Question: can a small deterministic checker expose disagreement between a labeled
LaTeX equation and an independently written Python function, without trusting an
AI summary or requiring authors to formalize their entire software stack?

The unit is an equation contract: a label, exact source file, function, ordered
inputs, closed real intervals, and explicit nonzero assumptions. Both sources
lower to the same ordered scalar expression representation. Neither source is
silently overwritten. The manifest binds independently authored sources.

## Acceptance

1. LaTeX to minimal Python, LaTeX back from Python, and both computation DAGs.
2. Per-node operation, inputs, stable semantic fingerprint, and source location.
3. Separate graph comparison, bounded real-equivalence SMT check, and actual
   CPython execution against the equation interpreter on deterministic samples.
4. Nonzero exit on mismatch, unsupported syntax, missing source, domain failure,
   insufficient execution, or unresolved proof when proof is required.
5. Source, configuration, checker and environment hashes in a verifiable receipt.
6. Offline HTML workbench with equation/code/graph comparison and evidence export.
7. A fault-injection corpus and self-application to formulas used by this package.

## Frozen scope

Scalar real inputs; exact decimal/rational constants; ordered +, -, *, /; literal
integer powers of absolute value at most 8; sqrt, exp, log. Python is straight-line
assignments and one final return. General modules are not imported. No loops,
branches, exception handlers, decorators, dynamic dispatch, tensor kernels, I/O,
or silent fallback. Each rejection names the node and location. Elementary
functions are executable but outside the first SMT backend. No Lean proof claim.

The Z3 backend checks satisfiable assumptions, totality of every division, and
absence of an unequal result over the declared real domain. An UNSAT result is
solver evidence relative to our translation and Z3; it is not a Lean certificate
and does not certify IEEE floating-point behavior. Numeric runs remain separate.

## Comparisons and limits

Baseline 1: a single example test. Baseline 2: ordered graph identity. EqTrace:
graph + SMT + deterministic runtime samples + strict rejection + provenance.
Measure classifications on authored fixtures, retain every per-case result, and
record wall time. No claims about real-world bug prevalence or general Python.
Self-application covers small score/error kernels; it does not establish the
correctness of the parsers or the checker that checks those kernels.

## References and inspiration

- Prove2Me and Lean: explicit trust boundary and pinned evidence.
- I Heart LA and HeartDown: existing equation-to-code/document systems; EqTrace's
  MVP focuses on independently authored sources and a CI merge check.
- code2flow: call-graph visualization is a different level of abstraction.
- Mappedinfo/llm-viz: calculation-linked inspection.
- Mappedinfo/llm-architecture-svg: semantic data separated from rendering.

No code copied from the visualization projects. The local Research MCP freshness
verdict was unknown (full-text version unverified); related-work support uses
verified public primary sources instead of local retrieval claims.
