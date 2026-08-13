import { useMemo, useState } from 'react';
import coverageRaw from '../data/generated/coverage-summary.json';
import flockRaw from '../data/generated/flock-transparency.json';
import digestRaw from '../data/generated/digest.json';
import foiaRaw from '../data/generated/foia-compliance.json';
import permitsRaw from '../data/generated/permits.json';
import trajectoryRaw from '../data/generated/trajectory.json';
import camerasRaw from '../data/generated/cameras.json';
import TrajectoryMap from '../components/TrajectoryMap';
import type {
	CameraDataset,
	CoverageSummary,
	DigestReport,
	FlockTransparencyItem,
	FoiaComplianceItem,
	PermitItem,
	TrajectoryReport,
} from '../data/generated/types';

const coverage = coverageRaw as CoverageSummary;
const flockItems = flockRaw as FlockTransparencyItem[];
const digest = digestRaw as DigestReport;
const foiaItems = foiaRaw as FoiaComplianceItem[];
const permitItems = permitsRaw as PermitItem[];
const trajectory = trajectoryRaw as TrajectoryReport;
const cameraData = camerasRaw as CameraDataset;

type Tab = 'overview' | 'digest' | 'flock' | 'foia' | 'trajectory' | 'permits';

const TABS: { id: Tab; label: string }[] = [
	{ id: 'overview', label: 'Coverage' },
	{ id: 'digest', label: 'Advocacy Digest' },
	{ id: 'flock', label: 'Flock Monitor' },
	{ id: 'foia', label: 'FOIA Compliance' },
	{ id: 'trajectory', label: 'Trajectory Simulator' },
	{ id: 'permits', label: 'Permit Filings' },
];

function fmtDate(iso: string | null | undefined): string {
	return iso ? iso.slice(0, 10) : 'n/a';
}

export default function Dashboard() {
	const [tab, setTab] = useState<Tab>('overview');
	const [query, setQuery] = useState('');
	const [cityFilter, setCityFilter] = useState('all');

	const normalizedQuery = query.trim().toLowerCase();

	const digestCities = useMemo(() => {
		const cities = new Set((digest.items ?? []).map((item) => item.city));
		return [...cities].sort();
	}, []);

	const filteredDigestItems = useMemo(() => {
		const items = digest.items ?? [];
		return items.filter((item) => {
			if (cityFilter !== 'all' && item.city !== cityFilter) return false;
			if (normalizedQuery === '') return true;
			return (
				item.title.toLowerCase().includes(normalizedQuery) ||
				item.city.toLowerCase().includes(normalizedQuery) ||
				item.keywords.toLowerCase().includes(normalizedQuery) ||
				(item.vendor ?? '').toLowerCase().includes(normalizedQuery)
			);
		});
	}, [normalizedQuery, cityFilter]);

	return (
		<>
			<p className="dashboard-note">
				This page is a static snapshot of the ingestion tools' output (last synced{' '}
				{fmtDate(coverage.ranAt)}), not a live feed. Regenerate it locally with{' '}
				<code>npm run batch</code> / <code>npm run digest</code> in <code>ingest/</code>, then{' '}
				<code>npm run sync-data</code> at the repo root.
			</p>

			<div className="subtabs">
				{TABS.map((t) => (
					<button key={t.id} className="chip" aria-pressed={tab === t.id} onClick={() => setTab(t.id)}>
						{t.label}
					</button>
				))}
			</div>

			{tab === 'overview' && <Overview />}
			{tab === 'digest' && (
				<DigestTab
					items={filteredDigestItems}
					query={query}
					onQueryChange={setQuery}
					total={digest.items?.length ?? 0}
					cities={digestCities}
					cityFilter={cityFilter}
					onCityFilterChange={setCityFilter}
				/>
			)}
			{tab === 'flock' && <FlockTab items={flockItems} />}
			{tab === 'foia' && <FoiaTab items={foiaItems} />}
			{tab === 'trajectory' && <TrajectoryTab report={trajectory} />}
			{tab === 'permits' && <PermitsTab items={permitItems} />}
		</>
	);
}

function Overview() {
	return (
		<main>
			<div className="stat-row">
				<div className="stat-tile">
					<div className="value">
						{coverage.citiesIngested ?? 0}/{coverage.totalCitiesTargeted ?? 0}
					</div>
					<div className="label">cities with a resolvable records source</div>
				</div>
				<div className="stat-tile">
					<div className="value">{(coverage.totalMattersFetched ?? 0).toLocaleString()}</div>
					<div className="label">agenda items scanned</div>
				</div>
				<div className="stat-tile">
					<div className="value">{(coverage.totalMatchesFound ?? 0).toLocaleString()}</div>
					<div className="label">surveillance-related matches</div>
				</div>
				<div className="stat-tile">
					<div className="value">{flockItems.length}</div>
					<div className="label">Flock-specific items tracked</div>
				</div>
			</div>

			<section className="category-block">
				<h2>Cities not yet covered</h2>
				<p className="cat-desc">
					These cities didn't resolve to a Legistar client under any guessed slug — they likely run a
					different records system, or a differently-hosted Legistar instance. Not a silent gap: every
					one of these was actually attempted.
				</p>
				<div className="not-found-list">
					{(coverage.citiesNotFound ?? []).map((c) => (
						<div key={c.name}>
							{c.name}, {c.state}
						</div>
					))}
				</div>
			</section>
		</main>
	);
}

