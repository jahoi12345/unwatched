import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
	fetchAlprCameras,
	fetchCityBoundingBox,
	fetchRoadNetwork,
	type AlprCamera,
	type BoundingBox,
	type RoadNetwork,
} from './sources/overpass.ts';
import { haversineMeters, pointToSegmentDistanceMeters, randomPointInBbox, type LatLon } from './geo.ts';
import { buildRoadGraph, nearestNode, shortestPath, type RoadGraph } from './roadgraph.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');
const AVG_SPEED_MPS = 11.2; // ~25 mph synthetic assumption, for illustrating timing only
const SAMPLE_ROUTE_COUNT = 7;
const MAX_ROUTE_POINTS = 150; // downsample long paths so the JSON export/frontend stay light

interface Args {
	city: string;
	trips: number;
	corridorMeters: number;
	radiusMeters: number;
}

function parseArgs(argv: string[]): Args {
	const get = (flag: string, def: string) => argv.find((a) => a.startsWith(`--${flag}=`))?.split('=')[1] ?? def;
	return {
		city: get('city', 'Oakland, California'),
		trips: Number(get('trips', '250')),
		corridorMeters: Number(get('corridor', '40')),
		radiusMeters: Number(get('radius', '50')),
	};
}

function slugify(city: string): string {
	return city
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/(^-|-$)/g, '');
}

async function getCameras(city: string, bbox: BoundingBox, slug: string): Promise<AlprCamera[]> {
	const cachePath = path.join(DATA_DIR, `cameras-${slug}.json`);
	if (existsSync(cachePath)) {
		const cached = JSON.parse(readFileSync(cachePath, 'utf-8'));
		const ageMs = Date.now() - new Date(cached.fetchedAt).getTime();
		if (ageMs < 24 * 60 * 60 * 1000) {
			console.log(`Using cached camera data for ${city} (${cached.cameras.length} cameras, fetched ${cached.fetchedAt}).`);
			return cached.cameras;
		}
	}
	console.log(`Fetching real ALPR camera locations for ${city} from OpenStreetMap/Overpass...`);
	const cameras = await fetchAlprCameras(bbox);
	mkdirSync(DATA_DIR, { recursive: true });
	writeFileSync(cachePath, JSON.stringify({ city, bbox, fetchedAt: new Date().toISOString(), cameras }, null, 2));
	console.log(`Fetched ${cameras.length} real cameras. Cached to ${cachePath}.`);
	return cameras;
}

async function getCached<T>(cachePath: string, ttlMs: number, fetcher: () => Promise<T>, label: string): Promise<T> {
	if (existsSync(cachePath)) {
		const cached = JSON.parse(readFileSync(cachePath, 'utf-8'));
		const ageMs = Date.now() - new Date(cached.fetchedAt).getTime();
		if (ageMs < ttlMs) {
			console.log(`Using cached ${label} (fetched ${cached.fetchedAt}).`);
			return cached.data;
		}
	}
	console.log(`Fetching ${label} from OpenStreetMap/Overpass...`);
	const data = await fetcher();
	mkdirSync(DATA_DIR, { recursive: true });
	writeFileSync(cachePath, JSON.stringify({ fetchedAt: new Date().toISOString(), data }, null, 2));
	console.log(`Fetched and cached ${label}.`);
	return data;
}

function downsample(path: LatLon[], maxPoints: number): LatLon[] {
	if (path.length <= maxPoints) return path;
	const step = (path.length - 1) / (maxPoints - 1);
	const result: LatLon[] = [];
	for (let i = 0; i < maxPoints; i++) {
		result.push(path[Math.round(i * step)]);
	}
	return result;
}

/** % of total arterial road length within radiusMeters of a known camera. */
function computeRoadCoverage(network: RoadNetwork, graph: RoadGraph, cameras: AlprCamera[], radiusMeters: number) {
	let totalMeters = 0;
	let coveredMeters = 0;
	const camPoints = cameras.map((c) => ({ lat: c.lat, lon: c.lon }));

	for (const way of network.ways) {
		for (let i = 0; i < way.nodeIds.length - 1; i++) {
			const a = graph.nodes.get(way.nodeIds[i]);
			const b = graph.nodes.get(way.nodeIds[i + 1]);
			if (!a || !b) continue;
			const segLength = haversineMeters(a, b);
			totalMeters += segLength;
			for (const cam of camPoints) {
				if (pointToSegmentDistanceMeters(cam, a, b) <= radiusMeters) {
					coveredMeters += segLength;
					break;
				}
			}
		}
	}

	return { totalMeters, coveredMeters, coveragePercent: totalMeters > 0 ? (coveredMeters / totalMeters) * 100 : 0 };
}

