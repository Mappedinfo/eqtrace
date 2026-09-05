# Equation and pseudocode contracts

The complete [example](../eqtrace.toml) and [self-check](../selfcheck.toml) show bindings. `paper_sources` explicitly selects LaTeX files. Every labeled equation or algorithm in those files must be bound or explicitly excluded with a reason. Unlabeled prose and transitive LaTeX inputs are outside this inventory.

## Accepted scalar syntax

- LaTeX: `equation` / `equation*`, one assignment, rational or decimal literals, declared symbols, grouping, `+ -`, multiplication, `\frac`, division, small literal integer powers, and selected elementary functions.
- Symbol spellings: single letters, numeric subscripts, selected Greek commands, and `\mathrm{identifier}` for explicit multi-letter identifiers. Inputs disambiguate symbol meaning.
- Python: scalar positional parameters, single-assignment local expressions, one final return, explicit `import math` for permitted elementary functions. No defaults, decorators, dynamic calls, branches, exceptions, mutation, reassignment, unused computation, or unsupported module header evaluation.
- LaTeX pseudocode: `algorithm` around `algorithmic`, ordered `\Require $a,b$`, optional `\Ensure $r$`, `\State $d \gets a-b$`, and final `\State \Return $...$`. No loops, branches, or statements after return.
- The integer-power range is −8 to 8, with additional expression size/depth/degree limits. Inputs are bounded by finite closed real intervals and optional explicit `nonzero` assumptions.

The parser consumes the entire expression. Unknown LaTeX commands, incomplete parses, and Python fallback paths block the contract instead of producing approximate translations. General engineering code remains available to the separate static/trace layer.

Square root, exp, and log can be translated and sampled, but this version's real proof backend does not support them. Z3 is optional. Missing Z3, unsupported operators, timeout, or `unknown` never becomes `PROVED_REAL`.

## Verdicts

| Field | Interpretation |
|---|---|
| Structural `IDENTICAL` | Same ordered expanded expression representation |
| Structural `DIFFERENT` | Operation graphs differ; algebraic policy may still pass |
| Proof `PROVED_REAL` | Nonempty domain, total rational expressions, and no unequal real output found by the accepted solver translation |
| Proof `COUNTEREXAMPLE` | Satisfying unequal-output witness |
| Proof `DOMAIN_ERROR` | An admitted input makes a divisor or negative power undefined |
| Proof `INVALID_DOMAIN` | Assumptions admit no input |
| Execution `PASS` | Required distinct samples ran and met the declared discrepancy tolerance |
| Project `PASS` | Every strict contract and selected-source inventory requirement passed |
| Project `SAMPLED_ONLY` | Explicit solver omission; exit 3, unsuitable for a strict merge gate |
| Project `FAIL` / `BLOCKED` | Disagreement or unavailable accepted evidence; nonzero exit |

`ordered` policy requires identical operation structure; `algebraic` permits rewrites with successful proof and execution. No policy silently replaces either source. Generated translations are candidates, labeled unexecuted/unproved until separately checked.

## Execution and receipts

Only the validated target function AST is compiled with a restricted namespace. The containing module is not imported. This checks current function source with ordinary scalars, not the behavior of every production caller or dependency backend.

Default sampling uses 64 distinct inputs, seed 1729, boundary/coordinate probes, and random interior probes. The rational reference interpreter evaluates exact fractions on the binary input values. The normalized squared discrepancy is `(a-b)^2/(1+b^2)` and must be at most `tolerance^2`. Insufficient distinct admissible samples, nonfinite outputs, or any failing sample prevents a pass.

```bash
code/.venv/bin/eqtrace check selfcheck.toml --out artifacts/selfcheck
code/.venv/bin/eqtrace verify artifacts/selfcheck/report.json --project .
```

Receipts include selected source hashes, checker hashes, environment versions, proof queries, graph origins, and individual execution records. Exported artifact hashes are also checked. Verification detects stale/edited receipts relative to the current environment. SHA-256 digests do not authenticate the producer or defend against a malicious checker.
