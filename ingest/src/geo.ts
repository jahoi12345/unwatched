export interface LatLon {
	lat: number;
	lon: number;
}

export function haversineMeters(a: LatLon, b: LatLon): number {
	const R = 6371000;
	const toRad = (d: number) => (d * Math.PI) / 180;
	const dLat = toRad(b.lat - a.lat);
	const dLon = toRad(b.lon - a.lon);
	const s = Math.sin(dLat / 2) ** 2 + Math.cos(toRad(a.lat)) * Math.cos(toRad(b.lat)) * Math.sin(dLon / 2) ** 2;
	return 2 * R * Math.asin(Math.sqrt(s));
}

/** Local equirectangular projection to meters, accurate enough at city scale (tens of km). */
export function projectMeters(point: LatLon, origin: LatLon): { x: number; y: number } {
	const x = (point.lon - origin.lon) * Math.cos((origin.lat * Math.PI) / 180) * 111320;
	const y = (point.lat - origin.lat) * 110540;
	return { x, y };
}

export function pointToSegmentDistanceMeters(p: LatLon, a: LatLon, b: LatLon): number {
	const origin = a;
	const P = projectMeters(p, origin);
	const A = { x: 0, y: 0 };
	const B = projectMeters(b, origin);
	const dx = B.x - A.x;
	const dy = B.y - A.y;
	const lengthSq = dx * dx + dy * dy;
	let t = lengthSq === 0 ? 0 : ((P.x - A.x) * dx + (P.y - A.y) * dy) / lengthSq;
	t = Math.max(0, Math.min(1, t));
	const cx = A.x + t * dx;
	const cy = A.y + t * dy;
	return Math.hypot(P.x - cx, P.y - cy);
}

export function randomPointInBbox(bbox: { south: number; west: number; north: number; east: number }): LatLon {
	return {
		lat: bbox.south + Math.random() * (bbox.north - bbox.south),
		lon: bbox.west + Math.random() * (bbox.east - bbox.west),
	};
}
