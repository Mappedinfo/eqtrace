/* Pure graph preparation and layered layout; never changes report evidence. */
(function (root) {
  'use strict';
  function uniqueEdges(nodes, edges) {
    const ids = new Set(nodes.map(n => n.id)), pairs = new Map();
    for (const e of edges) {
      if (!ids.has(e.from) || !ids.has(e.to)) continue;
      const key = JSON.stringify([e.from, e.to]);
      if (!pairs.has(key)) pairs.set(key, {...e, count: 0});
      pairs.get(key).count += e.count || 1;
    }
    return [...pairs.values()];
  }
  function packageId(file) {
    return 'package:' + file.repository + ':' + (file.path.split('/').slice(0, -1).join('/') || '.');
  }
  function packages(files, edges) {
    const groups = new Map(), byFile = new Map();
    for (const f of files) {
      const id = packageId(f), path = f.path.split('/').slice(0, -1).join('/') || '.';
      if (!groups.has(id)) groups.set(id, {id, kind: 'package', label: path === '.' ? 'Entry points' : path,
        path, repository: f.repository, files: [], evidence: 'static', status: 'SCANNED'});
      groups.get(id).files.push(f.id);
      byFile.set(f.id, id);
    }
    const nodes = [...groups.values()];
    const links = uniqueEdges(files, edges).filter(e => byFile.get(e.from) !== byFile.get(e.to))
      .map(e => ({...e, from: byFile.get(e.from), to: byFile.get(e.to)}));
    return {nodes, edges: uniqueEdges(nodes, links)};
  }
  function neighborhood(nodes, edges, id) {
    const ids = new Set([id]);
    for (const e of edges) {
      if (e.from === id) ids.add(e.to);
      if (e.to === id) ids.add(e.from);
    }
    const selected = nodes.filter(n => ids.has(n.id));
    return {nodes: selected, edges: uniqueEdges(selected, edges)};
  }
  function routeEdge(from, to, points, nodes, direction) {
    const axis = direction === 'LR' ? 'x' : 'y', cross = axis === 'x' ? 'y' : 'x';
    const size = axis === 'x' ? 'width' : 'height';
    const crossSize = axis === 'x' ? 'height' : 'width';
    const point = (along, across) => ({[axis]: along, [cross]: across});
    if (from.id === to.id) {
      const side = from[cross] + from[crossSize] / 2;
      return [point(from[axis] - 14, side), point(from[axis] - 14, side + 20),
        point(from[axis] + 14, side + 20), point(from[axis] + 14, side)];
    }
    // Dagre supplies a lane through each intermediate rank. Join those lanes
    // in the gaps between ranks, so a diagonal cannot cut through a wide card.
    const ranks = new Set(nodes.map(n => n[axis]));
    const lanes = points.slice(1, -1).filter(p => [...ranks].some(v => Math.abs(v - p[axis]) < .01));
    const stops = [from, ...lanes, to];
    const sign = Math.sign(to[axis] - from[axis]) || 1;
    const start = point(from[axis] + sign * from[size] / 2, from[cross]);
    const end = point(to[axis] - sign * to[size] / 2, to[cross]);
    const route = [start];
    for (let i = 1; i < stops.length; i++) {
      const a = stops[i - 1], b = stops[i], middle = (a[axis] + b[axis]) / 2;
      route.push(point(middle, a[cross]), point(middle, b[cross]));
    }
    route.push(end);
    return route.filter((p, i) => !i || p.x !== route[i - 1].x || p.y !== route[i - 1].y);
  }
  function layout(nodes, edges, direction = 'TB') {
    if (!nodes.length) return {nodes: [], edges: [], width: 480, height: 320};
    if (!root.dagre?.layout) throw new Error('The bundled graph layout engine is unavailable.');
    const compact = nodes.every(n => n.kind === 'package');
    const graph = new root.dagre.graphlib.Graph();
    graph.setGraph({rankdir: direction, ranker: 'network-simplex', acyclicer: 'greedy',
      nodesep: 36, edgesep: 18, ranksep: compact ? 40 : 64, marginx: 32, marginy: 32});
    graph.setDefaultEdgeLabel(() => ({}));
    for (const n of nodes) graph.setNode(n.id, {width: 216, height: compact ? 76 : 88});
    const links = uniqueEdges(nodes, edges);
    for (const e of links) graph.setEdge(e.from, e.to, {weight: 1});
    root.dagre.layout(graph);
    const placed = nodes.map(n => ({...n, ...graph.node(n.id)}));
    const byId = new Map(placed.map(n => [n.id, n]));
    const routed = links.map(e => ({...e, points: routeEdge(byId.get(e.from), byId.get(e.to),
      graph.edge(e.from, e.to).points, placed, direction)}));
    const points = routed.flatMap(e => e.points);
    return {nodes: placed, edges: routed,
      width: Math.ceil(Math.max(graph.graph().width, ...points.map(p => p.x + 24))),
      height: Math.ceil(Math.max(graph.graph().height, ...points.map(p => p.y + 24)))};
  }
  root.EqTraceLayout = {uniqueEdges, packageId, packages, neighborhood, layout};
})(globalThis);
