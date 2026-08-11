# Unwatched

A directory of anti-surveillance tools — camera-avoidance routing, crowdsourced surveillance
mapping, facial-recognition resistance, cell-site simulator detection, and FOIA/records
infrastructure — plus a home for new tools built to fill gaps in that space.

## Project structure

```text
/
├── src/
│   ├── data/tools.ts       # tool directory data (categories + entries)
│   ├── layouts/Layout.astro
│   ├── styles/global.css
│   └── pages/index.astro   # link-hub homepage
└── package.json
```

Adding a tool to the directory is just adding an entry to `src/data/tools.ts`.

## Commands

| Command           | Action                                       |
| :----------------- | :-------------------------------------------- |
| `npm install`       | Installs dependencies                         |
| `npm run dev`       | Starts local dev server at `localhost:4321`   |
| `npm run build`     | Builds production site to `./dist/`           |
| `npm run preview`   | Previews the build locally                    |
