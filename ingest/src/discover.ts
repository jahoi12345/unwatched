import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { TOP_50_CITIES } from './cities.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

const LIVE_THRESHOLD_MONTHS = 6;

export type ClientStatus = 'live' | 'stale' | 'not-found';

export interface DiscoveryResult {
	name: string;
	state: string;
	rank: number;
	status: ClientStatus;
	slug: string | null;
	mostRecentMatterDate: string | null;
	triedCandidates: string[];
}

interface ProbeOutcome {
	ok: boolean;
	mostRecentDate: string | null;
}

async function probe(slug: string): Promise<ProbeOutcome> {
	const url = `https://webapi.legistar.com/v1/${slug}/matters?$orderby=MatterId%20desc&$top=1`;
	try {
		const res = await fetch(url, { headers: { Accept: 'application/json' } });
		if (!res.ok) return { ok: false, mostRecentDate: null };
		const body = await res.text();
		const data = JSON.parse(body);
		if (!Array.isArray(data) || data.length === 0) return { ok: false, mostRecentDate: null };
		return { ok: true, mostRecentDate: data[0]?.MatterIntroDate ?? null };
	} catch {
		return { ok: false, mostRecentDate: null };
	}
}

function isLive(dateStr: string | null): boolean {
	if (!dateStr) return false;
	const date = new Date(dateStr);
	const cutoff = new Date();
	cutoff.setMonth(cutoff.getMonth() - LIVE_THRESHOLD_MONTHS);
	return date >= cutoff;
}

function sleep(ms: number): Promise<void> {
	return new Promise((resolve) => setTimeout(resolve, ms));
}

async function discoverCity(city: (typeof TOP_50_CITIES)[number]): Promise<DiscoveryResult> {
	let bestStaleSlug: string | null = null;
	let bestStaleDate: string | null = null;

	for (const slug of city.candidates) {
		const outcome = await probe(slug);
		await sleep(120);
		if (!outcome.ok) continue;

		if (isLive(outcome.mostRecentDate)) {
			return {
				name: city.name,
				state: city.state,
				rank: city.rank,
				status: 'live',
				slug,
				mostRecentMatterDate: outcome.mostRecentDate,
				triedCandidates: city.candidates,
			};
		}
		if (!bestStaleSlug) {
			bestStaleSlug = slug;
			bestStaleDate = outcome.mostRecentDate;
		}
	}

	if (bestStaleSlug) {
		return {
			name: city.name,
			state: city.state,
			rank: city.rank,
			status: 'stale',
			slug: bestStaleSlug,
			mostRecentMatterDate: bestStaleDate,
			triedCandidates: city.candidates,
		};
	}

	return {
		name: city.name,
		state: city.state,
		rank: city.rank,
		status: 'not-found',
		slug: null,
		mostRecentMatterDate: null,
		triedCandidates: city.candidates,
	};
}

export async function discoverAllCities(opts: { log?: boolean } = {}): Promise<DiscoveryResult[]> {
	const log = opts.log ?? true;
	if (log) {
		console.log(`Probing ${TOP_50_CITIES.length} cities for Legistar clients (candidates tried in order, first live match wins)...\n`);
	}

	const results: DiscoveryResult[] = [];
	for (const city of TOP_50_CITIES) {
		const result = await discoverCity(city);
		results.push(result);
		if (log) {
			const marker = result.status === 'live' ? '✓ live ' : result.status === 'stale' ? '~ stale' : '✗ none ';
			console.log(
				`${marker} #${String(city.rank).padStart(2, '0')} ${city.name}, ${city.state}`.padEnd(45) +
					(result.slug ? `slug=${result.slug}` : '(no Legistar client found)') +
					(result.mostRecentMatterDate ? ` (most recent matter: ${result.mostRecentMatterDate.slice(0, 10)})` : ''),
			);
		}
	}
	return results;
}

async function main() {
	const results = await discoverAllCities();

	const live = results.filter((r) => r.status === 'live');
	const stale = results.filter((r) => r.status === 'stale');
	const notFound = results.filter((r) => r.status === 'not-found');

	console.log(`\n${live.length}/${results.length} live, ${stale.length}/${results.length} stale, ${notFound.length}/${results.length} not found.`);

	mkdirSync(DATA_DIR, { recursive: true });
	const reportPath = path.join(DATA_DIR, 'discovery-report.json');
	writeFileSync(reportPath, JSON.stringify(results, null, 2));
	console.log(`\nFull report written to ${reportPath}`);
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
