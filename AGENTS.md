# EqTrace development contract

EqTrace combines an engineering evidence graph with a restricted scalar expression checker. Treat the
parsers, lowering, execution harness, and solver translation as trusted code,
not as already verified components. Keep real-number equivalence, graph identity,
and sampled CPython execution as separate result fields.

- Unsupported syntax, missing implementations, empty evidence, stale receipts,
  solver timeouts, and undeclared denominators must never become passes.
- Never use eval, SymPy parse_expr, or unrestricted imports on project inputs.
- Scalar checking executes only the validated target function AST. Engineering
  tracing executes an explicitly declared trusted pipeline in a child process;
  state its main-thread scope and ordinary-permission boundary.
- Keep declared block meaning, static candidates, and observed runtime evidence
  distinct. A block never inherits whole-program proof from a scalar leaf.
- Preserve operator order in the graph. Algebraic equality does not imply equal
  floating-point behavior or identical algorithms.
- Every reported test or benchmark number comes from an actual command and artifact.
- Core package has no runtime dependencies. Z3 is an explicit optional extra.
- Keep public examples synthetic; no private projects, paths, notes, or credentials.
- Run `make test` and `make demo` for core changes; build the paper after prose edits.
