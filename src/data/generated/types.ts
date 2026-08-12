export interface CoverageSummary {
	ranAt?: string;
	monthsLookback?: number;
	totalCitiesTargeted?: number;
	citiesIngested?: number;
	citiesNotFound?: { name: string; state: string; triedCandidates: string[] }[];
	totalMattersFetched?: number;
	totalMatchesFound?: number;
}

export interface SurveillanceMatter {
	city: string;
	state: string;
	slug: string;
	clientStatus: 'live' | 'stale' | 'not-found';
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

export interface FlockStatusEvent {
	status: string | null;
	observed_at: string;
}

export interface FlockTransparencyItem {
	city: string;
	title: string;
	currentStatus: string | null;
	agendaDate: string | null;
	url: string | null;
	statusHistory: FlockStatusEvent[];
}

export interface DigestItem {
	city: string;
	title: string;
	body: string | null;
	agendaDate: string | null;
	status: string | null;
	keywords: string;
	url: string | null;
	draftedComment: string;
	commentTemplate: 'data-sharing' | 'annual-report' | 'contract' | 'generic';
	vendor: string | null;
	dollarAmount: string | null;
}

export interface DigestReport {
	generatedAt?: string;
	sinceDate?: string;
	days?: number;
	items?: DigestItem[];
}

export interface FoiaComplianceItem {
	file: string;
	title: string;
	agency: string | null;
	state: string | null;
	surveillanceKeywords: string[];
	complianceFlags: string[];
	complianceDetail: string[];
}
