import type { RawDocument } from '../types.ts';

interface LegistarMatter {
	MatterId: number;
	MatterGuid: string;
	MatterFile: string | null;
	MatterName: string | null;
	MatterTitle: string | null;
	MatterTypeName: string | null;
	MatterStatusName: string | null;
	MatterBodyName: string | null;
	MatterIntroDate: string | null;
	MatterAgendaDate: string | null;
}

const PAGE_SIZE = 1000;

function legistarDetailUrl(client: string, matter: LegistarMatter): string {
	return `https://${client}.legistar.com/LegislationDetail.aspx?ID=${matter.MatterId}&GUID=${matter.MatterGuid}`;
}

export interface LegistarFetchResult {
	documents: RawDocument[];
	pagesFetched: number;
}

/**
 * Fetches Legistar matters (agenda items) for a client introduced on or after `sinceDate`.
 * Legistar's public Web API: https://webapi.legistar.com/Home/Examples
 *
 * `pagesFetched` is returned so callers can audit completeness: if the last
 * page fetched was a full page (PAGE_SIZE items), the loop kept going, so a
 * non-full last page is proof pagination reached the true end rather than
 * being cut short.
 */
export async function fetchLegistarMatters(client: string, sinceDate: Date): Promise<LegistarFetchResult> {
	const isoDate = sinceDate.toISOString().slice(0, 19);
	const documents: RawDocument[] = [];
	let skip = 0;
	let pagesFetched = 0;

	for (;;) {
		const url = new URL(`https://webapi.legistar.com/v1/${client}/matters`);
		url.searchParams.set('$filter', `MatterIntroDate ge datetime'${isoDate}'`);
		url.searchParams.set('$orderby', 'MatterIntroDate desc');
		url.searchParams.set('$top', String(PAGE_SIZE));
		url.searchParams.set('$skip', String(skip));

		const res = await fetch(url, { headers: { Accept: 'application/json' } });
		if (!res.ok) {
			throw new Error(`Legistar API error for client "${client}": ${res.status} ${res.statusText}`);
		}
		const page = (await res.json()) as LegistarMatter[];
		pagesFetched++;
		if (page.length === 0) break;

		for (const matter of page) {
			documents.push({
				source: `legistar:${client}`,
				externalId: String(matter.MatterId),
				title: matter.MatterTitle ?? matter.MatterName ?? '(untitled)',
				body: matter.MatterBodyName ?? '',
				docType: matter.MatterTypeName ?? '',
				status: matter.MatterStatusName ?? '',
				introDate: matter.MatterIntroDate,
				agendaDate: matter.MatterAgendaDate,
				url: legistarDetailUrl(client, matter),
				raw: matter,
			});
		}

		if (page.length < PAGE_SIZE) break;
		skip += PAGE_SIZE;
	}

	return { documents, pagesFetched };
}
