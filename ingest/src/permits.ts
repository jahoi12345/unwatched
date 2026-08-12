import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openDb, upsertDocument, replaceMatches, queryMatchedDocuments } from './db.ts';
import { findKeywordHits } from './keywords.ts';
import { PERMIT_SOURCES, fetchSurveillancePermits } from './sources/socrata-permits.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

async function main() {
	mkdirSync(DATA_DIR, { recursive: true });
	const db = openDb(path.join(DATA_DIR, 'unwatched.db'));

	let totalFetched = 0;
	let totalTagged = 0;
	const combined: unknown[] = [];

	for (const config of PERMIT_SOURCES) {
		console.log(`Fetching surveillance-related permits from ${config.host} (${config.citySlug})...`);
		const documents = await fetchSurveillancePermits(config);
		totalFetched += documents.length;
		console.log(`Found ${documents.length} permit(s) matching surveillance-hardware keywords.`);

		for (const doc of documents) {
			const hits = findKeywordHits(doc.title);
			const docId = upsertDocument(db, doc);
			replaceMatches(db, docId, hits.length > 0 ? hits : [{ keyword: 'surveillance permit', category: 'generic-surveillance' }]);
			totalTagged++;
		}

		const rows = queryMatchedDocuments(db, `permits:${config.citySlug}`);
		for (const row of rows) {
			console.log(`— [${config.citySlug}] ${row.title.slice(0, 100)}`);
			console.log(`  address: ${row.body} | status: ${row.status} | filed: ${row.intro_date?.slice(0, 10) ?? 'n/a'}`);
			console.log(`  keywords: ${row.keywords}\n`);
			combined.push({ city: config.citySlug, ...row });
		}
	}

	console.log(`${'='.repeat(50)}`);
	console.log(`${totalFetched} permit(s) fetched across ${PERMIT_SOURCES.length} source(s), ${totalTagged} stored.`);

	const outPath = path.join(DATA_DIR, 'surveillance-permits.json');
	writeFileSync(outPath, JSON.stringify(combined, null, 2));
	console.log(`Report written to ${outPath}`);

	db.close();
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
