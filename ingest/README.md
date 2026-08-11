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

## Adding a new source

Sources live in `src/sources/`. Each exports a function that returns
`RawDocument[]` (see `src/types.ts`). `src/sources/legistar.ts` is the
first one; a FOIA-response PDF ingester (for MuckRock exports or files
dropped in a local folder) is the natural next source to add.
