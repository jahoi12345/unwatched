import { DatabaseSync } from 'node:sqlite';
import type { KeywordHit, RawDocument } from './types.ts';

const SCHEMA = `
CREATE TABLE IF NOT EXISTS documents (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	source TEXT NOT NULL,
	external_id TEXT NOT NULL,
	title TEXT NOT NULL,
	body TEXT,
	doc_type TEXT,
	status TEXT,
	intro_date TEXT,
	agenda_date TEXT,
	url TEXT,
	raw_json TEXT,
	ingested_at TEXT NOT NULL,
	UNIQUE(source, external_id)
);

CREATE TABLE IF NOT EXISTS matches (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
	keyword TEXT NOT NULL,
	category TEXT NOT NULL,
	UNIQUE(document_id, keyword)
);

CREATE TABLE IF NOT EXISTS status_history (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
	status TEXT,
	observed_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS compliance_flags (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	document_id INTEGER NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
	flag TEXT NOT NULL,
	detail TEXT,
	UNIQUE(document_id, flag)
);

CREATE TABLE IF NOT EXISTS runs (
	id INTEGER PRIMARY KEY AUTOINCREMENT,
	source TEXT NOT NULL,
	city TEXT NOT NULL,
	state TEXT NOT NULL,
	slug TEXT,
	client_status TEXT NOT NULL,
	months_lookback INTEGER,
	pages_fetched INTEGER,
	matters_fetched INTEGER,
	matches_found INTEGER,
	error TEXT,
	started_at TEXT NOT NULL,
	finished_at TEXT
);
`;

export function openDb(path: string): DatabaseSync {
	const db = new DatabaseSync(path);
	db.exec(SCHEMA);
	return db;
}

export function upsertDocument(db: DatabaseSync, doc: RawDocument): number {
	const existing = db
		.prepare('SELECT id, status FROM documents WHERE source = ? AND external_id = ?')
		.get(doc.source, doc.externalId) as { id: number; status: string | null } | undefined;

	db.prepare(
		`INSERT INTO documents (source, external_id, title, body, doc_type, status, intro_date, agenda_date, url, raw_json, ingested_at)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
		 ON CONFLICT(source, external_id) DO UPDATE SET
			title = excluded.title,
			body = excluded.body,
			doc_type = excluded.doc_type,
			status = excluded.status,
			intro_date = excluded.intro_date,
			agenda_date = excluded.agenda_date,
			url = excluded.url,
			raw_json = excluded.raw_json,
			ingested_at = excluded.ingested_at`,
	).run(
		doc.source,
		doc.externalId,
		doc.title,
		doc.body,
		doc.docType,
		doc.status,
		doc.introDate,
		doc.agendaDate,
		doc.url,
		JSON.stringify(doc.raw),
		new Date().toISOString(),
	);

	const row = db
		.prepare('SELECT id FROM documents WHERE source = ? AND external_id = ?')
		.get(doc.source, doc.externalId) as { id: number };

	if (!existing || existing.status !== doc.status) {
		db.prepare('INSERT INTO status_history (document_id, status, observed_at) VALUES (?, ?, ?)').run(
			row.id,
			doc.status,
			new Date().toISOString(),
		);
	}

	return row.id;
}

export interface StatusHistoryRow {
	status: string | null;
	observed_at: string;
}

export function queryStatusHistory(db: DatabaseSync, documentId: number): StatusHistoryRow[] {
	return db
		.prepare('SELECT status, observed_at FROM status_history WHERE document_id = ? ORDER BY observed_at ASC')
		.all(documentId) as unknown as StatusHistoryRow[];
}

export function replaceMatches(db: DatabaseSync, documentId: number, hits: KeywordHit[]): void {
	db.prepare('DELETE FROM matches WHERE document_id = ?').run(documentId);
	const insert = db.prepare('INSERT INTO matches (document_id, keyword, category) VALUES (?, ?, ?)');
	for (const hit of hits) {
		insert.run(documentId, hit.keyword, hit.category);
	}
}

export function replaceComplianceFlags(
	db: DatabaseSync,
	documentId: number,
	flags: { flag: string; detail: string }[],
): void {
	db.prepare('DELETE FROM compliance_flags WHERE document_id = ?').run(documentId);
	const insert = db.prepare('INSERT INTO compliance_flags (document_id, flag, detail) VALUES (?, ?, ?)');
	for (const f of flags) {
		insert.run(documentId, f.flag, f.detail);
	}
}

