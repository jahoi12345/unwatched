# Unwatched Ingest

Shared records-ingestion layer: pulls public government records, tags the
ones that mention surveillance technology, and stores structured results
in a local SQLite database. This is the foundation the FOIA parser,
Flock transparency monitor, and municipal advocacy bot are meant to sit on
top of — one pipeline, multiple views.

## Usage

```sh
npm install
npm run ingest -- --client=<legistar-client-slug> [--months=24]
```

Example:

```sh
npm run ingest -- --client=oakland --months=24
```

This fetches council agenda items ("matters") introduced in the last
`--months` from that city's [Legistar](https://webapi.legistar.com/Home/Examples)
instance, flags any that mention ALPR/Flock/facial recognition/cell-site
simulators/drones/known vendors, stores them in `data/unwatched.db`, prints
a report, and exports matched records to `data/<client>-surveillance-matters.json`.

### Finding a client slug

The slug is the subdomain a city uses at `https://<slug>.legistar.com`.
Not every city runs Legistar, and not every Legistar instance is kept
current on the public `webapi.legistar.com` mirror — e.g. `sfgov`'s data
here is frozen at 2020 even though San Francisco's own site is current,
apparently because they migrated their public agenda site off this API.
Verify a client has recent data before relying on it:

```sh
curl -s "https://webapi.legistar.com/v1/<slug>/matters?\$orderby=MatterId%20desc&\$top=1"
```

## Data model

- `documents` — one row per agenda matter, keyed by `(source, external_id)`
- `matches` — keyword hits per document, with a category (`alpr`,
  `facial-recognition`, `cell-site`, `drone`, `vendor`, `generic-surveillance`)

Keyword taxonomy lives in `src/keywords.ts`.

## Running against many cities

`src/cities.ts` holds a target list (currently the top 50 US cities by
population) with best-guess Legistar client slugs per city.

```sh
npm run discover           # probes every candidate slug, classifies each
                            # city as live / stale / not-found, without
                            # ingesting anything
npm run batch -- --months=24   # runs discovery, then ingests every
                                # live/stale city, logging one row per
                                # city to the `runs` table for audit
```

`stale` means the client resolves but its most recent record predates
the live threshold (6 months) — e.g. `sfgov`'s data is frozen at 2020,
apparently because San Francisco migrated their public agenda site off
the shared `webapi.legistar.com` host. `not-found` means none of the
candidate slugs resolved — that city likely doesn't run Legistar, or
runs a private/differently-hosted instance; it needs a different source
connector, not a better slug guess.

### Validating coverage — the `runs` table

Every `batch` run writes one row per city to `runs`: slug, status,
pages fetched, matters fetched, matches found, and any error. This is
the audit trail for "did we actually cover what we meant to cover":

- **Pagination completeness**: `fetchLegistarMatters` keeps paging while
  a page comes back full-size, so a non-full last page is proof the
  loop reached the true end rather than being cut short. `pages_fetched`
  in `runs` makes that checkable after the fact.
- **City coverage**: `not-found` cities are listed explicitly in
  `data/batch-summary.json`, not silently dropped.
- **Anomaly spotting**: an unusually low `matters_fetched` next to peer
  cities is worth a manual check — e.g. Miami's low count turned out to
  be a real, low `MatterId` ceiling (their Legistar tenant appears
  recently established), not a scraping bug.

## Advocacy digest (#6)

```sh
npm run digest -- --days=30
```

Pulls every matched document with an agenda date in the last N days
across all ingested cities, and drafts a public-comment paragraph for
each one via `comment-drafter.ts` — the wording adapts based on whether
the item is a vendor contract (cites cost if found in the title), an
annual technology-use report, or a data-sharing/ICE-related policy item.
Output is a markdown file per run in `data/digest-<date>.md`, grouped by
city, meant to be skimmed and copied into a public-comment period.

## Flock transparency monitor (#3)

```sh
npm run flock-monitor
```

Filters the ingested data to just Flock Safety/Flock Group matches
across every city and reports current status plus status history for
each (via the `status_history` table — every `upsertDocument` call
records a new row whenever a document's status changes between runs,
so re-running `batch` periodically builds a real timeline: e.g.
Introduced → Passed, or Passed → Failed on reconsideration). Exports
`data/flock-transparency-report.json`.

## FOIA compliance parser (#5)

```sh
npm run foia -- --folder=./foia-inbox   # folder is the default, flag is optional
```

Extracts text from every PDF in `foia-inbox/` (via `pdf-parse`), runs it
through the same surveillance-keyword taxonomy used for council agendas,
and flags compliance issues: redaction language, full/partial denial or
exemption claims, denied fee waivers, and — if a same-named `.json`
metadata sidecar gives a request date, response date, and state — whether
the response beat that state's statutory deadline (`compliance.ts`; the
deadline table is approximate and meant to flag responses worth a closer
look, not to be cited as legal fact). Exports `data/foia-compliance-report.json`.

Verified against a real, redacted Cook County Sheriff's Office FOIA
response about Flock Safety (via MuckRock): correctly extracted "Flock
Safety"/"license plate reader" from an 8.5MB real PDF, flagged it as a
partial denial (the file itself is titled "Redacted"), and correctly
computed a 47-business-day response time against Illinois's 5-day
statutory deadline.

## Adding a new source

Sources live in `src/sources/`. Each exports a function that returns
`RawDocument[]` (see `src/types.ts`). `src/sources/legistar.ts` is the
first one; a FOIA-response PDF ingester (for MuckRock exports or files
dropped in a local folder) is the natural next source to add.
