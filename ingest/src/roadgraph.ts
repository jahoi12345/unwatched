import { haversineMeters, type LatLon } from './geo.ts';
import type { RoadNetwork } from './sources/overpass.ts';

export interface RoadGraph {
	nodes: Map<number, LatLon>;
	adjacency: Map<number, { to: number; distanceMeters: number }[]>;
}

export function buildRoadGraph(network: RoadNetwork): RoadGraph {
	const nodes = new Map<number, LatLon>();
	for (const n of network.nodes) nodes.set(n.id, { lat: n.lat, lon: n.lon });

	const adjacency = new Map<number, { to: number; distanceMeters: number }[]>();
	function addEdge(a: number, b: number) {
		const pa = nodes.get(a);
		const pb = nodes.get(b);
		if (!pa || !pb) return; // node outside the query result (rare clipped way)
		const d = haversineMeters(pa, pb);
		if (!adjacency.has(a)) adjacency.set(a, []);
		adjacency.get(a)!.push({ to: b, distanceMeters: d });
	}

	for (const way of network.ways) {
		for (let i = 0; i < way.nodeIds.length - 1; i++) {
			const a = way.nodeIds[i];
			const b = way.nodeIds[i + 1];
			addEdge(a, b);
			addEdge(b, a); // treat as undirected — we don't have reliable one-way data here
		}
	}

	return { nodes, adjacency };
}

/** Brute-force nearest node — fine at this graph size (tens of thousands of nodes), no spatial index needed. */
export function nearestNode(graph: RoadGraph, point: LatLon): number {
	let bestId = -1;
	let bestDist = Infinity;
	for (const [id, pos] of graph.nodes) {
		const d = haversineMeters(point, pos);
		if (d < bestDist) {
			bestDist = d;
			bestId = id;
		}
	}
	return bestId;
}

class MinHeap {
	private items: { id: number; priority: number }[] = [];

	push(id: number, priority: number) {
		this.items.push({ id, priority });
		let i = this.items.length - 1;
		while (i > 0) {
			const parent = (i - 1) >> 1;
			if (this.items[parent].priority <= this.items[i].priority) break;
			[this.items[parent], this.items[i]] = [this.items[i], this.items[parent]];
			i = parent;
		}
	}

	pop(): { id: number; priority: number } | undefined {
		if (this.items.length === 0) return undefined;
		const top = this.items[0];
		const last = this.items.pop()!;
		if (this.items.length > 0) {
			this.items[0] = last;
			let i = 0;
			for (;;) {
				const l = 2 * i + 1;
				const r = 2 * i + 2;
				let smallest = i;
				if (l < this.items.length && this.items[l].priority < this.items[smallest].priority) smallest = l;
				if (r < this.items.length && this.items[r].priority < this.items[smallest].priority) smallest = r;
				if (smallest === i) break;
				[this.items[smallest], this.items[i]] = [this.items[i], this.items[smallest]];
				i = smallest;
			}
		}
		return top;
	}

	get size() {
		return this.items.length;
	}
}

export interface RouteResult {
	path: LatLon[];
	totalMeters: number;
}

/** Dijkstra shortest path by distance, using a binary heap. Returns null if unreachable. */
export function shortestPath(graph: RoadGraph, fromId: number, toId: number): RouteResult | null {
	const dist = new Map<number, number>();
	const prev = new Map<number, number>();
	const heap = new MinHeap();
	dist.set(fromId, 0);
	heap.push(fromId, 0);
	const visited = new Set<number>();

	while (heap.size > 0) {
		const current = heap.pop()!;
		if (visited.has(current.id)) continue;
		visited.add(current.id);
		if (current.id === toId) break;

		const neighbors = graph.adjacency.get(current.id) ?? [];
		for (const edge of neighbors) {
			if (visited.has(edge.to)) continue;
			const newDist = current.priority + edge.distanceMeters;
			if (newDist < (dist.get(edge.to) ?? Infinity)) {
				dist.set(edge.to, newDist);
				prev.set(edge.to, current.id);
				heap.push(edge.to, newDist);
			}
		}
	}

	if (!dist.has(toId)) return null;

	const pathIds: number[] = [toId];
	let cur = toId;
	while (cur !== fromId) {
		const p = prev.get(cur);
		if (p === undefined) return null;
		pathIds.push(p);
		cur = p;
	}
	pathIds.reverse();

	return {
		path: pathIds.map((id) => graph.nodes.get(id)!),
		totalMeters: dist.get(toId)!,
	};
}