interface RoutedTrip {
	origin: LatLon;
	destination: LatLon;
	path: LatLon[];
	totalMeters: number;
	hits: { camera: AlprCamera; distanceAlongMeters: number }[];
}

function cumulativeDistances(path: LatLon[]): number[] {
	const cum = [0];
	for (let i = 1; i < path.length; i++) {
		cum.push(cum[i - 1] + haversineMeters(path[i - 1], path[i]));
	}
	return cum;
}

function findHitsAlongPath(path: LatLon[], cum: number[], cameras: AlprCamera[], halfWidth: number): RoutedTrip['hits'] {
	const hits: RoutedTrip['hits'] = [];
	for (const cam of cameras) {
		const camPoint: LatLon = { lat: cam.lat, lon: cam.lon };
		let bestOffset = Infinity;
		let bestDistAlong = 0;
		for (let i = 0; i < path.length - 1; i++) {
			const offset = pointToSegmentDistanceMeters(camPoint, path[i], path[i + 1]);
			if (offset < bestOffset) {
				bestOffset = offset;
				// approximate distance-along as the cumulative distance at the segment start
				bestDistAlong = cum[i] + haversineMeters(path[i], camPoint);
			}
		}
		if (bestOffset <= halfWidth) {
			hits.push({ camera: cam, distanceAlongMeters: Math.min(bestDistAlong, cum[cum.length - 1]) });
		}
	}
	hits.sort((a, b) => a.distanceAlongMeters - b.distanceAlongMeters);
	return hits;
}

function simulateRoutedTrips(
	bbox: BoundingBox,
	graph: RoadGraph,
	cameras: AlprCamera[],
	tripCount: number,
	corridorMeters: number,
): RoutedTrip[] {
	const halfWidth = corridorMeters / 2;
	const results: RoutedTrip[] = [];
	const maxAttempts = tripCount * 4; // real road graphs can have disconnected components near bbox edges
	let attempts = 0;

	while (results.length < tripCount && attempts < maxAttempts) {
		attempts++;
		const originPoint = randomPointInBbox(bbox);
		const destPoint = randomPointInBbox(bbox);
		const originNode = nearestNode(graph, originPoint);
		const destNode = nearestNode(graph, destPoint);
		if (originNode === destNode) continue;

		const route = shortestPath(graph, originNode, destNode);
		if (!route || route.path.length < 2) continue;

		const cum = cumulativeDistances(route.path);
		const hits = findHitsAlongPath(route.path, cum, cameras, halfWidth);

		results.push({ origin: route.path[0], destination: route.path[route.path.length - 1], path: route.path, totalMeters: route.totalMeters, hits });
	}

	return results;
}

