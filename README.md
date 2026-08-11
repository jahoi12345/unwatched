# Unwatched

A directory of anti-surveillance tools — camera-avoidance routing, crowdsourced surveillance
mapping, facial-recognition resistance, cell-site simulator detection, and FOIA/records
infrastructure — plus a home for new tools built to fill gaps in that space.

Built with Vite + React + TypeScript for rapid prototyping.

## Project structure

```text
/
├── src/
│   ├── data/tools.ts   # tool directory data (categories + entries)
│   ├── styles/global.css
│   ├── App.tsx         # link-hub homepage (search + category filter)
│   └── main.tsx
└── package.json
```

Adding a tool to the directory is just adding an entry to `src/data/tools.ts`.

## Commands

| Command           | Action                                       |
| :----------------- | :-------------------------------------------- |
| `npm install`       | Installs dependencies                         |
| `npm run dev`       | Starts local dev server at `localhost:5173`   |
| `npm run build`     | Type-checks and builds production site to `./dist/` |
| `npm run preview`   | Previews the build locally                    |
