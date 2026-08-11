import { existsSync, readdirSync, readFileSync, statSync } from 'node:fs';
import path from 'node:path';
import { PDFParse } from 'pdf-parse';
import type { RawDocument } from '../types.ts';
import type { FoiaMetadata } from '../compliance.ts';

export interface FoiaPdfRecord {
	doc: RawDocument;
	text: string;
	metadata: FoiaMetadata;
}

/**
 * Loads every PDF in `folder`. If a PDF has a same-named sidecar `.json`
 * file (e.g. `oakland-request-1.pdf` + `oakland-request-1.json`), it's used
 * as FOIA metadata (agency, state, requestDate, responseDate, subject) for
 * compliance-deadline analysis. Without a sidecar, the PDF is still ingested
 * and keyword-tagged, just without deadline compliance checking.
 */
export async function loadFoiaPdfs(folder: string): Promise<FoiaPdfRecord[]> {
	if (!existsSync(folder)) return [];

	const files = readdirSync(folder).filter((f) => f.toLowerCase().endsWith('.pdf'));
	const results: FoiaPdfRecord[] = [];

	for (const file of files) {
		const fullPath = path.join(folder, file);
		const buffer = readFileSync(fullPath);
		const parser = new PDFParse({ data: buffer });
		const { text } = await parser.getText();
		await parser.destroy();

		const metaPath = fullPath.replace(/\.pdf$/i, '.json');
		const metadata: FoiaMetadata = existsSync(metaPath) ? JSON.parse(readFileSync(metaPath, 'utf-8')) : {};
		const mtime = statSync(fullPath).mtime.toISOString();

		results.push({
			doc: {
				source: 'foia-pdf',
				externalId: file,
				title: metadata.requestSubject ?? file.replace(/\.pdf$/i, ''),
				body: metadata.agency ?? '',
				docType: 'foia-response',
				status: 'received',
				introDate: metadata.requestDate ?? null,
				agendaDate: metadata.responseDate ?? mtime.slice(0, 10),
				url: `file://${fullPath}`,
				raw: { file, textLength: text.length, metadata },
			},
			text,
			metadata,
		});
	}

	return results;
}
