# Engineering manifests

Start from the complete [sequence example](../examples/engineering/architecture.toml). The schema is version 1, encoded in TOML and validated by `load_architecture`; unknown fields are rejected. No schema generator or LLM is involved.

## Roots and semantic blocks

```toml
schema_version = 1
[[repositories]]
id = "model"
path = "model_repo"
[[repositories]]
id = "shared"
path = "../shared_repo"

[[entities]]
id = "tokens"
type = "virtual_tensor"
meaning = "Input token features before attention"
shape_axes = ["N", 6, 8]
dtype = "float64"
observed_at = {file="model:attention.py", function="attention", argument="values"}

[[entities]]
id = "attended"
type = "virtual_tensor"
meaning = "Output after attention projection"

[[blocks]]
id = "attention"
meaning = "Declared Q/K/V projection, attention weights, and output projection"
members = [{repository="model", pattern="attention.py"}, {repository="shared", pattern="softmax.py"}]
inputs = ["tokens"]
outputs = ["attended"]
```

Repository paths are explicit and may point to other codebases. Dataset, equation-manifest, receipt, and materialized-entity paths stay within the architecture manifest's directory. A block can add `parent = "encoder"`; parents must resolve and be acyclic. File membership uses `fnmatch` patterns on repository-relative Python paths. A selector matching no scanned file blocks the report.

Meanings, port names, and free-text `shape` descriptions are declarations. `shape_axes` is checked against NumPy observations when a run is available. Symbolic dimensions bind **within each observation**, not globally across unrelated calls or entities. Only selected NumPy arguments and returns are observed; this is not a PyTorch/GPU shape verifier.

## Datasets and flows

```toml
[[datasets]]
id = "sequences"
path = "data/sequences.csv"
required_columns = ["sample_id", "target"]
allow_nulls = false
max_rows = 100000

[[flows]]
id = "encoder-flow"
label = "Inside the encoder"
nodes = ["tokens", "attention", "attended"]
```

The scanner supports CSV and JSONL, up to 256 MiB per file and at most 1,000,000 scanned rows. A complete nonempty scan is required for acceptance. It emits field names, inferred value types, null counts, ranges, completeness, and a full-file SHA-256. The generated LaTeX table uses these observations; descriptions and scientific units are not inferred. No raw rows enter the report, but names, ranges, source excerpts, and file paths may still be sensitive in a real project.

Flows select nodes from the same graph; block ports supply the default edges. Optional `edges = [["from", "to"]]` adds declared sequencing edges. Named flows do not invent additional execution evidence. Click a block to inspect member files, then drill into the source dependency view.

## Explicit runs

A run names a Python entrypoint within one root, optional string arguments, expected blocks, materialized inputs/outputs, and a receipt path. Outputs are entities with `path`; inputs can be datasets or materialized entities. See the example for a complete declaration.

```bash
code/.venv/bin/eqtrace architecture examples/engineering/architecture.toml
code/.venv/bin/eqtrace trace examples/engineering/architecture.toml sequence-run
code/.venv/bin/eqtrace architecture examples/engineering/architecture.toml --require-runs
```

The first command scans without launching the pipeline. The second runs trusted code with the current Python environment and captures a bounded main-thread trace. The final command requires fresh successful receipts, required block function calls, observed shape matches, and current output evidence. It exits nonzero on failure. `SCANNED` never means executed; `CHECKED_WITH_RUNS` never means whole-program mathematical proof.

Required outputs must exist and have been opened for writing during that run. This prevents an untouched old checkpoint from satisfying the requirement. It cannot prove complete content regeneration or scientific validity. Native kernels, subprocesses, other threads, filesystem writes not using observed Python audit events, and malicious trace manipulation are outside coverage.

## Bind scalar proofs into blocks

At manifest root, set `equation_manifests = ["equations.toml"]`. In a block, use `equations = ["equations.toml#sample-error"]`. The checker resolves the scalar contract and requires its implementation to belong to that block. Proof and scalar sampling evidence are displayed separately from the block's runtime coverage. The scalar contract's declared domain is not automatically checked at every pipeline call.

## Machine-readable output

`architecture.json` contains `nodes`, `edges`, `code`, `datasets`, `blocks`, `flows`, `runs`, `shape_checks`, `equations`, `errors`, and hashes. Every relationship has an evidence kind or explicit status. `architecture.mmd` and dataset `.tex` files accompany the self-contained HTML. An AI reviewer should cite exact node/file/function IDs and evidence fields, and must not convert a declared meaning or a static candidate into a proof claim.

## Reading the source graph

Source dependencies start at the **Packages** level: files sharing a source
directory are grouped within their codebase. Arrows point from the importer to
its dependency; multiple imports between the same groups share a connection.
These groups are browsing aids, separate from manifest-defined semantic blocks.

Select a package and choose **Open files**. Its direct outgoing dependencies
remain visible as dashed cards, including dependencies in another codebase.
**Package overview** returns to the groups. Use **Files** to display the complete
filtered inventory, or **Focus direct connections** to inspect one node and its
incoming/outgoing neighbors. Selecting any node highlights those connections.

The bundled Dagre layout places dependencies in layers; connectors turn in the
gaps between layers. Choose a vertical or horizontal direction, zoom, scroll or
drag the background, and export the current SVG. Initial zoom preserves readable
labels; **Fit** explicitly reduces the full graph to the viewport. All operations
work offline and preserve the underlying evidence report.
