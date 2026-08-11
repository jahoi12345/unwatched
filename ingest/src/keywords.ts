import type { KeywordHit, MatchCategory } from './types.ts';

const KEYWORDS: Record<MatchCategory, string[]> = {
	alpr: [
		'automated license plate reader',
		'automatic license plate reader',
		'license plate reader',
		'license plate recognition',
		'ALPR',
		'LPR camera',
	],
	vendor: [
		'Flock Safety',
		'Flock Group',
		'Vigilant Solutions',
		'Motorola Solutions',
		'Rekor Systems',
		'Genetec',
		'Axon Enterprise',
		'ShotSpotter',
		'SoundThinking',
	],
	'facial-recognition': ['facial recognition', 'face recognition', 'biometric identification', 'biometric surveillance'],
	'cell-site': ['cell-site simulator', 'cell site simulator', 'Stingray device', 'IMSI catcher'],
	drone: ['drone as first responder', 'DFR program', 'unmanned aerial system', 'unmanned aircraft system'],
	'generic-surveillance': [
		'surveillance technology',
		'surveillance camera network',
		'predictive policing',
		'real-time crime center',
	],
};

const ALL_KEYWORDS: { keyword: string; category: MatchCategory; pattern: RegExp }[] = Object.entries(KEYWORDS).flatMap(
	([category, words]) =>
		words.map((keyword) => ({
			keyword,
			category: category as MatchCategory,
			pattern: new RegExp(`\\b${escapeRegExp(keyword)}\\b`, 'i'),
		})),
);

function escapeRegExp(s: string): string {
	return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

export function findKeywordHits(...texts: (string | null | undefined)[]): KeywordHit[] {
	const haystack = texts.filter(Boolean).join(' \n ');
	const hits: KeywordHit[] = [];
	for (const { keyword, category, pattern } of ALL_KEYWORDS) {
		if (pattern.test(haystack)) {
			hits.push({ keyword, category });
		}
	}
	return hits;
}
