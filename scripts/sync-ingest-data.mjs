#!/usr/bin/env node
// Copies generated ingest/ output into src/data/generated/ so the frontend
// can statically import it. Run after `npm run batch` / `npm run digest` /
// `npm run flock-monitor` / `npm run foia` inside ingest/ to publish fresh
// data to the site. The site always shows a snapshot as of the last sync,
// not live data — that's the point: it's a static site, not a backend.
import { copyFileSync, existsSync, mkdirSync, writeFileSync } from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const root = path.join(__dirname, '..');
const ingestData = path.join(root, 'ingest', 'data');
const outDir = path.join(root, 'src', 'data', 'generated');

mkdirSync(outDir, { recursive: true });

const FILES = [
	{ from: 'batch-summary.json', to: 'coverage-summary.json', required: false },
	{ from: 'all-cities-surveillance-matters.json', to: 'surveillance-matters.json', required: false },
	{ from: 'flock-transparency-report.json', to: 'flock-transparency.json', required: false },
	{ from: 'digest-items.json', to: 'digest.json', required: false },
	{ from: 'foia-compliance-report.json', to: 'foia-compliance.json', required: false },
];

let syncedAt = new Date().toISOString();
let copied = 0;

for (const file of FILES) {
	const src = path.join(ingestData, file.from);
	const dest = path.join(outDir, file.to);
	if (existsSync(src)) {
		copyFileSync(src, dest);
		copied++;
		console.log(`✓ ${file.from} -> src/data/generated/${file.to}`);
	} else {
		// Write an empty-but-valid placeholder so the frontend doesn't fail to import.
		const isArrayShaped = file.to === 'surveillance-matters.json' || file.to === 'flock-transparency.json' || file.to === 'foia-compliance.json';
		writeFileSync(dest, isArrayShaped ? '[]' : '{}');
		console.log(`- ${file.from} not found (run the corresponding ingest script first) — wrote empty placeholder`);
	}
}

writeFileSync(path.join(outDir, 'synced-at.json'), JSON.stringify({ syncedAt }, null, 2));
console.log(`\n${copied}/${FILES.length} file(s) synced at ${syncedAt}`);
