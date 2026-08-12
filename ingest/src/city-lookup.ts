import { existsSync, readFileSync } from 'node:fs';

export interface CityLookupEntry {
	slug: string;
	name: string;
	state: string;
}

/** Loads the slug -> {name, state} map written by batch.ts on its last run. */
export function loadCityLookup(dataDir: string): Map<string, CityLookupEntry> {
	const path = `${dataDir}/resolved-cities.json`;
	const map = new Map<string, CityLookupEntry>();
	if (!existsSync(path)) return map;
	const entries = JSON.parse(readFileSync(path, 'utf-8')) as CityLookupEntry[];
	for (const entry of entries) map.set(entry.slug, entry);
	return map;
}

/** Strips a "legistar:"/"permits:" source prefix and resolves it to a proper "City, ST" label. */
export function cityDisplayName(source: string, lookup: Map<string, CityLookupEntry>): string {
	const slug = source.replace(/^[a-z-]+:/, '');
	const entry = lookup.get(slug);
	return entry ? `${entry.name}, ${entry.state}` : slug;
}
