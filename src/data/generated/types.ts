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

export interface CameraRecord {
	id: number;
	lat: number;
	lon: number;
	manufacturer: string | null;
	direction: string | null;
	zone: string | null;
}

export interface CameraDataset {
	city?: string;
	bbox?: { south: number; west: number; north: number; east: number };
	fetchedAt?: string;
	cameras?: CameraRecord[];
}

export interface TrajectoryReport {
	city?: string;
	bbox?: { south: number; west: number; north: number; east: number };
	generatedAt?: string;
	cameraCount?: number;
	coverage?: {
		gridSize: number;
		radiusMeters: number;
		total: number;
		covered: number;
		coveragePercent: number;
	};
	trips?: {
		count: number;
		corridorMeters: number;
		capturedTripCount: number;
		captureRatePercent: number;
		avgHitsPerCapturedTrip: number;
		exampleReconstruction: {
			hitCount: number;
			sequence: { manufacturer: string | null; lat: number; lon: number; approxSecondsIntoTrip: number }[];
		} | null;
	};
	methodology?: string[];
}

export interface PermitItem {
	city: string;
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

export interface FoiaComplianceItem {
	file: string;
	title: string;
	agency: string | null;
	state: string | null;
	surveillanceKeywords: string[];
	complianceFlags: string[];
	complianceDetail: string[];
}