function DigestTab({
	items,
	query,
	onQueryChange,
	total,
	cities,
	cityFilter,
	onCityFilterChange,
}: {
	items: NonNullable<DigestReport['items']>;
	query: string;
	onQueryChange: (q: string) => void;
	total: number;
	cities: string[];
	cityFilter: string;
	onCityFilterChange: (c: string) => void;
}) {
	return (
		<main>
			<div className="controls" style={{ borderBottom: 'none', padding: '0 0 12px' }}>
				<input
					type="search"
					aria-label="Search advocacy digest"
					placeholder="Search by city, vendor, or keyword…"
					value={query}
					onChange={(e) => onQueryChange(e.target.value)}
				/>
			</div>
			<div className="subtabs" style={{ margin: '0 0 16px' }}>
				<button className="chip" aria-pressed={cityFilter === 'all'} onClick={() => onCityFilterChange('all')}>
					All cities
				</button>
				{cities.map((city) => (
					<button
						key={city}
						className="chip"
						aria-pressed={cityFilter === city}
						onClick={() => onCityFilterChange(city)}
					>
						{city}
					</button>
				))}
			</div>
			<p className="cat-desc" style={{ marginTop: '-4px' }}>
				Showing {items.length} of {total} matched agenda items, each with an auto-drafted public comment.
			</p>
			<div className="item-list">
				{items.map((item, i) => (
					<article className="item-card" key={i}>
						<h3 className="item-title">
							{item.url ? (
								<a href={item.url} target="_blank" rel="noopener noreferrer">
									{item.title}
								</a>
							) : (
								item.title
							)}
						</h3>
						<div className="item-meta">
							<span className="badge">{item.city}</span>
							<span className="badge">{item.status ?? 'unknown'}</span>
							<span className="badge">{fmtDate(item.agendaDate)}</span>
							{item.vendor && <span className="badge">{item.vendor}</span>}
							{item.dollarAmount && <span className="badge">{item.dollarAmount}</span>}
						</div>
						<details className="draft-comment">
							<summary>Draft public comment ({item.commentTemplate})</summary>
							<blockquote>{item.draftedComment}</blockquote>
						</details>
					</article>
				))}
				{items.length === 0 && <p className="empty-state" style={{ display: 'block' }}>No items match your search.</p>}
			</div>
		</main>
	);
}

function FlockTab({ items }: { items: FlockTransparencyItem[] }) {
	return (
		<main>
			<p className="cat-desc">
				Flock Safety / Flock Group matches across every ingested city, with status history — this builds
				up over time as <code>npm run batch</code> is re-run periodically and observes status changes.
			</p>
			<div className="item-list">
				{items.map((item, i) => (
					<article className="item-card" key={i}>
						<h3 className="item-title">
							{item.url ? (
								<a href={item.url} target="_blank" rel="noopener noreferrer">
									{item.title.split('\n')[0]}
								</a>
							) : (
								item.title.split('\n')[0]
							)}
						</h3>
						<div className="item-meta">
							<span className="badge">{item.city}</span>
							<span className="badge">{item.currentStatus ?? 'unknown'}</span>
							<span className="badge">{fmtDate(item.agendaDate)}</span>
						</div>
						{item.statusHistory.length > 1 && (
							<div className="status-history">
								{item.statusHistory.map((h, idx) => (
									<span key={idx}>
										{idx > 0 && <span className="sep">→ </span>}
										{h.status ?? 'unknown'} ({fmtDate(h.observed_at)})
									</span>
								))}
							</div>
						)}
					</article>
				))}
				{items.length === 0 && <p className="empty-state" style={{ display: 'block' }}>No Flock-related items found yet.</p>}
			</div>
		</main>
	);
}

function FoiaTab({ items }: { items: FoiaComplianceItem[] }) {
	return (
		<main>
			<p className="cat-desc">
				FOIA/public-records responses processed for surveillance-tech mentions and compliance issues
				(redactions, denials, late responses against state statutory deadlines).
			</p>
			<div className="item-list">
				{items.map((item, i) => (
					<article className="item-card" key={i}>
						<h3 className="item-title">{item.title}</h3>
						<div className="item-meta">
							{item.agency && <span className="badge">{item.agency}</span>}
							{item.state && <span className="badge">{item.state}</span>}
							{item.complianceFlags.map((flag) => (
								<span
									className={`badge ${flag.includes('denial') || flag === 'late-response' || flag === 'fee-waiver-denied' ? 'warn' : ''}`}
									key={flag}
								>
									{flag}
								</span>
							))}
						</div>
						{item.complianceDetail.length > 0 && (
							<ul style={{ margin: '4px 0 0', paddingLeft: '18px', color: 'var(--text-dim)', fontSize: '0.82rem' }}>
								{item.complianceDetail.map((d, idx) => (
									<li key={idx}>{d}</li>
								))}
							</ul>
						)}
						{item.surveillanceKeywords.length > 0 && (
							<div className="item-meta" style={{ marginTop: '8px' }}>
								{item.surveillanceKeywords.map((k) => (
									<span className="badge" key={k}>
										{k}
									</span>
								))}
							</div>
						)}
					</article>
				))}
				{items.length === 0 && (
					<p className="empty-state" style={{ display: 'block' }}>
						No FOIA responses processed yet — drop PDFs into <code>ingest/foia-inbox/</code> and run{' '}
						<code>npm run foia</code>.
					</p>
				)}
			</div>
		</main>
	);
}

