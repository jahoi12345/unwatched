export type MatchCategory =
	| 'alpr'
	| 'facial-recognition'
	| 'cell-site'
	| 'drone'
	| 'vendor'
	| 'generic-surveillance';

export interface RawDocument {
	source: string; // e.g. 'legistar:sfgov'
	externalId: string; // e.g. Legistar MatterId
	title: string;
	body: string; // committee/department name
	docType: string;
	status: string;
	introDate: string | null;
	agendaDate: string | null;
	url: string;
	raw: unknown;
}

export interface KeywordHit {
	keyword: string;
	category: MatchCategory;
}
