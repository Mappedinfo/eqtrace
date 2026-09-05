# Offline graph layout engine

`dagre-3.1.1.min.js` is the unchanged browser bundle from
[`@dagrejs/dagre` 3.1.1](https://github.com/dagrejs/dagre), including
`@dagrejs/graphlib` 4.0.5. Both use the MIT license; the corresponding notices
are kept here and embedded into each standalone engineering HTML report.

- npm archive: `https://registry.npmjs.org/@dagrejs/dagre/-/dagre-3.1.1.tgz`
- Archive SHA-512 (base64): `zroZB1dFOFiGgv4Xcrn1DckB1o4aOikPqD2NDQPV0WM//CXGcS6xiD0rNkqHmw6FEg4tabt4nxPLwgCWT+Vb2A==`
- Bundle SHA-256: `3152d214941a5df3a3d4c079dfa338c3cd7a6c0d4c1b4c3a2fdb6bba6f6facf9`
- Extracted member: `package/dist/dagre.min.js`

To update, fetch a pinned archive with `npm pack --ignore-scripts`, verify its
integrity, extract the browser bundle and licenses, and rerun `make demo` and
`make browser`. No npm install, CDN, external request, or build step is required
to use the exported HTML. Use a modern browser with `structuredClone` support.
The upstream source-map reference is retained; the optional development map is
not shipped.

EqTrace's `graph-layout.js` groups source directories, aggregates import edges,
and adds orthogonal routing between Dagre's ranks. This affects presentation
only. Neither package membership nor geometry establishes semantic correctness
or execution evidence.