async function main() {
	const args = parseArgs(process.argv.slice(2));
	const slug = slugify(args.city);

	console.log(`Resolving bounding box for "${args.city}"...`);
	const bbox = await fetchCityBoundingBox(args.city);
	console.log(`Bounding box: ${JSON.stringify(bbox)}`);

	const cameras = await getCameras(args.city, bbox, slug);
	if (cameras.length === 0) {
		console.log('No ALPR cameras found in this bounding box on OpenStreetMap. Try a different city.');
		return;
	}
	console.log(`${cameras.length} real cameras loaded.`);

	const network = await getCached<RoadNetwork>(
		path.join(DATA_DIR, `roads-${slug}.json`),
		7 * 24 * 60 * 60 * 1000,
		() => fetchRoadNetwork(bbox),
		`arterial road network for ${args.city}`,
	);
	console.log(`Road network: ${network.nodes.length} nodes, ${network.ways.length} ways.`);

	console.log('Building routing graph...');
	const graph = buildRoadGraph(network);

	console.log(`\nComputing road-length coverage (${args.radiusMeters}m detection radius)...`);
	const coverage = computeRoadCoverage(network, graph, cameras, args.radiusMeters);
	console.log(
		`${coverage.coveragePercent.toFixed(1)}% of arterial road length (${(coverage.totalMeters / 1000).toFixed(0)}km total) is within ${args.radiusMeters}m of a known ALPR camera.`,
	);

	console.log(`\nRouting ${args.trips} synthetic trips over real streets (${args.corridorMeters}m detection corridor)...`);
	const trips = simulateRoutedTrips(bbox, graph, cameras, args.trips, args.corridorMeters);
	const capturedTrips = trips.filter((t) => t.hits.length > 0);
	const captureRatePercent = trips.length > 0 ? (capturedTrips.length / trips.length) * 100 : 0;
	const avgHitsPerCapturedTrip = capturedTrips.length > 0 ? capturedTrips.reduce((s, t) => s + t.hits.length, 0) / capturedTrips.length : 0;

	console.log(
		`${captureRatePercent.toFixed(1)}% of routed trips passed at least one camera (${capturedTrips.length}/${trips.length}); ` +
			`captured trips saw an average of ${avgHitsPerCapturedTrip.toFixed(1)} camera(s).`,
	);

	// Example reconstruction: the captured trip closest to the median hit count.
	const sortedByHits = [...capturedTrips].sort((a, b) => a.hits.length - b.hits.length);
	const example = sortedByHits[Math.floor(sortedByHits.length / 2)];

	const exampleNarrative = example
		? {
				hitCount: example.hits.length,
				sequence: example.hits.map((h) => ({
					manufacturer: h.camera.manufacturer,
					lat: h.camera.lat,
					lon: h.camera.lon,
					approxSecondsIntoTrip: Math.round(h.distanceAlongMeters / AVG_SPEED_MPS),
				})),
			}
		: null;

	if (exampleNarrative) {
		console.log(`\nExample reconstruction (routed trip, ${exampleNarrative.hitCount} camera hits):`);
		for (const hit of exampleNarrative.sequence) {
			console.log(`  T+${hit.approxSecondsIntoTrip}s — camera at (${hit.lat.toFixed(5)}, ${hit.lon.toFixed(5)})${hit.manufacturer ? ` [${hit.manufacturer}]` : ''}`);
		}
	}

	// A handful of full routes (real streets) for the frontend's multi-vehicle
	// "traffic" animation — picked from trips that actually got captured, so
	// the animation always has something to show.
	const sampleRoutes = capturedTrips
		.sort(() => Math.random() - 0.5)
		.slice(0, SAMPLE_ROUTE_COUNT)
		.map((t) => {
			const downsampled = downsample(t.path, MAX_ROUTE_POINTS);
			return {
				path: downsampled,
				totalMeters: t.totalMeters,
				hits: t.hits.map((h) => ({
					manufacturer: h.camera.manufacturer,
					lat: h.camera.lat,
					lon: h.camera.lon,
					distanceAlongMeters: h.distanceAlongMeters,
					approxSecondsIntoTrip: Math.round(h.distanceAlongMeters / AVG_SPEED_MPS),
				})),
			};
		});

	const report = {
		city: args.city,
		bbox,
		generatedAt: new Date().toISOString(),
		cameraCount: cameras.length,
		roadNetwork: { nodeCount: network.nodes.length, wayCount: network.ways.length },
		coverage: {
			radiusMeters: args.radiusMeters,
			...coverage,
		},
		trips: {
			count: trips.length,
			corridorMeters: args.corridorMeters,
			capturedTripCount: capturedTrips.length,
			captureRatePercent,
			avgHitsPerCapturedTrip,
			exampleReconstruction: exampleNarrative,
		},
		sampleRoutes,
		methodology: [
			'Camera locations are real: every point comes from OpenStreetMap nodes tagged surveillance:type=ALPR, the same crowdsourced, volunteer-surveyed dataset DeFlock is built on.',
			'Roads are real too: routing runs over the actual arterial street network (motorway through tertiary) fetched from OpenStreetMap, not straight lines — trips follow real streets and turns, computed via shortest-path (Dijkstra) routing.',
			'Trip origins and destinations are synthetic: uniformly random points generated fresh on each run, snapped to the nearest real road, never derived from any real person’s address, device, or movement history.',
			'Coverage is now measured as % of arterial road length within detection range of a known camera, not raw land area — a more meaningful number since surveillance exposure only matters where vehicles actually drive.',
			'Residential side streets are excluded from the road network (arterials only), both to keep routing fast and because ALPR cameras concentrate on arterial roads/chokepoints in the first place — so this is a reasonable, if not perfectly exhaustive, model of real driving exposure.',
		],
	};

	mkdirSync(DATA_DIR, { recursive: true });
	const outPath = path.join(DATA_DIR, `trajectory-report-${slug}.json`);
	writeFileSync(outPath, JSON.stringify(report, null, 2));
	console.log(`\nReport written to ${outPath}`);
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