function TrajectoryTab({ report }: { report: TrajectoryReport }) {
	if (!report.coverage || !report.trips) {
		return (
			<main>
				<p className="empty-state" style={{ display: 'block' }}>
					No trajectory report yet — run <code>npm run trajectory -- --city="City, State"</code> in{' '}
					<code>ingest/</code>.
				</p>
			</main>
		);
	}

	const { coverage: cov, trips } = report;

	return (
		<main>
			<p className="cat-desc">
				Synthetic trips routed over {report.city}'s real arterial street network
				{report.roadNetwork ? ` (${report.roadNetwork.nodeCount.toLocaleString()} road nodes)` : ''}, checked
				against real, OpenStreetMap-tagged ALPR camera locations ({(report.cameraCount ?? 0).toLocaleString()}{' '}
				cameras). Built to give city councils and advocates a quantifiable answer to "how much of this city is
				actually covered" — see methodology below for exactly what's real data versus simulated.
			</p>
			<div className="stat-row">
				<div className="stat-tile">
					<div className="value">{cov.coveragePercent.toFixed(1)}%</div>
					<div className="label">
						of arterial road length within {cov.radiusMeters}m of a known camera
					</div>
				</div>
				<div className="stat-tile">
					<div className="value">{trips.captureRatePercent.toFixed(1)}%</div>
					<div className="label">of {trips.count.toLocaleString()} synthetic trips passed a camera</div>
				</div>
				<div className="stat-tile">
					<div className="value">{trips.avgHitsPerCapturedTrip.toFixed(1)}</div>
					<div className="label">avg. camera hits per captured trip</div>
				</div>
			</div>

			{trips.exampleReconstruction && (
				<section className="category-block">
					<h2>Example reconstruction</h2>
					<p className="cat-desc">
						One synthetic trip, {trips.exampleReconstruction.hitCount} camera hits — showing how a
						sequence of real camera positions alone reconstructs an approximate timed route. Press
						"Simulate" to watch it play out.
					</p>
					<TrajectoryMap cameraData={cameraData} report={report} />
					<div className="item-list" style={{ marginTop: '16px' }}>
						{trips.exampleReconstruction.sequence.map((hit, i) => (
							<div className="item-card" key={i}>
								<div className="item-meta">
									<span className="badge">T+{hit.approxSecondsIntoTrip}s</span>
									<span className="badge">
										{hit.lat.toFixed(5)}, {hit.lon.toFixed(5)}
									</span>
									{hit.manufacturer && <span className="badge">{hit.manufacturer}</span>}
								</div>
							</div>
						))}
					</div>
				</section>
			)}

			<section className="category-block">
				<h2>Methodology</h2>
				<ul style={{ color: 'var(--text-dim)', fontSize: '0.85rem', lineHeight: 1.7, paddingLeft: '18px' }}>
					{(report.methodology ?? []).map((line, i) => (
						<li key={i}>{line}</li>
					))}
				</ul>
			</section>
		</main>
	);
}

function PermitsTab({ items }: { items: PermitItem[] }) {
	return (
		<main>
			<p className="cat-desc">
				Public building/electrical permits whose filed description mentions surveillance hardware —
				this is how private, non-governmental camera deployments (businesses, parking lots, HOAs) show up
				in public records, since there's no police purchase order to FOIA for them.
			</p>
			<div className="item-list">
				{items.map((item, i) => (
					<article className="item-card" key={i}>
						<h3 className="item-title">
							{item.url ? (
								<a href={item.url} target="_blank" rel="noopener noreferrer">
									{item.title}
								</a>
							) : (
								item.title
							)}
						</h3>
						<div className="item-meta">
							<span className="badge">{item.city}</span>
							<span className="badge">{item.status ?? 'unknown'}</span>
							<span className="badge">{fmtDate(item.intro_date)}</span>
							{item.body && <span className="badge">{item.body}</span>}
						</div>
					</article>
				))}
				{items.length === 0 && (
					<p className="empty-state" style={{ display: 'block' }}>
						No permits processed yet — run <code>npm run permits</code> in <code>ingest/</code>.
					</p>
				)}
			</div>
		</main>
	);
}
