import { useEffect, useRef, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import { haversineMeters, type LatLon } from '../lib/geo';
import type { CameraDataset, TrajectoryReport } from '../data/generated/types';

const AVG_SPEED_MPS = 11.2; // matches ingest/src/trajectory.ts's synthetic-timing assumption
const ANIMATION_MS = 5000;

function lerp(a: LatLon, b: LatLon, t: number): LatLon {
	return { lat: a.lat + (b.lat - a.lat) * t, lon: a.lon + (b.lon - a.lon) * t };
}

export default function TrajectoryMap({ cameraData, report }: { cameraData: CameraDataset; report: TrajectoryReport }) {
	const cameras = cameraData.cameras ?? [];
	const example = report.trips?.exampleReconstruction ?? null;

	const [progress, setProgress] = useState(0);
	const [playing, setPlaying] = useState(false);
	const rafRef = useRef<ReturnType<typeof setInterval> | null>(null);
	const startRef = useRef<number | null>(null);

	const totalRealSeconds = example ? haversineMeters(example.origin, example.destination) / AVG_SPEED_MPS : 0;

	// setInterval instead of requestAnimationFrame: rAF is throttled/paused by
	// the browser when the tab isn't visible, which would silently freeze the
	// simulation if a user switches away mid-animation. A plain interval keeps
	// advancing (wall-clock-based, so it still catches up correctly either way).
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
				if (rafRef.current) clearInterval(rafRef.current);
			}
		}
		rafRef.current = setInterval(tick, 50);
		tick();
		return () => {
			if (rafRef.current) clearInterval(rafRef.current);
		};
	}, [playing]);

	if (!example) {
		return <p className="empty-state" style={{ display: 'block' }}>No example trip to visualize yet.</p>;
	}

	function handlePlay() {
		setProgress(0);
		startRef.current = null;
		setPlaying(true);
	}

	const currentPos = lerp(example.origin, example.destination, progress);
	const elapsedRealSeconds = progress * totalRealSeconds;
	const center: [number, number] = [(example.origin.lat + example.destination.lat) / 2, (example.origin.lon + example.destination.lon) / 2];

	return (
		<div>
			<div className="map-container">
				<MapContainer center={center} zoom={13} style={{ height: '420px', width: '100%' }}>
					<TileLayer
						attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
						url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
					/>
					{cameras.map((cam) => (
						<CircleMarker
							key={cam.id}
							center={[cam.lat, cam.lon]}
							radius={2}
							pathOptions={{ color: '#6ee7c4', fillColor: '#6ee7c4', fillOpacity: 0.35, weight: 0 }}
						/>
					))}
					<Polyline
						positions={[
							[example.origin.lat, example.origin.lon],
							[example.destination.lat, example.destination.lon],
						]}
						pathOptions={{ color: '#888', dashArray: '4 6', weight: 2 }}
					/>
					{example.sequence.map((hit, i) => {
						const captured = elapsedRealSeconds >= hit.approxSecondsIntoTrip;
						return (
							<CircleMarker
								key={i}
								center={[hit.lat, hit.lon]}
								radius={captured ? 8 : 6}
								pathOptions={{
									color: captured ? '#f0a868' : '#f0a868',
									fillColor: captured ? '#f0a868' : 'transparent',
									fillOpacity: captured ? 0.95 : 0.4,
									weight: 2,
								}}
							/>
						);
					})}
					<CircleMarker
						center={[example.origin.lat, example.origin.lon]}
						radius={7}
						pathOptions={{ color: '#fff', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
					/>
					<CircleMarker
						center={[example.destination.lat, example.destination.lon]}
						radius={7}
						pathOptions={{ color: '#fff', fillColor: '#ef4444', fillOpacity: 1, weight: 2 }}
					/>
					{(playing || progress > 0) && (
						<CircleMarker
							center={[currentPos.lat, currentPos.lon]}
							radius={6}
							pathOptions={{ color: '#fff', fillColor: '#111', fillOpacity: 1, weight: 2 }}
						/>
					)}
				</MapContainer>
			</div>
			<div className="item-meta" style={{ marginTop: '12px' }}>
				<button className="chip" onClick={handlePlay} aria-pressed={playing}>
					{playing ? 'Simulating…' : '▶ Simulate this trip'}
				</button>
				<span className="badge">blue = start</span>
				<span className="badge">red = end</span>
				<span className="badge">orange = camera capture</span>
				{playing && <span className="badge">T+{Math.round(elapsedRealSeconds)}s</span>}
			</div>
		</div>
	);
}
