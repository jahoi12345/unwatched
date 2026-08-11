import type { MatchedDocumentWithSourceRow } from './db.ts';

function extractDollarAmount(text: string): string | null {
	const matches = text.match(/\$[\d,]+(?:\.\d{2})?/g);
	if (!matches) return null;
	let best = 0;
	let bestStr: string | null = null;
	for (const m of matches) {
		const value = Number(m.replace(/[$,]/g, ''));
		if (value > best) {
			best = value;
			bestStr = m;
		}
	}
	return bestStr;
}

function vendorFromKeywords(keywords: string[]): string | null {
	const knownVendors = [
		'Flock Safety',
		'Flock Group',
		'Motorola Solutions',
		'Vigilant Solutions',
		'Rekor Systems',
		'Genetec',
		'Avigilon',
		'Verkada',
		'Hikvision',
		'Dahua',
		'Clearview AI',
		'Axon Enterprise',
		'Cellebrite',
		'ShotSpotter',
		'SoundThinking',
		'Palantir',
		'LexisNexis',
		'Idemia',
	];
	return knownVendors.find((v) => keywords.includes(v)) ?? null;
}

type Template = 'data-sharing' | 'annual-report' | 'contract' | 'generic';

function classify(row: MatchedDocumentWithSourceRow): Template {
	const text = `${row.title} ${row.body ?? ''}`;
	if (/\bICE\b|immigration and customs enforcement/i.test(text)) return 'data-sharing';
	if (/annual report/i.test(text)) return 'annual-report';
	if (/contract|agreement|award|acquisition|purchase/i.test(text)) return 'contract';
	return 'generic';
}

export interface DraftedComment {
	template: Template;
	vendor: string | null;
	dollarAmount: string | null;
	text: string;
}

export function draftPublicComment(row: MatchedDocumentWithSourceRow): DraftedComment {
	const keywords = row.keywords.split(',');
	const vendor = vendorFromKeywords(keywords);
	const dollarAmount = extractDollarAmount(row.title);
	const body = row.body?.replace(/^\*/, '').trim() || 'the relevant committee';
	const dateStr = row.agenda_date ? row.agenda_date.slice(0, 10) : 'an upcoming date';
	const tech = vendor ?? keywords[0] ?? 'surveillance technology';
	const template = classify(row);

	let text: string;
	switch (template) {
		case 'data-sharing':
			text =
				`This item before ${body} on ${dateStr} concerns data-sharing policy for ${tech}, including access by ` +
				`Immigration and Customs Enforcement (ICE) or other outside agencies. I'm asking the council to require public ` +
				`disclosure of every outside agency this data has been shared with over the past 12 months, and to adopt a ` +
				`binding policy prohibiting data sharing with federal immigration enforcement absent a judicial warrant.`;
			break;
		case 'annual-report':
			text =
				`This item asks ${body} to accept the annual report on ${tech} and decide whether to continue using it. ` +
				`I'm asking the council not to treat this as a formality: require the report to include hit-rate/false-positive ` +
				`statistics, total cost to date, and a complete list of outside agencies that received data from this system ` +
				`before voting to continue its use.`;
			break;
		case 'contract':
			text =
				`This item before ${body} on ${dateStr} would commit the city to ${vendor ? `a contract with ${vendor}` : 'a surveillance technology contract'}` +
				`${dollarAmount ? ` at a cost of ${dollarAmount}` : ''}. Before approving this, I'm asking the council to: ` +
				`(1) publish the full contract and any data-sharing agreements attached to it; (2) confirm in writing whether ` +
				`captured data will be shared with agencies outside this jurisdiction, including federal immigration enforcement; ` +
				`(3) require a public annual audit of usage, false-positive rates, and data-sharing requests before any renewal.`;
			break;
		default:
			text =
				`This item before ${body} on ${dateStr} involves surveillance technology (${tech}). I'm asking the council to ` +
				`ensure any decision includes public disclosure of cost, vendor, data retention period, and any data-sharing ` +
				`agreements before moving forward.`;
	}

	return { template, vendor, dollarAmount, text };
}
