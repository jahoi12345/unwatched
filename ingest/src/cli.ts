import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import { openDb, upsertDocument, replaceMatches, queryMatchedDocuments } from './db.ts';
import { findKeywordHits } from './keywords.ts';
import { fetchLegistarMatters } from './sources/legistar.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

function parseArgs(argv: string[]): { client: string; months: number } {
	const args = Object.fromEntries(
		argv
			.filter((a) => a.startsWith('--'))
			.map((a) => {
				const [key, value] = a.slice(2).split('=');
				return [key, value ?? 'true'];
			}),
	);

	const client = args.client;
	if (!client) {
		console.error('Usage: npm run ingest -- --client=<legistar-client-slug> [--months=24]');
		console.error('Example: npm run ingest -- --client=sfgov --months=24');
		process.exit(1);
	}

	return { client, months: args.months ? Number(args.months) : 24 };
}

async function main() {
	const { client, months } = parseArgs(process.argv.slice(2));
	const source = `legistar:${client}`;
	const sinceDate = new Date();
	sinceDate.setMonth(sinceDate.getMonth() - months);

	console.log(`Fetching matters for "${client}" since ${sinceDate.toISOString().slice(0, 10)}...`);
	const documents = await fetchLegistarMatters(client, sinceDate);
	console.log(`Fetched ${documents.length} matters. Scanning for surveillance-related keywords...`);

	mkdirSync(DATA_DIR, { recursive: true });
	const db = openDb(path.join(DATA_DIR, 'unwatched.db'));

	let matchedCount = 0;
	for (const doc of documents) {
		const hits = findKeywordHits(doc.title, doc.body);
		if (hits.length === 0) continue;
		matchedCount++;
		const docId = upsertDocument(db, doc);
		replaceMatches(db, docId, hits);
	}

	console.log(`${matchedCount} matter(s) matched a surveillance-related keyword.\n`);

	const rows = queryMatchedDocuments(db, source);
	for (const row of rows) {
		console.log(`— [${row.categories}] ${row.title}`);
		console.log(`  body: ${row.body || '(unspecified)'} | status: ${row.status || 'unknown'} | agenda: ${row.agenda_date?.slice(0, 10) ?? 'n/a'}`);
		console.log(`  keywords: ${row.keywords}`);
		console.log(`  ${row.url}\n`);
	}

	const exportPath = path.join(DATA_DIR, `${client}-surveillance-matters.json`);
	writeFileSync(exportPath, JSON.stringify(rows, null, 2));
	console.log(`Exported ${rows.length} matched record(s) to ${exportPath}`);

	db.close();
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
