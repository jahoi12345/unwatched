import { existsSync, mkdirSync, readFileSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { fetchAlprCameras, fetchCityBoundingBox, type AlprCamera, type BoundingBox } from './sources/overpass.ts';
import { haversineMeters, pointToSegmentDistanceMeters, randomPointInBbox, type LatLon } from './geo.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

interface Args {
	city: string;
	trips: number;
	corridorMeters: number;
	radiusMeters: number;
	gridSize: number;
}

function parseArgs(argv: string[]): Args {
	const get = (flag: string, def: string) => argv.find((a) => a.startsWith(`--${flag}=`))?.split('=')[1] ?? def;
	return {
		city: get('city', 'Oakland, California'),
		trips: Number(get('trips', '500')),
		corridorMeters: Number(get('corridor', '80')),
		radiusMeters: Number(get('radius', '50')),
		gridSize: Number(get('grid', '80')),
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

function computeGridCoverage(bbox: BoundingBox, cameras: AlprCamera[], gridSize: number, radiusMeters: number) {
	let covered = 0;
	let total = 0;
	for (let i = 0; i < gridSize; i++) {
		for (let j = 0; j < gridSize; j++) {
			const point: LatLon = {
				lat: bbox.south + (i / (gridSize - 1)) * (bbox.north - bbox.south),
				lon: bbox.west + (j / (gridSize - 1)) * (bbox.east - bbox.west),
			};
			total++;
			for (const cam of cameras) {
				if (haversineMeters(point, { lat: cam.lat, lon: cam.lon }) <= radiusMeters) {
					covered++;
					break;
				}
			}
		}
	}
	return { total, covered, coveragePercent: (covered / total) * 100 };
}

interface TripResult {
	origin: LatLon;
	destination: LatLon;
	hits: { camera: AlprCamera; distanceAlongTripMeters: number; offsetFromCorridorMeters: number }[];
}

function simulateTrips(bbox: BoundingBox, cameras: AlprCamera[], tripCount: number, corridorMeters: number): TripResult[] {
	const halfWidth = corridorMeters / 2;
	const results: TripResult[] = [];

	for (let i = 0; i < tripCount; i++) {
		const origin = randomPointInBbox(bbox);
		const destination = randomPointInBbox(bbox);
		const tripLengthMeters = haversineMeters(origin, destination);

		const hits: TripResult['hits'] = [];
		for (const cam of cameras) {
			const camPoint: LatLon = { lat: cam.lat, lon: cam.lon };
			const offset = pointToSegmentDistanceMeters(camPoint, origin, destination);
			if (offset <= halfWidth) {
				// Approximate how far along the trip this camera sits, for ordering/timing.
				const distFromOrigin = haversineMeters(origin, camPoint);
				const distanceAlongTrip = Math.min(distFromOrigin, tripLengthMeters);
				hits.push({ camera: cam, distanceAlongTripMeters: distanceAlongTrip, offsetFromCorridorMeters: offset });
			}
		}
		hits.sort((a, b) => a.distanceAlongTripMeters - b.distanceAlongTripMeters);
		results.push({ origin, destination, hits });
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

	console.log(`\nComputing area coverage (${args.gridSize}x${args.gridSize} grid, ${args.radiusMeters}m detection radius)...`);
	const coverage = computeGridCoverage(bbox, cameras, args.gridSize, args.radiusMeters);
	console.log(
		`${coverage.coveragePercent.toFixed(1)}% of the sampled area is within ${args.radiusMeters}m of a known ALPR camera (${coverage.covered}/${coverage.total} grid points).`,
	);

	console.log(`\nSimulating ${args.trips} synthetic trips (${args.corridorMeters}m travel corridor)...`);
	const trips = simulateTrips(bbox, cameras, args.trips, args.corridorMeters);
	const capturedTrips = trips.filter((t) => t.hits.length > 0);
	const captureRatePercent = (capturedTrips.length / trips.length) * 100;
	const avgHitsPerCapturedTrip = capturedTrips.length > 0 ? capturedTrips.reduce((s, t) => s + t.hits.length, 0) / capturedTrips.length : 0;

	console.log(
		`${captureRatePercent.toFixed(1)}% of synthetic trips passed at least one camera (${capturedTrips.length}/${trips.length}); ` +
			`captured trips saw an average of ${avgHitsPerCapturedTrip.toFixed(1)} camera(s).`,
	);

	// Pick a representative example: the captured trip closest to the median hit count.
	const sortedByHits = [...capturedTrips].sort((a, b) => a.hits.length - b.hits.length);
	const example = sortedByHits[Math.floor(sortedByHits.length / 2)];
	const AVG_SPEED_MPS = 11.2; // ~25 mph synthetic assumption, for illustrating timing only

	const exampleNarrative = example
		? {
				origin: example.origin,
				destination: example.destination,
				hitCount: example.hits.length,
				sequence: example.hits.map((h) => ({
					manufacturer: h.camera.manufacturer,
					lat: h.camera.lat,
					lon: h.camera.lon,
					approxSecondsIntoTrip: Math.round(h.distanceAlongTripMeters / AVG_SPEED_MPS),
				})),
			}
		: null;

	if (exampleNarrative) {
		console.log(`\nExample reconstruction (synthetic trip, ${exampleNarrative.hitCount} camera hits):`);
		for (const hit of exampleNarrative.sequence) {
			console.log(`  T+${hit.approxSecondsIntoTrip}s — camera at (${hit.lat.toFixed(5)}, ${hit.lon.toFixed(5)})${hit.manufacturer ? ` [${hit.manufacturer}]` : ''}`);
		}
	}

	const report = {
		city: args.city,
		bbox,
		generatedAt: new Date().toISOString(),
		cameraCount: cameras.length,
		coverage: {
			gridSize: args.gridSize,
			radiusMeters: args.radiusMeters,
			...coverage,
		},
		trips: {
			count: args.trips,
			corridorMeters: args.corridorMeters,
			capturedTripCount: capturedTrips.length,
			captureRatePercent,
			avgHitsPerCapturedTrip,
			exampleReconstruction: exampleNarrative,
		},
		methodology: [
			'Camera locations are real: every point comes from OpenStreetMap nodes tagged surveillance:type=ALPR, the same crowdsourced, volunteer-surveyed dataset DeFlock is built on.',
			'Trip origins and destinations are synthetic: uniformly random points generated fresh on each run, never derived from any real person’s address, device, or movement history.',
			'A trip is modeled as a straight line between two random points with a fixed-width travel corridor, not real street routing. This is a conservative simplification — actual driving routes follow streets, which are less direct than a straight line and disproportionately pass through arterial roads where ALPR cameras are concentrated, so real capture rates are likely higher than this estimate, not lower.',
			'Area coverage is computed on a regular grid sampled across the city’s bounding box, not its exact administrative boundary, so a thin edge margin may include neighboring jurisdictions.',
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
