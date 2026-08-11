import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openDb, queryAllMatchedDocuments, queryStatusHistory, type MatchedDocumentWithSourceRow } from './db.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

function cityLabel(row: MatchedDocumentWithSourceRow): string {
	return row.source.replace(/^legistar:/, '');
}

function main() {
	const db = openDb(path.join(DATA_DIR, 'unwatched.db'));
	// keywordLike scoped to "Flock" catches both "Flock Safety" and "Flock Group" without
	// pulling in unrelated matches — it's a targeted LIKE against the matches.keyword column.
	const rows = queryAllMatchedDocuments(db, { keywordLike: 'Flock' });

	if (rows.length === 0) {
		console.log('No Flock-related agenda items found. (Run `npm run batch` first if the database is empty.)');
		db.close();
		return;
	}

	console.log(`${rows.length} Flock-related agenda item(s) found across ${new Set(rows.map(cityLabel)).size} cities.\n`);

	const report: unknown[] = [];

	for (const row of rows) {
		const history = queryStatusHistory(db, row.id);
		console.log(`— [${cityLabel(row)}] ${row.title.split('\n')[0].slice(0, 100)}`);
		console.log(`  current status: ${row.status ?? 'unknown'} | agenda: ${row.agenda_date?.slice(0, 10) ?? 'n/a'}`);
		if (history.length > 1) {
			console.log(`  status history: ${history.map((h) => `${h.status ?? 'unknown'} (${h.observed_at.slice(0, 10)})`).join(' -> ')}`);
		}
		console.log(`  ${row.url}\n`);

		report.push({
			city: cityLabel(row),
			title: row.title,
			currentStatus: row.status,
			agendaDate: row.agenda_date,
			url: row.url,
			statusHistory: history,
		});
	}

	db.close();

	mkdirSync(DATA_DIR, { recursive: true });
	const outPath = path.join(DATA_DIR, 'flock-transparency-report.json');
	writeFileSync(outPath, JSON.stringify(report, null, 2));
	console.log(`Report written to ${outPath}`);
}

main();
