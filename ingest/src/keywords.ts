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
		// ALPR / camera / video surveillance vendors
		'Flock Safety',
		'Flock Group',
		'Vigilant Solutions',
		'Motorola Solutions',
		'Rekor Systems',
		'Genetec',
		'Avigilon',
		'Verkada',
		'Hikvision',
		'Dahua',
		'BriefCam',
		'Fusus',
		// Facial recognition / biometrics vendors
		'Clearview AI',
		'NEC Corporation',
		'Cognitec',
		'Idemia',
		'BI2 Technologies',
		// Gunshot detection
		'ShotSpotter',
		'SoundThinking',
		// Body cameras / digital evidence / forensics
		'Axon Enterprise',
		'Cellebrite',
		'Grayshift',
		// Data fusion / real-time crime center / data brokers
		'Palantir',
		'Forensic Logic',
		'CopLink',
		'Crimetracer',
		'LexisNexis',
		'Thomson Reuters CLEAR',
	],
	'facial-recognition': [
		'facial recognition',
		'face recognition',
		'biometric identification',
		'biometric surveillance',
		'biometrics',
	],
	'cell-site': ['cell-site simulator', 'cell site simulator', 'Stingray device', 'IMSI catcher', 'pen register'],
	drone: [
		'drone as first responder',
		'DFR program',
		'unmanned aerial system',
		'unmanned aircraft system',
		'forward looking infrared',
		'FLIR',
	],
	'generic-surveillance': [
		'surveillance technology',
		'surveillance camera network',
		'predictive policing',
		'real-time crime center',
		'gunshot detection',
		'gunshot location',
		'live stream transmitter',
		'DNA analysis technology',
	],
};

interface CompiledKeyword {
	keyword: string;
	category: MatchCategory;
	pattern: RegExp;
}

function escapeRegExp(s: string): string {
	return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

/**
 * Word-boundary match that tolerates a trailing plural/possessive so
 * "license plate reader" still matches "License Plate Readers", and
 * "camera" still matches "cameras". Matching only exact phrases missed
 * real hits (e.g. Oakland's own annual report says "Readers", not "Reader").
 */
function buildPattern(keyword: string): RegExp {
	return new RegExp(`\\b${escapeRegExp(keyword)}(?:'s|s)?\\b`, 'i');
}

const ALL_KEYWORDS: CompiledKeyword[] = Object.entries(KEYWORDS).flatMap(([category, words]) =>
	words.map((keyword) => ({
		keyword,
		category: category as MatchCategory,
		pattern: buildPattern(keyword),
	})),
);

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