export interface ComplianceFlagRow {
	document_id: number;
	title: string;
	url: string | null;
	flag: string;
	detail: string | null;
}

export function queryComplianceFlags(db: DatabaseSync, source?: string): ComplianceFlagRow[] {
	const where = source ? 'WHERE d.source = ?' : '';
	return db
		.prepare(
			`SELECT d.id AS document_id, d.title, d.url, cf.flag, cf.detail
			 FROM compliance_flags cf
			 JOIN documents d ON d.id = cf.document_id
			 ${where}
			 ORDER BY d.id`,
		)
		.all(...(source ? [source] : [])) as unknown as ComplianceFlagRow[];
}

export interface RunRecord {
	source: string;
	city: string;
	state: string;
	slug: string | null;
	clientStatus: string;
	monthsLookback: number | null;
	pagesFetched: number | null;
	mattersFetched: number | null;
	matchesFound: number | null;
	error: string | null;
	startedAt: string;
	finishedAt: string | null;
}

export function insertRun(db: DatabaseSync, run: RunRecord): void {
	db.prepare(
		`INSERT INTO runs (source, city, state, slug, client_status, months_lookback, pages_fetched, matters_fetched, matches_found, error, started_at, finished_at)
		 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
	).run(
		run.source,
		run.city,
		run.state,
		run.slug,
		run.clientStatus,
		run.monthsLookback,
		run.pagesFetched,
		run.mattersFetched,
		run.matchesFound,
		run.error,
		run.startedAt,
		run.finishedAt,
	);
}

export interface MatchedDocumentRow {
	id: number;
	title: string;
	body: string | null;
	doc_type: string | null;
	status: string | null;
	intro_date: string | null;
	agenda_date: string | null;
	url: string | null;
	categories: string;
	keywords: string;
}

export function queryMatchedDocuments(db: DatabaseSync, source: string): MatchedDocumentRow[] {
	return db
		.prepare(
			`SELECT
				d.id, d.title, d.body, d.doc_type, d.status, d.intro_date, d.agenda_date, d.url,
				GROUP_CONCAT(DISTINCT m.category) AS categories,
				GROUP_CONCAT(DISTINCT m.keyword) AS keywords
			 FROM documents d
			 JOIN matches m ON m.document_id = d.id
			 WHERE d.source = ?
			 GROUP BY d.id
			 ORDER BY d.agenda_date DESC`,
		)
		.all(source) as unknown as MatchedDocumentRow[];
}

export interface MatchedDocumentWithSourceRow extends MatchedDocumentRow {
	source: string;
}

/**
 * All matched documents across every ingested city, optionally filtered
 * to those with at least one match on/after `sinceDate` and/or matching
 * a specific keyword (case-insensitive substring, e.g. vendor name).
 */
export function queryAllMatchedDocuments(
	db: DatabaseSync,
	opts: { sinceAgendaDate?: string; keywordLike?: string; sourcePrefix?: string } = {},
): MatchedDocumentWithSourceRow[] {
	const clauses: string[] = [];
	const params: string[] = [];

	if (opts.sinceAgendaDate) {
		clauses.push('d.agenda_date >= ?');
		params.push(opts.sinceAgendaDate);
	}
	if (opts.keywordLike) {
		clauses.push('d.id IN (SELECT document_id FROM matches WHERE keyword LIKE ?)');
		params.push(`%${opts.keywordLike}%`);
	}
	if (opts.sourcePrefix) {
		clauses.push('d.source LIKE ?');
		params.push(`${opts.sourcePrefix}%`);
	}

	const where = clauses.length > 0 ? `WHERE ${clauses.join(' AND ')}` : '';

	return db
		.prepare(
			`SELECT
				d.id, d.source, d.title, d.body, d.doc_type, d.status, d.intro_date, d.agenda_date, d.url,
				GROUP_CONCAT(DISTINCT m.category) AS categories,
				GROUP_CONCAT(DISTINCT m.keyword) AS keywords
			 FROM documents d
			 JOIN matches m ON m.document_id = d.id
			 ${where}
			 GROUP BY d.id
			 ORDER BY d.agenda_date DESC`,
		)
		.all(...params) as unknown as MatchedDocumentWithSourceRow[];
}
