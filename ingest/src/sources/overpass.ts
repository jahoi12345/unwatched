export interface BoundingBox {
	south: number;
	west: number;
	north: number;
	east: number;
}

export interface AlprCamera {
	id: number;
	lat: number;
	lon: number;
	manufacturer: string | null;
	direction: string | null;
	zone: string | null;
}

const OVERPASS_ENDPOINTS = ['https://overpass-api.de/api/interpreter', 'https://overpass.kumi.systems/api/interpreter'];

const USER_AGENT = 'unwatched-trajectory-research/1.0 (public-interest anti-surveillance research tool)';

/**
 * Resolves a place name to a bounding box via OSM's Nominatim geocoder.
 * This never handles any user/personal address — only public place names
 * like "Oakland, California" for choosing which city's public camera
 * dataset to analyze.
 */
export async function fetchCityBoundingBox(cityQuery: string): Promise<BoundingBox> {
	const url = `https://nominatim.openstreetmap.org/search?q=${encodeURIComponent(cityQuery)}&format=json&limit=1`;
	const res = await fetch(url, { headers: { 'User-Agent': USER_AGENT } });
	if (!res.ok) throw new Error(`Nominatim error: ${res.status}`);
	const data = (await res.json()) as { boundingbox: string[] }[];
	if (data.length === 0) throw new Error(`No geocoding result for "${cityQuery}"`);
	const [south, north, west, east] = data[0].boundingbox.map(Number);
	return { south, west, north, east };
}

interface OverpassElement {
	type: 'node' | 'way' | 'relation';
	id: number;
	lat?: number;
	lon?: number;
	nodes?: number[];
	tags?: Record<string, string>;
}

async function runOverpassQuery(query: string, timeoutMs: number): Promise<OverpassElement[]> {
	let lastErr: unknown;
	for (const endpoint of OVERPASS_ENDPOINTS) {
		try {
			const controller = new AbortController();
			const timer = setTimeout(() => controller.abort(), timeoutMs);
			const res = await fetch(endpoint, {
				method: 'POST',
				body: new URLSearchParams({ data: query }),
				headers: { 'User-Agent': USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded' },
				signal: controller.signal,
			});
			clearTimeout(timer);
			const text = await res.text();
			if (!res.ok || text.trim().startsWith('<')) {
				throw new Error(`Overpass endpoint ${endpoint} returned an error (HTTP ${res.status})`);
			}
			const json = JSON.parse(text) as { elements: OverpassElement[] };
			return json.elements;
		} catch (err) {
			lastErr = err;
			continue;
		}
	}
	throw new Error(`All Overpass endpoints failed. Last error: ${lastErr}`);
}

/**
 * Fetches every OpenStreetMap node tagged surveillance:type=ALPR within a
 * bounding box — this is the same public, crowdsourced dataset DeFlock
 * itself is built on (volunteers survey real cameras and tag them in OSM).
 * Real camera geography, not synthetic — only trip generation downstream
 * of this is synthetic.
 */
export async function fetchAlprCameras(bbox: BoundingBox): Promise<AlprCamera[]> {
	const query = `[out:json][timeout:60];\nnode["surveillance:type"="ALPR"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});\nout body;`;
	const elements = await runOverpassQuery(query, 65000);
	return elements.map((el) => ({
		id: el.id,
		lat: el.lat!,
		lon: el.lon!,
		manufacturer: el.tags?.manufacturer ?? null,
		direction: el.tags?.direction ?? null,
		zone: el.tags?.['surveillance:zone'] ?? null,
	}));
}

export interface RoadNetwork {
	nodes: { id: number; lat: number; lon: number }[];
	ways: { id: number; nodeIds: number[] }[];
}

/**
 * Fetches the arterial road network (motorway through tertiary, no
 * residential side streets) within a bounding box — real street topology
 * for routing synthetic trips over, instead of straight lines. Scoped to
 * arterials both to keep the graph a manageable size for repeated
 * shortest-path queries, and because ALPR cameras concentrate on
 * arterial roads/chokepoints in the first place.
 */
export async function fetchRoadNetwork(bbox: BoundingBox): Promise<RoadNetwork> {
	const highwayTypes = 'motorway|trunk|primary|secondary|tertiary|motorway_link|trunk_link|primary_link|secondary_link|tertiary_link';
	const query = `[out:json][timeout:120];\nway["highway"~"^(${highwayTypes})$"](${bbox.south},${bbox.west},${bbox.north},${bbox.east});\n(._;>;);\nout skel qt;`;
	const elements = await runOverpassQuery(query, 130000);

	const nodes: RoadNetwork['nodes'] = [];
	const ways: RoadNetwork['ways'] = [];
	for (const el of elements) {
		if (el.type === 'node') {
			nodes.push({ id: el.id, lat: el.lat!, lon: el.lon! });
		} else if (el.type === 'way' && el.nodes) {
			ways.push({ id: el.id, nodeIds: el.nodes });
		}
	}
	return { nodes, ways };
}
