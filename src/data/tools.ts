export type Category =
	| 'routing'
	| 'mapping'
	| 'facial-recognition'
	| 'cell-site'
	| 'foia';

export interface CategoryMeta {
	id: Category;
	label: string;
	description: string;
}

export const categories: CategoryMeta[] = [
	{
		id: 'routing',
		label: 'Camera-Avoidance Routing',
		description: 'Route planners that steer you around known ALPR and surveillance cameras.',
	},
	{
		id: 'mapping',
		label: 'Surveillance Mapping',
		description: 'Crowdsourced and research databases documenting where surveillance tech is deployed.',
	},
	{
		id: 'facial-recognition',
		label: 'Facial Recognition Resistance',
		description: 'Campaigns, apparel, and eyewear built to resist or ban facial recognition.',
	},
	{
		id: 'cell-site',
		label: 'Cell-Site Simulator Detection',
		description: 'Tools that detect IMSI catchers ("Stingrays") monitoring nearby phones.',
	},
	{
		id: 'foia',
		label: 'FOIA & Records Infrastructure',
		description: 'Tools for requesting, tracking, and researching government surveillance records.',
	},
];

export interface Tool {
	name: string;
	url: string;
	description: string;
	category: Category;
}

export const tools: Tool[] = [
	{
		name: 'FlockHopper',
		url: 'https://dontgetflocked.com/',
		description:
			'Free route planner that shows how many ALPR cameras line your route and generates an alternative that avoids them. No account required.',
		category: 'routing',
	},
	{
		name: 'Drivers Against Flock',
		url: 'https://driversagainstflock.org/',
		description:
			'Privacy-first turn-by-turn navigation app that routes around known ALPR and surveillance devices. No login, no data collection.',
		category: 'routing',
	},
	{
		name: 'Untracked',
		url: 'https://www.untracked.app/',
		description:
			'Navigation app that identifies ALPR-dense areas and optimizes routes to reduce exposure.',
		category: 'routing',
	},
	{
		name: 'UnFlocked',
		url: 'https://unflocked.org/app',
		description: 'Maps Flock ALPR cameras nationwide and plans routes that avoid them.',
		category: 'routing',
	},
	{
		name: 'flckd',
		url: 'https://flckd.com/',
		description: 'Camera-avoiding route planner focused on ALPR cameras.',
		category: 'routing',
	},
	{
		name: 'DeFlock',
		url: 'https://deflock.org/',
		description:
			'Open-source, OpenStreetMap-based crowdsourced map of ALPR and surveillance camera locations — 16,000+ cameras logged.',
		category: 'mapping',
	},
	{
		name: 'EFF Atlas of Surveillance',
		url: 'https://www.atlasofsurveillance.org/',
		description:
			'Searchable database of 15,000+ police surveillance technology deployments across 6,000+ U.S. jurisdictions, from EFF and the Reynolds School of Journalism.',
		category: 'mapping',
	},
	{
		name: 'Fight for the Future: Ban Facial Recognition',
		url: 'https://www.fightforthefuture.org/',
		description:
			'Interactive map tracking facial recognition use and local bans, plus a toolkit for starting a ban campaign.',
		category: 'facial-recognition',
	},
	{
		name: 'Amnesty International: Ban the Scan',
		url: 'https://www.amnesty.org/en/petition/ban-the-scan-petition/',
		description: 'Global campaign and petition against police use of facial recognition surveillance.',
		category: 'facial-recognition',
	},
	{
		name: 'Adversarial Apparel',
		url: 'https://adversarialapparel.com/',
		description: 'Clothing with adversarial patterns designed to confuse computer vision and facial recognition systems.',
		category: 'facial-recognition',
	},
	{
		name: 'Reflectacles',
		url: 'https://www.reflectacles.com/',
		description:
			'Infrared-blocking, reflective eyewear designed to defeat facial recognition systems, including Face ID.',
		category: 'facial-recognition',
	},
	{
		name: 'Rayhunter',
		url: 'https://github.com/EFForg/rayhunter',
		description:
			"EFF's open-source tool that runs on a low-cost mobile hotspot to detect cell-site simulators (Stingrays).",
		category: 'cell-site',
	},
	{
		name: 'AIMSICD',
		url: 'https://cellularprivacy.github.io/Android-IMSI-Catcher-Detector/',
		description: 'Android app for detecting IMSI catchers monitoring nearby cell traffic.',
		category: 'cell-site',
	},
	{
		name: 'MuckRock',
		url: 'https://www.muckrock.com/',
		description:
			'FOIA request generator and tracker spanning ~22,000 government agencies, with a public archive of 120,000+ requests.',
		category: 'foia',
	},
	{
		name: 'IPVM',
		url: 'https://ipvm.com/',
		description:
			'Independent research and intelligence on physical security and video surveillance technology, including vendor contracts.',
		category: 'foia',
	},
];
