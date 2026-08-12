import { useMemo, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Polyline, useMapEvents } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import cameraDataRaw from '../data/generated/cameras.json';
import type { CameraDataset } from '../data/generated/types';
import { haversineMeters, pointToSegmentDistanceMeters, type LatLon } from '../lib/geo';

const cameraData = cameraDataRaw as CameraDataset;
const cameras = cameraData.cameras ?? [];
const CORRIDOR_METERS = 80;

function ClickHandler({ onClick }: { onClick: (p: LatLon) => void }) {
	useMapEvents({
		click(e) {
			onClick({ lat: e.latlng.lat, lon: e.latlng.lng });
		},
	});
	return null;
}

export default function Exposure() {
	const [pointA, setPointA] = useState<LatLon | null>(null);
	const [pointB, setPointB] = useState<LatLon | null>(null);

	function handleMapClick(p: LatLon) {
		if (!pointA || (pointA && pointB)) {
			setPointA(p);
			setPointB(null);
		} else {
			setPointB(p);
		}
	}

	function reset() {
		setPointA(null);
		setPointB(null);
	}

	const result = useMemo(() => {
		if (!pointA || !pointB) return null;
		const halfWidth = CORRIDOR_METERS / 2;
		const hitIds = new Set(
			cameras
				.filter((cam) => pointToSegmentDistanceMeters({ lat: cam.lat, lon: cam.lon }, pointA, pointB) <= halfWidth)
				.map((c) => c.id),
		);
		const tripLength = haversineMeters(pointA, pointB);
		return { hitIds, tripLength };
	}, [pointA, pointB]);

	const center: [number, number] = cameraData.bbox
		? [(cameraData.bbox.south + cameraData.bbox.north) / 2, (cameraData.bbox.west + cameraData.bbox.east) / 2]
		: [37.8044, -122.2712];

	return (
		<main>
			<p className="dashboard-note">
				Click two points on the map below — say, home and work — to see how many known ALPR cameras lie
				along a straight-line corridor between them. This runs entirely in your browser: nothing you click
				is sent anywhere, logged, or stored — reload the page and it's gone. Currently scoped to{' '}
				{cameraData.city ?? 'Oakland, CA'} ({cameras.length.toLocaleString()} real cameras, tagged in
				OpenStreetMap) — the same dataset behind the Trajectory Simulator.
			</p>

			<div className="exposure-layout">
				<div className="map-container">
					<MapContainer center={center} zoom={12} style={{ height: '520px', width: '100%' }}>
						<TileLayer
							attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
							url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
						/>
						<ClickHandler onClick={handleMapClick} />
						{cameras.map((cam) => {
							const isHit = result?.hitIds.has(cam.id) ?? false;
							return (
								<CircleMarker
									key={cam.id}
									center={[cam.lat, cam.lon]}
									radius={isHit ? 5 : 3}
									pathOptions={{
										color: isHit ? '#f0a868' : '#6ee7c4',
										fillColor: isHit ? '#f0a868' : '#6ee7c4',
										fillOpacity: isHit ? 0.9 : 0.5,
										weight: isHit ? 2 : 0,
									}}
								/>
							);
						})}
						{pointA && (
							<CircleMarker
								center={[pointA.lat, pointA.lon]}
								radius={9}
								pathOptions={{ color: '#fff', fillColor: '#3b82f6', fillOpacity: 1, weight: 2 }}
							/>
						)}
						{pointB && (
							<CircleMarker
								center={[pointB.lat, pointB.lon]}
								radius={9}
								pathOptions={{ color: '#fff', fillColor: '#ef4444', fillOpacity: 1, weight: 2 }}
							/>
						)}
						{pointA && pointB && (
							<Polyline
								positions={[
									[pointA.lat, pointA.lon],
									[pointB.lat, pointB.lon],
								]}
								pathOptions={{ color: '#888', dashArray: '4 6' }}
							/>
						)}
					</MapContainer>
				</div>

				<div className="exposure-results">
					<button className="chip" onClick={reset}>
						Reset points
					</button>

					{!pointA && <p className="cat-desc">Click the map to place your first point (e.g. home).</p>}
					{pointA && !pointB && <p className="cat-desc">Now click a second point (e.g. work).</p>}

					{result && (
						<>
							<div className="stat-row" style={{ gridTemplateColumns: '1fr 1fr' }}>
								<div className="stat-tile">
									<div className="value">{result.hitIds.size}</div>
									<div className="label">camera{result.hitIds.size === 1 ? '' : 's'} along this route</div>
								</div>
								<div className="stat-tile">
									<div className="value">{(result.tripLength / 1000).toFixed(1)} km</div>
									<div className="label">straight-line distance</div>
								</div>
							</div>
							<p className="cat-desc">
								{result.hitIds.size === 0
									? "No known cameras lie within this route's corridor — though OpenStreetMap's camera data is crowdsourced and incomplete, so this isn't a guarantee of privacy."
									: `A route between these two points would likely be logged by at least ${result.hitIds.size} automated license plate reader${result.hitIds.size === 1 ? '' : 's'}, each recording a plate, location, and timestamp as it passes.`}
							</p>
						</>
					)}

					<p className="dashboard-note" style={{ margin: '20px 0 0' }}>
						Method: straight line between your two points with an {CORRIDOR_METERS}m corridor, same as
						the Trajectory Simulator — a simplified stand-in for real street routing, explained on that
						page.
					</p>
				</div>
			</div>
		</main>
	);
}
