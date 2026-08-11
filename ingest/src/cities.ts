export interface CityTarget {
	name: string;
	state: string;
	rank: number; // population rank, for reporting
	/** Candidate Legistar client slugs to try, in order. First one that resolves to live data wins. */
	candidates: string[];
}

function compact(name: string): string {
	return name.toLowerCase().replace(/[^a-z]/g, '');
}

function guesses(name: string, extra: string[] = []): string[] {
	const c = compact(name);
	return [...extra, c, `${c}gov`, `cityof${c}`, `city${c}`];
}

// Top 50 US cities by population (2026 estimates), with best-guess Legistar
// client slugs. Not every city runs Legistar, and not every guess is right —
// that's exactly what `discover.ts` is for: it probes these and tells us
// which actually resolve to live data.
export const TOP_50_CITIES: CityTarget[] = [
	{ name: 'New York', state: 'NY', rank: 1, candidates: guesses('New York', ['nyc', 'council']) },
	{ name: 'Los Angeles', state: 'CA', rank: 2, candidates: guesses('Los Angeles', ['lacity', 'lacouncil']) },
	{ name: 'Chicago', state: 'IL', rank: 3, candidates: guesses('Chicago') },
	{ name: 'Houston', state: 'TX', rank: 4, candidates: guesses('Houston') },
	{ name: 'Phoenix', state: 'AZ', rank: 5, candidates: guesses('Phoenix') },
	{ name: 'San Antonio', state: 'TX', rank: 6, candidates: guesses('San Antonio', ['sanantonio']) },
	{ name: 'Philadelphia', state: 'PA', rank: 7, candidates: guesses('Philadelphia', ['phila']) },
	{ name: 'San Diego', state: 'CA', rank: 8, candidates: guesses('San Diego', ['sandiego']) },
	{ name: 'Dallas', state: 'TX', rank: 9, candidates: guesses('Dallas') },
	{ name: 'Fort Worth', state: 'TX', rank: 10, candidates: guesses('Fort Worth', ['fortworth']) },
	{ name: 'Jacksonville', state: 'FL', rank: 11, candidates: guesses('Jacksonville', ['coj']) },
	{ name: 'Austin', state: 'TX', rank: 12, candidates: guesses('Austin') },
	{ name: 'San Jose', state: 'CA', rank: 13, candidates: guesses('San Jose', ['sanjoseca', 'sanjose']) },
	{ name: 'Charlotte', state: 'NC', rank: 14, candidates: guesses('Charlotte', ['charlottenc']) },
	{ name: 'Columbus', state: 'OH', rank: 15, candidates: guesses('Columbus') },
	{ name: 'Indianapolis', state: 'IN', rank: 16, candidates: guesses('Indianapolis', ['indy']) },
	{ name: 'San Francisco', state: 'CA', rank: 17, candidates: guesses('San Francisco', ['sfgov']) },
	{ name: 'Seattle', state: 'WA', rank: 19, candidates: guesses('Seattle') },
	{ name: 'Denver', state: 'CO', rank: 20, candidates: guesses('Denver') },
	{ name: 'Oklahoma City', state: 'OK', rank: 21, candidates: guesses('Oklahoma City', ['okc']) },
	{ name: 'Nashville', state: 'TN', rank: 22, candidates: guesses('Nashville') },
	{ name: 'Washington', state: 'DC', rank: 23, candidates: ['dc', 'dccouncil', 'dcgov'] },
	{ name: 'Las Vegas', state: 'NV', rank: 24, candidates: guesses('Las Vegas', ['lasvegas']) },
	{ name: 'El Paso', state: 'TX', rank: 25, candidates: guesses('El Paso', ['elpaso']) },
	{ name: 'Boston', state: 'MA', rank: 26, candidates: guesses('Boston') },
	{ name: 'Detroit', state: 'MI', rank: 27, candidates: guesses('Detroit') },
	{ name: 'Louisville', state: 'KY', rank: 28, candidates: guesses('Louisville', ['louisvilleky']) },
	{ name: 'Portland', state: 'OR', rank: 29, candidates: guesses('Portland', ['portlandoregon']) },
	{ name: 'Memphis', state: 'TN', rank: 30, candidates: guesses('Memphis') },
	{ name: 'Baltimore', state: 'MD', rank: 31, candidates: guesses('Baltimore') },
	{ name: 'Milwaukee', state: 'WI', rank: 32, candidates: guesses('Milwaukee') },
	{ name: 'Fresno', state: 'CA', rank: 33, candidates: guesses('Fresno') },
	{ name: 'Albuquerque', state: 'NM', rank: 34, candidates: guesses('Albuquerque', ['cabq']) },
	{ name: 'Tucson', state: 'AZ', rank: 35, candidates: guesses('Tucson') },
	{ name: 'Sacramento', state: 'CA', rank: 36, candidates: guesses('Sacramento') },
	{ name: 'Atlanta', state: 'GA', rank: 37, candidates: guesses('Atlanta', ['atlantaga']) },
	{ name: 'Kansas City', state: 'MO', rank: 38, candidates: guesses('Kansas City', ['kcmo']) },
	{ name: 'Mesa', state: 'AZ', rank: 39, candidates: guesses('Mesa') },
	{ name: 'Raleigh', state: 'NC', rank: 40, candidates: guesses('Raleigh') },
	{ name: 'Miami', state: 'FL', rank: 41, candidates: guesses('Miami', ['miamifl']) },
	{ name: 'Colorado Springs', state: 'CO', rank: 43, candidates: guesses('Colorado Springs', ['coloradosprings']) },
	{ name: 'Omaha', state: 'NE', rank: 44, candidates: guesses('Omaha') },
	{ name: 'Virginia Beach', state: 'VA', rank: 45, candidates: guesses('Virginia Beach', ['vbgov']) },
	{ name: 'Long Beach', state: 'CA', rank: 46, candidates: guesses('Long Beach', ['longbeach']) },
	{ name: 'Oakland', state: 'CA', rank: 47, candidates: guesses('Oakland') },
	{ name: 'Minneapolis', state: 'MN', rank: 48, candidates: guesses('Minneapolis') },
	{ name: 'Bakersfield', state: 'CA', rank: 49, candidates: guesses('Bakersfield') },
	{ name: 'Tampa', state: 'FL', rank: 50, candidates: guesses('Tampa') },
];
