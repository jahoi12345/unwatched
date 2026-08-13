import { Fragment, useEffect, useMemo, useRef, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { haversineMeters, type LatLon } from '../lib/geo';
import type { CameraDataset, SampleRoute, TrajectoryReport } from '../data/generated/types';

const AVG_SPEED_MPS = 11.2; // matches ingest/src/trajectory.ts's synthetic-timing assumption
const ANIMATION_MS = 6000;

const VEHICLE_COLORS = ['#3b82f6', '#ef4444', '#f0a868', '#a78bfa', '#22d3ee', '#f472b6', '#84cc16'];

function cumulativeDistances(path: LatLon[]): number[] {
	const cum = [0];
	for (let i = 1; i < path.length; i++) cum.push(cum[i - 1] + haversineMeters(path[i - 1], path[i]));
	return cum;
}

function pointAtDistance(path: LatLon[], cum: number[], targetMeters: number): LatLon {
	if (targetMeters <= 0) return path[0];
	const total = cum[cum.length - 1];
	if (targetMeters >= total) return path[path.length - 1];
	// Linear scan is fine — paths are capped at ~150 points.
	for (let i = 1; i < cum.length; i++) {
		if (cum[i] >= targetMeters) {
			const segStart = cum[i - 1];
			const segLen = cum[i] - segStart;
			const t = segLen > 0 ? (targetMeters - segStart) / segLen : 0;
			const a = path[i - 1];
			const b = path[i];
			return { lat: a.lat + (b.lat - a.lat) * t, lon: a.lon + (b.lon - a.lon) * t };
		}
	}
	return path[path.length - 1];
}

interface VehicleState {
	route: SampleRoute;
	cum: number[];
	durationSeconds: number;
	color: string;
}

export default function TrajectoryMap({ cameraData, report }: { cameraData: CameraDataset; report: TrajectoryReport }) {
	const cameras = cameraData.cameras ?? [];
	const routes = report.sampleRoutes ?? [];

	const [progress, setProgress] = useState(0); // 0..1 across the whole animation window
	const [playing, setPlaying] = useState(false);
	const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const startRef = useRef<number | null>(null);

	const vehicles: VehicleState[] = useMemo(
		() =>
			routes.map((route, i) => ({
				route,
				cum: cumulativeDistances(route.path),
				durationSeconds: route.totalMeters / AVG_SPEED_MPS,
				color: VEHICLE_COLORS[i % VEHICLE_COLORS.length],
			})),
		[routes],
	);

	const maxDurationSeconds = Math.max(1, ...vehicles.map((v) => v.durationSeconds));

	useEffect(() => {
		if (!playing) return;
		function tick() {
			const now = performance.now();
			if (startRef.current === null) startRef.current = now;
			const elapsed = now - startRef.current;
			const t = Math.min(1, elapsed / ANIMATION_MS);
			setProgress(t);
			if (t >= 1) {
				setPlaying(false);
				startRef.current = null;
				if (intervalRef.current) clearInterval(intervalRef.current);
			}
		}
		intervalRef.current = setInterval(tick, 50);
		tick();
		return () => {
			if (intervalRef.current) clearInterval(intervalRef.current);
		};
	}, [playing]);

	if (vehicles.length === 0) {
		return <p className="empty-state" style={{ display: 'block' }}>No sample routes to visualize yet.</p>;
	}

	function handlePlay() {
		setProgress(0);
		startRef.current = null;
		setPlaying(true);
	}

	// Global elapsed "synthetic seconds" — the slowest (longest) vehicle
	// finishes exactly as the animation ends; shorter trips finish earlier,
	// which is what real traffic looks like.
	const elapsedSeconds = progress * maxDurationSeconds;

	const allLats = vehicles.flatMap((v) => v.route.path.map((p) => p.lat));
	const allLons = vehicles.flatMap((v) => v.route.path.map((p) => p.lon));
	const center: [number, number] =
		allLats.length > 0
			? [(Math.min(...allLats) + Math.max(...allLats)) / 2, (Math.min(...allLons) + Math.max(...allLons)) / 2]
			: [37.8044, -122.2712];

	const capturedCameraKeys = new Set<string>();
	for (const v of vehicles) {
		const vehicleElapsed = Math.min(elapsedSeconds, v.durationSeconds);
		for (const hit of v.route.hits) {
			if (hit.approxSecondsIntoTrip <= vehicleElapsed) capturedCameraKeys.add(`${hit.lat},${hit.lon}`);
		}
	}

	return (
		<div>
			<div className="map-container">
				<MapContainer center={center} zoom={12} style={{ height: '460px', width: '100%' }}>
					<TileLayer
						attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
						url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
					/>
					{cameras.map((cam) => {
						const isHit = capturedCameraKeys.has(`${cam.lat},${cam.lon}`);
						return (
							<CircleMarker
								key={cam.id}
								center={[cam.lat, cam.lon]}
								radius={isHit ? 5 : 2}
								pathOptions={{
									color: isHit ? '#f0a868' : '#6ee7c4',
									fillColor: isHit ? '#f0a868' : '#6ee7c4',
									fillOpacity: isHit ? 0.95 : 0.3,
									weight: isHit ? 2 : 0,
								}}
							/>
						);
					})}

					{vehicles.map((v, i) => (
						<Polyline key={i} positions={v.route.path.map((p) => [p.lat, p.lon])} pathOptions={{ color: v.color, weight: 2, opacity: 0.5 }} />
					))}

					{vehicles.map((v, i) => {
						const vehicleProgressSeconds = Math.min(elapsedSeconds, v.durationSeconds);
						const distanceMeters = (vehicleProgressSeconds / v.durationSeconds) * v.route.totalMeters;
						const pos = pointAtDistance(v.route.path, v.cum, distanceMeters);
						const start = v.route.path[0];
						const end = v.route.path[v.route.path.length - 1];
						return (
							<Fragment key={i}>
								<CircleMarker center={[start.lat, start.lon]} radius={4} pathOptions={{ color: v.color, fillColor: v.color, fillOpacity: 0.5, weight: 1 }} />
								<CircleMarker center={[end.lat, end.lon]} radius={4} pathOptions={{ color: v.color, fillColor: '#fff', fillOpacity: 1, weight: 2 }} />
								{(playing || progress > 0) && (
									<CircleMarker center={[pos.lat, pos.lon]} radius={6} pathOptions={{ color: '#fff', fillColor: v.color, fillOpacity: 1, weight: 2 }} />
								)}
							</Fragment>
						);
					})}
				</MapContainer>
			</div>
			<div className="item-meta" style={{ marginTop: '12px' }}>
				<button className="chip" onClick={handlePlay} aria-pressed={playing}>
					{playing ? 'Simulating…' : `▶ Simulate traffic (${vehicles.length} vehicles)`}
				</button>
				<span className="badge">filled dot = destination</span>
				<span className="badge">orange = camera capture</span>
				{playing && <span className="badge">T+{Math.round(elapsedSeconds)}s</span>}
			</div>
		</div>
	);
}
