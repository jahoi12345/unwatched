import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { discoverAllCities } from './discover.ts';
import { fetchLegistarMatters } from './sources/legistar.ts';
import { findKeywordHits } from './keywords.ts';
import { openDb, upsertDocument, replaceMatches, insertRun, queryMatchedDocuments } from './db.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

function parseMonths(argv: string[]): number {
	const arg = argv.find((a) => a.startsWith('--months='));
	return arg ? Number(arg.split('=')[1]) : 24;
}

async function main() {
	const months = parseMonths(process.argv.slice(2));
	mkdirSync(DATA_DIR, { recursive: true });
	const db = openDb(path.join(DATA_DIR, 'unwatched.db'));

	const discovery = await discoverAllCities();
	const runnable = discovery.filter((r) => r.status !== 'not-found');

	console.log(`\n${runnable.length} of ${discovery.length} target cities have a resolvable Legistar client. Ingesting each...\n`);

	const sinceDate = new Date();
	sinceDate.setMonth(sinceDate.getMonth() - months);

	let totalMatters = 0;
	let totalMatches = 0;
	const combined: unknown[] = [];

	for (const city of runnable) {
		const startedAt = new Date().toISOString();
		const slug = city.slug!;
		const source = `legistar:${slug}`;

		try {
			const { documents, pagesFetched } = await fetchLegistarMatters(slug, sinceDate);

			let matched = 0;
			for (const doc of documents) {
				const hits = findKeywordHits(doc.title, doc.body);
				if (hits.length === 0) continue;
				matched++;
				const docId = upsertDocument(db, doc);
				replaceMatches(db, docId, hits);
			}

			totalMatters += documents.length;
			totalMatches += matched;

			insertRun(db, {
				source,
				city: city.name,
				state: city.state,
				slug,
				clientStatus: city.status,
				monthsLookback: months,
				pagesFetched,
				mattersFetched: documents.length,
				matchesFound: matched,
				error: null,
				startedAt,
				finishedAt: new Date().toISOString(),
			});

			const rows = queryMatchedDocuments(db, source);
			combined.push(...rows.map((r) => ({ city: city.name, state: city.state, slug, clientStatus: city.status, ...r })));

			console.log(
				`${city.status === 'stale' ? '~' : '✓'} ${city.name}, ${city.state} (${slug}): ${documents.length} matters, ${pagesFetched} page(s), ${matched} matched`,
			);
		} catch (err) {
			insertRun(db, {
				source,
				city: city.name,
				state: city.state,
				slug,
				clientStatus: city.status,
				monthsLookback: months,
				pagesFetched: null,
				mattersFetched: null,
				matchesFound: null,
				error: err instanceof Error ? err.message : String(err),
				startedAt,
				finishedAt: new Date().toISOString(),
			});
			console.log(`✗ ${city.name}, ${city.state} (${slug}): ERROR — ${err instanceof Error ? err.message : err}`);
		}
	}

	const notFound = discovery.filter((r) => r.status === 'not-found');
	console.log(`\n${'='.repeat(60)}`);
	console.log(`Batch complete: ${totalMatters} matters fetched, ${totalMatches} matched across ${runnable.length} cities.`);
	console.log(`${notFound.length} cities had no resolvable Legistar client (not covered by this source):`);
	for (const c of notFound) console.log(`  - ${c.name}, ${c.state}`);

	const summaryPath = path.join(DATA_DIR, 'batch-summary.json');
	writeFileSync(
		summaryPath,
		JSON.stringify(
			{
				ranAt: new Date().toISOString(),
				monthsLookback: months,
				totalCitiesTargeted: discovery.length,
				citiesIngested: runnable.length,
				citiesNotFound: notFound.map((c) => ({ name: c.name, state: c.state, triedCandidates: c.triedCandidates })),
				totalMattersFetched: totalMatters,
				totalMatchesFound: totalMatches,
			},
			null,
			2,
		),
	);
	console.log(`\nSummary written to ${summaryPath}`);

	const combinedPath = path.join(DATA_DIR, 'all-cities-surveillance-matters.json');
	writeFileSync(combinedPath, JSON.stringify(combined, null, 2));
	console.log(`Combined matched-record export written to ${combinedPath}`);

	db.close();
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
