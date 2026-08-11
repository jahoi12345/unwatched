export type Category =
	| 'routing'
	| 'mapping'
	| 'facial-recognition'
	| 'tracking-device'
	| 'ice-surveillance'
	| 'foia'
	| 'digital-security';

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
		id: 'tracking-device',
		label: 'Tracking Device Detection',
		description: 'Tools that detect physical tracking devices — cell-site simulators ("Stingrays") and Bluetooth trackers like AirTags.',
	},
	{
		id: 'ice-surveillance',
		label: 'Immigration & Data-Broker Surveillance',
		description: 'Tracking the data brokers and tech vendors that feed surveillance data to ICE and other agencies.',
	},
	{
		id: 'foia',
		label: 'FOIA & Records Infrastructure',
		description: 'Tools for requesting, tracking, and researching government surveillance records.',
	},
	{
		id: 'digital-security',
		label: 'Digital Security Guides',
		description: 'General-purpose guides for securing your devices, communications, and online footprint.',
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
		name: 'Rural Privacy Coalition',
		url: 'https://ruralprivacy.org',
		description:
			'ALPR action toolkit and map connecting rural privacy organizers, with templates for pushing back on local surveillance deployments.',
		category: 'mapping',
	},
	{
		name: 'Texas Privacy Coalition',
		url: 'https://www.texasprivacycoalition.com/map',
		description: 'State-specific map of ALPR/Flock camera locations across Texas, plus an organizing toolkit.',
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
		name: 'America Under Watch',
		url: 'https://www.americaunderwatch.com/',
		description:
			"Georgetown Center on Privacy & Technology's research hub documenting citywide face-surveillance networks in the U.S.",
		category: 'facial-recognition',
	},
	{
		name: 'Rayhunter',
		url: 'https://github.com/EFForg/rayhunter',
		description:
			"EFF's open-source tool that runs on a low-cost mobile hotspot to detect cell-site simulators (Stingrays).",
		category: 'tracking-device',
	},
	{
		name: 'AIMSICD',
		url: 'https://cellularprivacy.github.io/Android-IMSI-Catcher-Detector/',
		description: 'Android app for detecting IMSI catchers monitoring nearby cell traffic.',
		category: 'tracking-device',
	},
	{
		name: 'AirGuard',
		url: 'https://github.com/seemoo-lab/AirGuard',
		description:
			'Open-source Android app that detects unwanted Bluetooth trackers — AirTags, Samsung SmartTags, Tile, and similar devices.',
		category: 'tracking-device',
	},
	{
		name: 'Mijente: No Tech For ICE',
		url: 'https://notechforice.com/',
		description:
			'Documents the data brokers and tech vendors (Palantir and others) supplying surveillance data and tooling to ICE.',
		category: 'ice-surveillance',
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
	{
		name: 'Lucy Parsons Labs',
		url: 'https://www.lucyparsonslabs.com/',
		description:
			'Files and litigates public-records requests to expose police surveillance technology purchases and use.',
		category: 'foia',
	},
	{
		name: 'OpenOversight',
		url: 'https://openoversight.com/',
		description:
			"Lucy Parsons Labs' crowdsourced, public-records-based database for identifying police officers by badge, name, or photo.",
		category: 'foia',
	},
	{
		name: 'EFF Surveillance Self-Defense',
		url: 'https://ssd.eff.org/',
		description:
			"EFF's guide to securing your devices and communications — threat modeling, secure messaging, and step-by-step tool tutorials.",
		category: 'digital-security',
	},
];
