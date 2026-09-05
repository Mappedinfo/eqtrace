/* Offline geometry regressions, using the same bundled engine as the workbench. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const root = path.resolve(__dirname, '..');
const context = vm.createContext({structuredClone});
for (const file of ['vendor/dagre-3.1.1.min.js', 'graph-layout.js']) {
  vm.runInContext(fs.readFileSync(path.join(root, 'code/src/eqtrace/web', file), 'utf8'), context);
}
const api = context.EqTraceLayout;
const report = JSON.parse(fs.readFileSync(path.join(root, 'artifacts/engineering/architecture.json'), 'utf8'));
const files = report.code.files;
const imports = report.code.imports.flatMap(e => e.targets.map(to => ({from: e.from, to})));
const packages = api.packages(files, imports);
assert.equal(packages.nodes.length, 7);
assert.equal(packages.nodes.flatMap(n => n.files).length, 36);
assert.equal(new Set(packages.nodes.flatMap(n => n.files)).size, 36);

function crossesInterior(a, b, node) {
  let near = 0, far = 1;
  for (const [axis, size] of [['x', 'width'], ['y', 'height']]) {
    const low = node[axis] - node[size] / 2 + .1, high = node[axis] + node[size] / 2 - .1;
    const delta = b[axis] - a[axis];
    if (Math.abs(delta) < 1e-9) {if (a[axis] < low || a[axis] > high) return false;}
    else {
      const t1 = (low - a[axis]) / delta, t2 = (high - a[axis]) / delta;
      near = Math.max(near, Math.min(t1, t2)); far = Math.min(far, Math.max(t1, t2));
      if (near > far) return false;
    }
  }
  return true;
}
let layouts = 0;
function check(nodes, edges, direction) {
  const before = JSON.stringify({nodes, edges});
  const result = api.layout(nodes, edges, direction);
  assert.equal(JSON.stringify({nodes, edges}), before, 'Layout must not mutate evidence');
  assert.ok(Number.isFinite(result.width) && result.width > 0);
  assert.ok(Number.isFinite(result.height) && result.height > 0);
  assert.equal(result.nodes.length, nodes.length);
  const accepted = new Set(nodes.map(n => n.id));
  const expected = new Set(edges.filter(e => accepted.has(e.from) && accepted.has(e.to)).map(e => `${e.from}\0${e.to}`));
  assert.deepEqual(new Set(result.edges.map(e => `${e.from}\0${e.to}`)), expected);
  for (const [i, a] of result.nodes.entries()) {
    assert.ok(Number.isFinite(a.x) && Number.isFinite(a.y));
    for (const b of result.nodes.slice(i + 1)) {
      assert.ok(Math.abs(a.x - b.x) >= (a.width + b.width) / 2 ||
        Math.abs(a.y - b.y) >= (a.height + b.height) / 2, `Overlapping nodes: ${a.id}, ${b.id}`);
    }
  }
  for (const e of result.edges) {
    assert.ok(e.points.length >= 2);
    for (const p of e.points) assert.ok(Number.isFinite(p.x) && Number.isFinite(p.y));
    for (const n of result.nodes.filter(n => n.id !== e.from && n.id !== e.to)) {
      for (let i = 1; i < e.points.length; i++) {
        assert.ok(!crossesInterior(e.points[i - 1], e.points[i], n), `Edge ${e.from} → ${e.to} crosses ${n.id}`);
      }
    }
  }
  layouts++;
}
for (const direction of ['TB', 'LR']) {
  check(files, imports, direction);
  check(packages.nodes, packages.edges, direction);
  const nodes = ['a', 'b', 'c', 'isolated'].map(id => ({id}));
  check(nodes, [{from:'a',to:'b'}, {from:'b',to:'c'}, {from:'c',to:'a'}, {from:'a',to:'a'}], direction);
  check([], [], direction);
}
console.log(`Graph layout checks passed: ${layouts} layouts; no node overlap or edges crossing unrelated nodes.`);
