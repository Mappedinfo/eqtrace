# Evidence and trust model

EqTrace is a lightweight consistency checker. Its trusted implementation includes the frontends, lowering rules, IR semantics, Z3 translation, runtime harness, instrumentation, and renderers. Self-checking a few kernels does not remove that trust boundary.

## Formal evidence

`PROVED_REAL` is solver evidence about a restricted scalar expression pair over declared mathematical real domains. The backend checks nonempty assumptions and denominator totality before inequality. SMT-LIB query files make the actual queries replayable. No Lean proof term, independently checked certificate, arbitrary Python proof, tensor proof, or universal floating-point guarantee is produced.

## Engineering evidence

Block meaning, parent relations, and virtual dataflow are author declarations. Static calls are candidates; unresolved targets remain visible. Run observations cover selected Python sources and the main thread. Function calls, shapes, and output-open events establish limited facts about one run. A block with `CALLS_OBSERVED` may contain unexecuted member files or branches. A whole block does not inherit the proof of a bound scalar leaf.

## Freshness and environment

Receipts bind source, configuration, checker, dataset, output, and relevant recorded runtime versions. Digests detect accidental edits and stale state under an honest producer. They are not signatures or remote attestations. Dependencies recorded by the instrumentation are selected loaded numerical libraries; the full OS, hardware, external services, native kernels, and process tree are not attested. Regenerate reports after code or environment changes.

## Local execution and disclosure

`check` compiles only a validated target AST. `architecture` parses source and reads datasets. `trace` deliberately executes a declared project entry point with ordinary user permissions, in a child process with a timeout; it is not a sandbox. Use trusted code. The loopback live editor enforces same-origin requests and cannot launch pipeline commands.

Offline reports contain source excerpts, paths, hashes, dataset schemas/ranges, solver witnesses, and sampled scalar values. Dataset row contents are omitted from schema summaries, but a user's pipeline logs may contain arbitrary text. Review reports and logs before public release. This repository uses synthetic public fixtures only.

## Non-claims

The prototype does not establish scientific validity, exhaustive manuscript coverage, complete call-graph recovery, all-input pipeline correctness, soundness of its own parsers, or effectiveness on an independent bug corpus. An unsupported result states that the contract was not established; it does not establish that the submitted method is wrong.
