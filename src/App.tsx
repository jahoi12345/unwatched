import { BrowserRouter, NavLink, Route, Routes } from 'react-router-dom';
import Directory from './pages/Directory';
import Dashboard from './pages/Dashboard';

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
					</nav>
				</header>

				<Routes>
					<Route path="/" element={<Directory />} />
					<Route path="/tools" element={<Dashboard />} />
				</Routes>

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
