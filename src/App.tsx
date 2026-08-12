import { Suspense, lazy } from 'react';
import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import Directory from './pages/Directory';

// Dashboard bundles ~130KB of JSON snapshots, and Exposure bundles Leaflet
// plus the camera dataset — split both out so browsing the directory (the
// landing page) doesn't pay for either.
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Exposure = lazy(() => import('./pages/Exposure'));

export default function App() {
	return (
		<BrowserRouter>
			<div className="wrap">
				<header className="site">
					<h1>Unwatched</h1>
					<p>
						A directory of tools for driving, mapping, and organizing against surveillance
						infrastructure — Flock/ALPR cameras, facial recognition, cell-site simulators, and the
						public records that document them.
					</p>
					<nav className="toplevel-nav">
						<NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
							Directory
						</NavLink>
						<NavLink to="/tools" className={({ isActive }) => (isActive ? 'active' : '')}>
							Our Tools
						</NavLink>
						<NavLink to="/exposure" className={({ isActive }) => (isActive ? 'active' : '')}>
							Privacy Check
						</NavLink>
					</nav>
				</header>

				<Suspense fallback={<main className="cat-desc">Loading…</main>}>
					<Routes>
						<Route path="/" element={<Directory />} />
						<Route path="/tools" element={<Dashboard />} />
						<Route path="/exposure" element={<Exposure />} />
					</Routes>
				</Suspense>

				<footer className="site">
					<p>
						Community-maintained directory. Not affiliated with, sponsored by, or endorsed by any
						tool listed here. Links go directly to each project's own site — review their privacy
						practices independently before use.
					</p>
				</footer>
			</div>
		</BrowserRouter>
	);
}
