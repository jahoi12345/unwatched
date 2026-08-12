import type { RawDocument } from '../types.ts';

export interface PermitSourceConfig {
	citySlug: string;
	displayName: string; // e.g. 'San Francisco, CA'
	host: string; // e.g. 'data.sfgov.org'
	resourceId: string; // e.g. 'p4e4-a5a7'
	descriptionField: string;
	numberField: string;
	filedDateField: string;
	statusDateField: string;
	statusField: string;
	addressFields: string[]; // fields to join into a human-readable address
}

/** Verified, currently-live Socrata permit datasets. Add more cities here as they're found. */
export const PERMIT_SOURCES: PermitSourceConfig[] = [
	{
		citySlug: 'sfgov',
		displayName: 'San Francisco, CA',
		host: 'data.sfgov.org',
		resourceId: 'p4e4-a5a7',
		descriptionField: 'description',
		numberField: 'permit_number',
		filedDateField: 'filed_date',
		statusDateField: 'status_date',
		statusField: 'status',
		addressFields: ['street_number', 'street_name', 'street_suffix'],
	},
];

const SURVEILLANCE_PERMIT_KEYWORDS = [
	'license plate reader',
	'automated license plate',
	'alpr',
	'surveillance camera',
	'security camera pole',
	'flock safety',
	'flock camera',
];

interface SocrataRow {
	[key: string]: string | undefined;
}

/**
 * Queries a city's public Socrata open-data permits dataset for filings
 * whose free-text description mentions surveillance/ALPR hardware — this
 * is how private commercial and HOA-driven camera installs surface in
 * public records: as electrical/structural permits, not police purchases.
 */
export async function fetchSurveillancePermits(config: PermitSourceConfig): Promise<RawDocument[]> {
	const clauses = SURVEILLANCE_PERMIT_KEYWORDS.map(
		(kw) => `lower(${config.descriptionField}) like '%${kw.replace(/'/g, "''")}%'`,
	).join(' OR ');
	const url = `https://${config.host}/resource/${config.resourceId}.json?$where=${encodeURIComponent(clauses)}&$limit=1000`;

	const res = await fetch(url, { headers: { Accept: 'application/json' } });
	if (!res.ok) {
		throw new Error(`Socrata API error for ${config.host}/${config.resourceId}: ${res.status} ${res.statusText}`);
	}
	const rows = (await res.json()) as SocrataRow[];

	return rows.map((row) => {
		const address = config.addressFields
			.map((f) => row[f])
			.filter(Boolean)
			.join(' ');
		const number = row[config.numberField] ?? '';
		return {
			source: `permits:${config.citySlug}`,
			externalId: number,
			title: (row[config.descriptionField] ?? '(no description)').slice(0, 300),
			body: address || 'address unavailable',
			docType: 'permit',
			status: row[config.statusField] ?? 'unknown',
			introDate: row[config.filedDateField] ?? null,
			agendaDate: row[config.statusDateField] ?? row[config.filedDateField] ?? null,
			url: `https://${config.host}/resource/${config.resourceId}.json?${config.numberField}=${encodeURIComponent(number)}`,
			raw: row,
		};
	});
}
