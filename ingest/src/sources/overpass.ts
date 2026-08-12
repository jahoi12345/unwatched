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
	id: number;
	lat: number;
	lon: number;
	tags?: Record<string, string>;
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

	let lastErr: unknown;
	for (const endpoint of OVERPASS_ENDPOINTS) {
		try {
			const res = await fetch(endpoint, {
				method: 'POST',
				body: new URLSearchParams({ data: query }),
				headers: { 'User-Agent': USER_AGENT, 'Content-Type': 'application/x-www-form-urlencoded' },
			});
			const text = await res.text();
			if (!res.ok || text.trim().startsWith('<')) {
				throw new Error(`Overpass endpoint ${endpoint} returned an error (HTTP ${res.status})`);
			}
			const json = JSON.parse(text) as { elements: OverpassElement[] };
			return json.elements.map((el) => ({
				id: el.id,
				lat: el.lat,
				lon: el.lon,
				manufacturer: el.tags?.manufacturer ?? null,
				direction: el.tags?.direction ?? null,
				zone: el.tags?.['surveillance:zone'] ?? null,
			}));
		} catch (err) {
			lastErr = err;
			continue;
		}
	}
	throw new Error(`All Overpass endpoints failed. Last error: ${lastErr}`);
}
