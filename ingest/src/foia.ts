import { mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { openDb, upsertDocument, replaceMatches, replaceComplianceFlags, queryComplianceFlags } from './db.ts';
import { findKeywordHits } from './keywords.ts';
import { analyzeCompliance } from './compliance.ts';
import { loadFoiaPdfs } from './sources/foia-pdf.ts';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DATA_DIR = path.join(__dirname, '..', 'data');

function parseFolder(argv: string[]): string {
	const arg = argv.find((a) => a.startsWith('--folder='));
	return arg ? arg.split('=')[1] : path.join(__dirname, '..', 'foia-inbox');
}

async function main() {
	const folder = parseFolder(process.argv.slice(2));
	console.log(`Loading FOIA response PDFs from ${folder}...`);

	const records = await loadFoiaPdfs(folder);
	if (records.length === 0) {
		console.log('No PDFs found. Drop FOIA response PDFs (optionally with a same-named .json metadata sidecar) into that folder and re-run.');
		return;
	}
	console.log(`Loaded ${records.length} PDF(s).\n`);

	mkdirSync(DATA_DIR, { recursive: true });
	const db = openDb(path.join(DATA_DIR, 'unwatched.db'));

	const report: unknown[] = [];

	for (const { doc, text, metadata } of records) {
		const docId = upsertDocument(db, doc);

		const hits = findKeywordHits(text);
		replaceMatches(db, docId, hits);

		const compliance = analyzeCompliance(text, metadata);
		replaceComplianceFlags(
			db,
			docId,
			compliance.flags.map((flag, i) => ({ flag, detail: compliance.detail[i] ?? '' })),
		);

		console.log(`— ${doc.externalId}`);
		console.log(`  surveillance keywords: ${hits.length > 0 ? hits.map((h) => h.keyword).join(', ') : '(none found)'}`);
		console.log(`  compliance flags: ${compliance.flags.length > 0 ? compliance.flags.join(', ') : '(none)'}`);
		for (const d of compliance.detail) console.log(`    - ${d}`);
		console.log('');

		report.push({
			file: doc.externalId,
			title: doc.title,
			agency: metadata.agency ?? null,
			state: metadata.state ?? null,
			surveillanceKeywords: hits.map((h) => h.keyword),
			complianceFlags: compliance.flags,
			complianceDetail: compliance.detail,
		});
	}

	const allFlags = queryComplianceFlags(db, 'foia-pdf');
	const lateCount = allFlags.filter((f) => f.flag === 'late-response').length;
	const denialCount = allFlags.filter((f) => f.flag === 'full-denial' || f.flag === 'partial-denial').length;
	console.log(`${'='.repeat(50)}`);
	console.log(`${records.length} document(s) processed. ${lateCount} late response(s), ${denialCount} denial(s)/exemption(s) flagged.`);

	const outPath = path.join(DATA_DIR, 'foia-compliance-report.json');
	writeFileSync(outPath, JSON.stringify(report, null, 2));
	console.log(`Report written to ${outPath}`);

	db.close();
}

main().catch((err) => {
	console.error(err);
	process.exit(1);
});
