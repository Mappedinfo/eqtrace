# EqTrace development contract

EqTrace checks a deliberately restricted scalar expression language. Treat the
parsers, lowering, execution harness, and solver translation as trusted code,
not as already verified components. Keep real-number equivalence, graph identity,
and sampled CPython execution as separate result fields.

- Unsupported syntax, missing implementations, empty evidence, stale receipts,
  solver timeouts, and undeclared denominators must never become passes.
- Never use eval, SymPy parse_expr, or unrestricted imports on project inputs.
- Execute only the validated target function AST; state this extraction boundary.
- Preserve operator order in the graph. Algebraic equality does not imply equal
  floating-point behavior or identical algorithms.
- Every reported test or benchmark number comes from an actual command and artifact.
- Core package has no runtime dependencies. Z3 is an explicit optional extra.
- Keep public examples synthetic; no private projects, paths, notes, or credentials.
- Run `make test` and `make demo` for core changes; build the paper after prose edits.
