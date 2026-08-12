import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openDb, queryAllMatchedDocuments, type MatchedDocumentWithSourceRow } from './db.ts';
import { draftPublicComment } from './comment-drafter.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

function parseDays(argv: string[]): number {
	const arg = argv.find((a) => a.startsWith('--days='));
	return arg ? Number(arg.split('=')[1]) : 30;
}

function cityLabel(row: MatchedDocumentWithSourceRow): string {
	// source is "legistar:<slug>" — good enough as a label until we join back to cities.ts
	return row.source.replace(/^legistar:/, '');
}

function main() {
	const days = parseDays(process.argv.slice(2));
	const since = new Date();
	since.setDate(since.getDate() - days);
	const sinceIso = since.toISOString().slice(0, 10);

	const db = openDb(path.join(DATA_DIR, 'unwatched.db'));
	const rows = queryAllMatchedDocuments(db, { sinceAgendaDate: sinceIso });
	db.close();

	if (rows.length === 0) {
		console.log(`No surveillance-related agenda items found with an agenda date on/after ${sinceIso}.`);
		console.log('(Run `npm run batch` first if the database is empty, or widen --days.)');
		return;
	}

	const byCity = new Map<string, MatchedDocumentWithSourceRow[]>();
	for (const row of rows) {
		const city = cityLabel(row);
		if (!byCity.has(city)) byCity.set(city, []);
		byCity.get(city)!.push(row);
	}

	const jsonItems: unknown[] = [];
	const lines: string[] = [];
	lines.push(`# Surveillance Advocacy Digest`);
	lines.push('');
	lines.push(`Agenda items with a surveillance-related keyword match, agenda date on/after **${sinceIso}** (${days} days).`);
	lines.push(`${rows.length} item(s) across ${byCity.size} cities.`);
	lines.push('');

	for (const [city, cityRows] of [...byCity.entries()].sort((a, b) => b[1].length - a[1].length)) {
		lines.push(`## ${city} (${cityRows.length})`);
		lines.push('');
		for (const row of cityRows) {
			const drafted = draftPublicComment(row);
			lines.push(`### ${row.title.split('\n')[0].slice(0, 120)}`);
			lines.push('');
			lines.push(`- **Body:** ${row.body || 'unspecified'}`);
			lines.push(`- **Agenda date:** ${row.agenda_date?.slice(0, 10) ?? 'n/a'}`);
			lines.push(`- **Status:** ${row.status || 'unknown'}`);
			lines.push(`- **Matched keywords:** ${row.keywords}`);
			lines.push(`- **Link:** ${row.url}`);
			lines.push('');
			lines.push(`**Draft public comment** (${drafted.template}${drafted.vendor ? `, vendor: ${drafted.vendor}` : ''}${drafted.dollarAmount ? `, amount: ${drafted.dollarAmount}` : ''}):`);
			lines.push('');
			lines.push(`> ${drafted.text}`);
			lines.push('');

			jsonItems.push({
				city,
				title: row.title.split('\n')[0].slice(0, 200),
				body: row.body,
				agendaDate: row.agenda_date,
				status: row.status,
				keywords: row.keywords,
				url: row.url,
				draftedComment: drafted.text,
				commentTemplate: drafted.template,
				vendor: drafted.vendor,
				dollarAmount: drafted.dollarAmount,
			});
		}
	}

	mkdirSync(DATA_DIR, { recursive: true });
	const dateStr = new Date().toISOString().slice(0, 10);
	writeFileSync(path.join(DATA_DIR, `digest-${dateStr}.md`), lines.join('\n'));
	writeFileSync(
		path.join(DATA_DIR, 'digest-items.json'),
		JSON.stringify({ generatedAt: new Date().toISOString(), sinceDate: sinceIso, days, items: jsonItems }, null, 2),
	);

	console.log(`${rows.length} item(s) across ${byCity.size} cities.`);
	console.log(`Digest written to data/digest-${dateStr}.md and data/digest-items.json`);
}

main();
