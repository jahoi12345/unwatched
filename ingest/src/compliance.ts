export type ComplianceFlag =
	| 'redaction'
	| 'full-denial'
	| 'partial-denial'
	| 'fee-waiver-denied'
	| 'late-response'
	| 'on-time-response'
	| 'unknown-deadline';

export interface FoiaMetadata {
	agency?: string;
	state?: string;
	requestDate?: string; // ISO date the FOIA/public-records request was filed
	responseDate?: string; // ISO date the response was received
	requestSubject?: string;
}

/**
 * Statutory response-deadline in business days, by state, for public-records
 * requests. These are approximate and meant to flag responses worth a closer
 * look, not to be relied on as legal advice — deadlines vary by request type
 * and change over time; verify the current statute before citing one.
 */
const STATE_DEADLINE_BUSINESS_DAYS: Record<string, number> = {
	CA: 10,
	NY: 5,
	TX: 10,
	IL: 5,
	WA: 5,
	MA: 10,
	PA: 5,
	OH: 0, // "reasonable period" — no fixed statutory number
	MI: 5,
	CO: 3,
	AZ: 0, // "promptly" — no fixed statutory number
	FL: 0, // "reasonable time" — no fixed statutory number
	GA: 3,
	NC: 0, // "as promptly as possible" — no fixed statutory number
	OR: 0, // "reasonable time" — no fixed statutory number
};

function businessDaysBetween(start: Date, end: Date): number {
	let count = 0;
	const cur = new Date(start);
	while (cur < end) {
		const day = cur.getDay();
		if (day !== 0 && day !== 6) count++;
		cur.setDate(cur.getDate() + 1);
	}
	return count;
}

export interface ComplianceResult {
	flags: ComplianceFlag[];
	detail: string[];
}

export function analyzeCompliance(text: string, metadata: FoiaMetadata): ComplianceResult {
	const flags: ComplianceFlag[] = [];
	const detail: string[] = [];

	if (/redact/i.test(text)) {
		flags.push('redaction');
		detail.push('Document contains redaction language.');
	}

	if (/(no responsive records|withheld in full|records? (are|is) exempt from disclosure)/i.test(text)) {
		flags.push('full-denial');
		detail.push('Language suggests a full denial or blanket exemption claim.');
	} else if (/exempt|withheld pursuant to/i.test(text)) {
		flags.push('partial-denial');
		detail.push('Language suggests a partial exemption/withholding claim.');
	}

	if (/fee waiver[^.]{0,40}(denied|not granted|rejected)/i.test(text)) {
		flags.push('fee-waiver-denied');
		detail.push('Fee waiver appears to have been denied.');
	}

	if (metadata.requestDate && metadata.responseDate) {
		const deadline = metadata.state ? STATE_DEADLINE_BUSINESS_DAYS[metadata.state.toUpperCase()] : undefined;
		const days = businessDaysBetween(new Date(metadata.requestDate), new Date(metadata.responseDate));
		if (!deadline) {
			flags.push('unknown-deadline');
			detail.push(
				`Response took ${days} business day(s); no fixed statutory deadline configured for ${metadata.state ?? 'this state'} (verify manually).`,
			);
		} else if (days > deadline) {
			flags.push('late-response');
			detail.push(`Response took ${days} business day(s); ${metadata.state}'s statutory deadline is ${deadline}.`);
		} else {
			flags.push('on-time-response');
			detail.push(`Response took ${days} business day(s); within ${metadata.state}'s ${deadline}-day deadline.`);
		}
	}

	return { flags, detail };
}
