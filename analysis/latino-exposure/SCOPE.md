# Scope: Flock/ALPR camera siting and Latino population exposure (Oakland pilot)

## Research question

Conditional on standard siting rationales (traffic engineering, crime concentration,
arterial/chokepoint geometry), is Flock/ALPR camera density in Oakland systematically
higher in block groups with greater Hispanic/Latino population share?

This is a disparate-impact / spatial-equity question, not a claim about intent. The
design can show correlation robust to observable confounders; it cannot establish that
any city or vendor targeted Latino neighborhoods deliberately.

## Decisions locked in

- **Exposure proxy**: residential ACS Hispanic/Latino population share (block-group
  level, ACS 5-year, table B03002). Chosen over POI-proximity or mobility data because
  it's public, redistributable, and has a well-established precedent in the
  environmental-justice/surveillance-disparity literature.
- **Geography**: Oakland only, as a pilot. It's the only city in this repo with a real
  camera pull already done ([`cameras.json`](../../src/data/generated/cameras.json),
  856 points, fetched 2026-08-13). Multi-city expansion is Phase 2, gated on the pilot
  actually working and on rerunning `overpass.ts` across the ~30 resolved cities in
  [`cities.ts`](../../ingest/src/cities.ts).
- **Deliverable**: standalone Python analysis (data pipeline + regressions +
  diagnostics + written report), not a site feature. Proper spatial-regression
  diagnostics (Moran's I, spatial lag/error models) don't belong in the TS/Vite app.

## Data provenance (read before trusting any result)

Camera coordinates come from OpenStreetMap nodes tagged `surveillance:type=ALPR` —
the same crowdsourced dataset the DeFlock project is built on
([`overpass.ts:73-91`](../../ingest/src/sources/overpass.ts#L73-L91)), not a Flock
corporate feed or a FOIA'd city inventory. This means the *input* camera list is
volunteer-mapped: block groups that are undercounted are ones where fewer OSM
contributors have gone out and tagged cameras, not necessarily ones with fewer
cameras. OSM contributor density itself correlates with income/education
(well-documented in the VGI literature), which could induce a spurious relationship
in either direction. This has to be a named limitation in the writeup, and ideally
checked (see Phase 1, task 6).

## Unit of analysis

**Updated after Phase 0** (originally scoped as block-group primary / tract
robustness — reversed once ACS MOE data came back, see Phase 0 status below):
Census **tract** is the primary unit, Oakland city boundary, 379 tracts in Alameda
County. Block group (353 units within Oakland) is a secondary, finer-resolution
robustness check only, flagged as noisy — see Threats to Validity.

## Variables

**Outcome**: camera count per block group. Count data, plausibly overdispersed →
negative binomial as the primary model, Poisson as a check, OLS on log(count + 1) as a
sensitivity spec. Distance-to-nearest-camera as a continuous alternative outcome for
the spatial-lag/GWR specifications.

**Key regressor**: block-group Hispanic/Latino share (ACS B03002).

**Controls** (all with a stated placement-rationale reason, since the whole point is
to net out the facially race-neutral explanations Flock/cities give):
- Population density (more people → mechanically more plausible camera sites)
- Road classification / arterial-road length per block group (Flock's own marketing
  materials describe siting logic keyed on entry/exit chokepoints and arterial
  corridors — `overpass.ts`'s road fetch already filters to
  motorway/trunk/primary/secondary/tertiary, which is the right feature to reuse here)
- Median household income / poverty rate (ACS)
- Crime rate, if Oakland's open-data portal has geocoded incident data at usable
  resolution — needed because "high crime" is the standard public justification for
  camera placement, so omitting it confounds *any* demographic result
- Distance to downtown/major commercial corridor
- City council district fixed effects (camera funding/placement in Oakland is
  frequently a per-district budget decision, so district FEs absorb a lot of the
  political-process variation)
- Non-Latino-nonwhite share (Black share, Asian share) — needed to check whether an
  effect is Latino-specific or just "nonwhite/lower-income neighborhood" generally
- Land use (residential/commercial/industrial), if parcel data is available

## Econometric approach

1. **Baseline**: negative binomial regression of camera count on Latino share +
   controls, robust/clustered SEs.
2. **Spatial diagnostics**: Moran's I on regression residuals to test for spatial
   autocorrelation (near-certain to be present — crime, roads, and demographics are
   all spatially clustered). If present, plain NB/OLS standard errors are wrong and
   spatial models are required, not optional.
3. **Spatial regression**: spatial-lag and spatial-error specifications (PySAL /
   `spreg`) to correct for (2).
4. **Geographically weighted regression (GWR)** as an exploratory/robustness layer —
   does the Latino-share coefficient vary across Oakland's neighborhoods, or is it
   stable? Useful for figures even if the global model is the headline number.
5. **Geographic discontinuity check**: Oakland council district boundaries are a
   plausible source of quasi-random variation in *budget authority* even when the
   underlying geography (roads, crime) varies continuously across the line — compare
   camera density just inside vs. just outside a Latino-plurality district boundary,
   controlling for arterial presence. Treat as suggestive, not causal — no reason to
   believe district boundaries were drawn independent of demographics.
6. **OSM-coverage sensitivity check**: pull OSM edit/node density (any tag, not just
   cameras) per block group as a proxy for mapper attention, and confirm the headline
   result survives controlling for it. Directly addresses the provenance caveat above.

## Threats to validity (state upfront, don't discover after the fact)

- **Omitted variable bias**: the single biggest risk is that "camera near arterial
  road" and "arterial road near denser/lower-income neighborhood" both being true
  produces a Latino-share correlation with no independent explanatory content. Control
  6 (crime) and the road-density control are the load-bearing pieces here.
- **Reverse causality / simultaneity**: can't distinguish "cameras placed because of
  crime, which correlates with demographics" from "cameras placed because of
  demographics, dressed up as crime response." This design produces a
  correlation-net-of-observables result, not a causal claim on intent.
- **MAUP**: block-group results must be checked against tract-level aggregation
  (Phase 3) before treating a specific coefficient as meaningful.
- **Ecological fallacy**: a block-group correlation says nothing about which
  individuals are exposed; don't let the writeup slide into individual-level language.
- **ACS margin of error / attenuation bias**: confirmed in Phase 0 — Oakland
  block-group Latino-share estimates have a median MOE of 65% of the point estimate
  (72% of block groups exceed 50%); tract-level is better (38% median) but still not
  clean. Primary spec uses tract-level; regressions should use MOE-based
  inverse-variance weights, not plain OLS/NB. Unweighted, MOE-blind estimates would
  suffer classical measurement-error attenuation — biasing the Latino-share
  coefficient toward zero, i.e. an ACS-noise-blind analysis is more likely to
  understate a real effect than manufacture a fake one.
- **Camera dataset undercount / VGI bias**: see provenance section above; check 6 is
  the mitigation, but it can only be partial.

## Phase 0 status (run 2026-08-23)

- **Block-group boundaries**: done. Census cartographic boundary file (`cb_2023_06_bg_500k`)
  clipped to Oakland's place polygon (centroid-within test) → 353 block groups,
  saved to `data/processed/oakland_block_groups.geojson`. No API key needed.
- **Arterial road network**: done. Same Overpass query as
  [`overpass.ts`](../../ingest/src/sources/overpass.ts)'s `fetchRoadNetwork`, run
  directly against Oakland's bbox → 56,514 nodes / 11,449 ways, saved to
  `data/raw/oakland_road_network.json`.
- **Crime data**: done. Oakland's Socrata open-data portal has a live, actively
  updated dataset (`ppgh-7dqv`, "CrimeWatch Data") with point geocoding, not just the
  90-day rolling extracts most of their other "crime" resources turned out to be.
  Pulled 2023-01-01 through 2026-08-01 → 210,098 incidents, 200,445 (95.4%) geocoded,
  saved to `data/raw/oakland_crime_2023_2026.json`. Good coverage on both sides of
  the 2025-12-16 treatment date for Part 2.
- **ACS demographics (Latino share, income, population)**: done, key activated
  2026-08-23. Pulled block-group and tract-level ACS 2023 5-year estimates
  (B03002 Hispanic/Latino, B19013 income, B01003 population) for Alameda County,
  joined to Oakland's 353 block groups →
  `data/processed/oakland_block_groups_acs.geojson`. This also resolved the
  block-group-vs-tract open question:
  - **Block-group Latino-share estimates are too noisy to use alone.** Median
    margin of error is 65% of the point estimate; 72% of Oakland block groups have
    MOE exceeding half the estimate itself (roughly CV ≈ 39%, "low reliability" by
    Census's own reliability convention).
  - **Tract-level is meaningfully better but not clean**: median relative MOE
    drops to 38% (CV ≈ 23%, "medium" reliability), but 28% of tracts still exceed
    the 50%-of-estimate threshold.
  - **Decision: tract-level is the primary geography**, block-group is a
    robustness/finer-resolution check only, with an explicit noise caveat on any
    single block-group's coefficient. This also means Part 1's regressions should
    use weighted least squares (inverse-variance weights from the MOE) rather than
    unweighted OLS/NB, and the writeup needs to name **attenuation bias**: classical
    measurement error in a regressor biases its estimated coefficient toward zero,
    so an unweighted, MOE-blind regression would understate rather than overstate
    any real relationship. Added to the Threats to Validity list below.
  - Primary dataset built: `data/processed/oakland_tracts_acs.geojson`, 116 Oakland
    tracts with boundaries + Latino share + income + population + MOE, ready for
    Phase 1's spatial join. Secondary/robustness dataset:
    `data/processed/oakland_block_groups_acs.geojson`, 353 block groups.

## Empirical finding that changes Part 2, Design A

Before building the retrospective OSM-history panel (Part 2's primary near-term
design), I ran a feasibility check on it directly:
[`src/check_osm_history.py`](src/check_osm_history.py), 120 of Oakland's 856 camera
nodes, pulling each node's full OSM edit history.

**Result: the "OSM tagging date = rough proxy for camera install date" idea in the
original Part 2 scope does not hold up.** First-tagged-as-ALPR dates cluster heavily
around a small number of specific days rather than spreading organically over time —
36 of 120 sampled nodes (30%) were first tagged `ALPR` on the single day
**2024-11-20**, and 47% fall within a five-day window (2024-11-17 to 2024-11-21).
That's a mapper doing a bulk survey/import pass, not 36 cameras independently
installed on the same day. The provenance caveat already written into Part 1 and
Part 2 ("OSM tagging date is a mapper's action, not an installation date") is
confirmed, and it's not a minor-edge-case caveat — it's the dominant pattern in the
sample.

One data point from the original three-node spot-check doesn't hold up either: three
nodes edited within minutes of each other on 2025-12-19 (three days after Oakland's
Flock-agreement passage) looked like it might be a policy-driven mapping response. At
n=120, only 8 nodes (6.7%) have any edit in December 2025, spread across the 1st,
14th, 19th, and 30th — not a single-day spike. Read as background OSM activity, not
evidence either way of a passage-triggered mapping event.

**Consequence for Design A**: a retrospective panel built from first-ALPR-tag dates
would mostly measure when a handful of mappers did survey passes, not when cameras
went in. Using it for a month- or quarter-level event study would attribute bulk
mapping-campaign timing to Flock installation timing — exactly backwards from what
the design needs. **Design A is downgraded from "near-term buildable" to "not viable
at current OSM data resolution."** The prospective-snapshot approach (recurring
Overpass pulls starting now) becomes the *only* sound path to a real installation-date
panel, which means Part 2's DiD is realistically a multi-month-out deliverable, not
something the pilot can produce this quarter. Recommend: start the recurring snapshot
job now regardless (cost is near-zero, and every month of delay is a month of
post-period lost later), but don't plan near-term deliverables assuming a working DiD
result exists yet.

## Phased plan

**Phase 0 — data acquisition**
- Pull Oakland block-group boundaries + ACS B03002 (Hispanic/Latino), B19013 (median
  income), B01003 (population) via the Census API (free, no auth beyond an API key).
- Get Oakland crime incident data (city open-data portal, check availability/recency).
- Reuse `cameras.json` as-is; no new ingest needed for the pilot.
- Pull arterial road network for Oakland via the already-built `fetchRoadNetwork` bbox
  logic in [`overpass.ts`](../../ingest/src/sources/overpass.ts) (or a standalone
  Python Overpass call, to keep this analysis self-contained from the TS ingest tool).

**Phase 1 — spatial join & descriptive (done, run 2026-08-23)**
- Spatial join built in [`src/spatial_join.py`](src/spatial_join.py): camera count,
  arterial road length, and **pre-treatment** crime count (2023-01-01 through
  2025-12-15, deliberately cut off the day before Oakland's Flock passage so this
  control isn't itself downstream of cameras) joined to both tracts (primary) and
  block groups (robustness), by GEOID. Output:
  `data/processed/oakland_{tracts,block_groups}_analysis_table.geojson`.
  - Scope note: `cameras.json`'s 856 cameras were pulled against a bounding-box
    rectangle, not Oakland's actual city polygon — 520 fall genuinely inside city
    limits (confirmed both via the sjoin and an independent polygon-containment
    check), the other 336 are in neighboring jurisdictions the rectangle happened to
    catch. All analysis uses the 520 Oakland-only cameras.
- Descriptives run in [`src/diagnostics.py`](src/diagnostics.py):
  - **Raw bivariate correlation between Latino share and camera density is weak and
    not statistically significant** at tract level (Pearson r=0.050, p=0.59;
    Spearman rho=0.17, p=0.068) or block-group level (r=0.052, p=0.33; rho=0.099,
    p=0.064). Latino-share terciles don't show a monotonic gradient in camera
    density either (tract-level means: low=5.28, mid=4.65, high=5.55 cameras/km²).
  - **This is the marginal/unconditional relationship only — it does not answer
    the research question.** A weak raw correlation is fully consistent with a real
    conditional relationship hiding behind confounders that happen to cancel out
    (e.g., if arterial-road placement correlates negatively with Latino share while
    crime correlates positively, the two could offset in the raw numbers and only
    show up once both are controlled for in Phase 2). Don't over-read this as "no
    effect" — it's the reason Phase 2's controlled regression is necessary, not a
    substitute for it.
  - **Moran's I on camera density**: not significant at tract level (I=0.010,
    p=0.33) but significant at block-group level (I=0.095, p=0.005). Moran's I on
    Latino share itself is strongly significant at both levels (tract I=0.83,
    block-group I=0.69, p=0.001) — demographics are clustered as expected, cameras
    less clearly so. The block-group-level spatial autocorrelation means Phase 2's
    block-group robustness regressions still need spatial-lag/error correction even
    though the tract-level primary spec may not.

**Phase 2 — regression models (done, run 2026-08-23)**
- Built in [`src/models.py`](src/models.py): NB baseline → attenuation-bias
  correction → Moran's I on residuals → spatial lag/error (`spreg`) → GWR (`mgwr`).
  VIF checked separately (all < 2.6, no multicollinearity concern).
- **Headline result: the raw correlation (§Phase 1) is weak, but the controlled
  relationship is large, positive, and robust.** Net of arterial road density,
  income, population density, and pre-treatment crime, tract-level Latino share
  has NB coefficient 2.37 (p < 0.001, HC1 robust SE), surviving spatial-lag
  (β=2.16, p<0.001) and spatial-error (β=1.87, p<0.001) correction, an
  attenuation-bias correction (pushes the estimate *up* to 2.52, not down — see
  below), and block-group-level replication (β=1.82 baseline, both spatial models
  significant). GWR finds the local coefficient positive everywhere in Oakland
  (1.21-2.27), with a near-full-sample optimal bandwidth (113 of 114 tracts) —
  read as a mild, smooth spatial gradient, not sharp neighborhood heterogeneity.
- Mechanism for the raw-vs-controlled reversal: Latino share correlates
  *negatively* with arterial road density (r=-0.32) and income (r=-0.48) in this
  sample — both independently predict fewer cameras — masking the demographic
  relationship until those factors are held fixed.
- Pre-treatment crime rate is **not** significant in either geography (tract
  p=0.555, block group p=0.058) — "responding to crime" does not independently
  explain Oakland's camera placement once other factors are controlled.
- Full writeup with figures: **[report/index.html](report/index.html)**, published
  as a Claude Artifact. Regression tables, methodology, and all limitations
  (correlational-not-causal, ecological fallacy, camera-dataset provenance, ACS
  MOE/attenuation, single-city scope, GWR bandwidth caveat) are written out there
  in full rather than duplicated here.
- **Follow-up (race/class horse race, [`src/race_class_horserace.py`](src/race_class_horserace.py)):**
  added non-Hispanic White/Black/Asian shares (White as omitted reference) and a
  poverty-rate variable to the baseline spec. Latino share remains the only
  statistically robust demographic term; Black share, Asian share, and poverty
  rate are all not significant, and their point estimates aren't even
  consistently signed. Caveat: Black and Asian share have less variance in this
  sample than Latino share, which lowers power to detect an effect on those
  terms — "not significant" is not the same as "ruled out." Full writeup in
  report §6.

**Phase 3 — robustness**
- Tract-level re-run of Phase 2.
- OSM-coverage control (validity check 6).
- District-boundary discontinuity check.

**Phase 4 — writeup**
- Report structured like an applied econometrics paper: research question, data,
  identification strategy and its limits, results, robustness, and an explicit
  "what this does and doesn't show" section aimed at a non-technical reader, since this
  will likely be read by advocacy/policy audiences as well as technical ones.

**Phase 5 — multi-city expansion (done, run 2026-08-23, first batch)**
- Piloted on 4 more cities chosen for confirmed OSM/DeFlock camera coverage and a
  range of Latino shares: El Paso, Fresno, Phoenix, Albuquerque (
  [`src/multi_city.py`](src/multi_city.py)). None have an equivalent to Oakland's
  crime-data feed (checked via Socrata catalog search, domain guesses, ArcGIS Hub
  search — bounded effort, then dropped per decision), so the pooled model
  ([`src/pooled_model.py`](src/pooled_model.py)) omits crime rate for all five
  cities to keep one consistent specification.
- **Finding: Oakland's result does not yet generalize.** A pooled NB model with
  city fixed effects and one shared Latino-share slope finds no significant
  effect (coef=-0.26, p=0.53). Allowing each city its own slope (interaction
  model, per-city SEs via the delta method — not the raw interaction-term
  p-value) shows why: **Oakland is the only city where the slope is itself
  statistically distinguishable from zero** (β=1.95, p<0.001). Albuquerque,
  Fresno, El Paso, and Phoenix range from mildly positive to meaningfully
  negative, none individually significant.
- Candidate explanations, one now resolved: (1) missing crime control in the 4
  new cities. **Resolved by follow-up search** — real geocoded crime feeds
  found for 3 of 4 ([`src/fetch_city_crime.py`](src/fetch_city_crime.py),
  [`src/add_crime_controls.py`](src/add_crime_controls.py)): Fresno (official
  ArcGIS FeatureServer, but stale — only 2022-01 to 2023-07), Albuquerque
  (official ArcGIS MapServer, point-level, but only a rolling ~6-month
  window), Phoenix (CSV feed, but geocoded only to a police grid cell, not a
  point — aggregated via area-weighted join to a separate grid-polygon
  service). El Paso: still nothing found despite an expanded search (general
  web search, the city's ArcGIS Hub portal, an org-wide ArcGIS search, direct
  fetch of the PD's records page) — stays without a crime control.
  Re-running the pooled model on Oakland + the 3 newly-crime-controlled
  cities: **crime rate is itself a significant positive predictor (β=0.267,
  p=0.006), and Oakland's Latino-share effect survives and slightly
  strengthens (β=2.26 vs 1.95 without crime, p<0.001) — ruling out "missing
  crime control" as the explanation for Oakland looking different from the
  other cities.**
- Remaining candidate explanations, not resolved: (2) El Paso's mean tract
  Latino share is 82% (vs Oakland's 26%), leaving little within-city
  comparison group; (3) El Paso has an active council effort to *end* Flock
  agreements (§Part 2) — a different institutional moment than Oakland's
  expansion; (4) Fresno's stale data and Phoenix's grid-resolution crime proxy
  are themselves noisier than Oakland's; (5) genuinely could be
  Oakland-specific. Distinguishing these needs more cities and better-matched
  crime data, not a conclusion from 4-5 cities.
- Full writeup: report §7, Figures 5-6, Table 4.

**Expansion to 10 cities (run 2026-08-23).** Added San Jose, Fort Worth,
Denver, Sacramento, Seattle (chosen via a quick Overpass camera-count
feasibility check; all had strong OSM/DeFlock coverage). Total pooled n =
1,737 tracts across 10 cities.
- **The joint pooled/interaction model stopped numerically converging at 10
  cities.** Seattle's Latino share occupies an unusually narrow real-world
  range (0.6%-26%, vs. 20+ points of spread elsewhere), which makes the joint
  model's Hessian singular once its city dummy and interaction term are added
  alongside 9 others. Fix: per-city independent NB regressions
  ([`pooled_model.py`](src/pooled_model.py)'s `per_city_independent_models`),
  standard practice for this situation, numerically robust, at the cost of no
  single-model cross-city equality test. Also implemented in
  [`multi_city_race_class.py`](src/multi_city_race_class.py) for the
  race/class extension.
- Result unchanged in substance: **Oakland remains the only city with a
  significant Latino-share effect** (β=2.45, p<0.0001). Seattle's raw
  coefficient is largest (9.6) but that's a range artifact — recalibrated to
  P10→P90 implied effect (0.97), it's comparable to Oakland's (1.32) and its
  p-value (0.072) is close to, without clearing, significance.
- Race/class extension across all 10: **Black share now significant and
  positive in 3 cities** (Albuquerque p=0.015, Phoenix p=0.015, Sacramento
  p=0.0001) — the second-most-consistently-replicating signal after Oakland's
  Latino result. Notably, Sacramento's Latino-share coefficient becomes
  significant too (p=0.022) once Black/Asian share and poverty are controlled
  for jointly, vs. not significant in the Latino-only spec — informative
  divergence, not a contradiction (suggests confounding between Sacramento's
  Latino and Black populations in the simpler spec). Asian share and poverty
  rate remain sign-inconsistent across cities, no coherent story. 7/40
  city-variable combinations significant vs. ~2 expected by chance, no
  multiple-comparison correction applied.
- Crime-controlled model (§7) still only covers Oakland/Fresno/Phoenix/
  Albuquerque — San Jose, Fort Worth, Denver, Sacramento, Seattle haven't been
  searched for crime data yet. Natural next step.
- Full writeup: report §7 (updated), §8 (updated), Table 4 (10 rows), Table 5
  (40 rows), Figures 5-6.

**Follow-up: does the race/class horse race (§6, Oakland-only) generalize?**
([`src/multi_city_race_class.py`](src/multi_city_race_class.py)) Pulled
Black/Asian/White share + poverty rate ACS data for the 4 new cities' counties,
pooled all 5 with city FE, and computed per-city implied slopes for Latino,
Black, Asian share, and poverty rate — recalibrated as "effect of moving a
tract from that city's own 10th to 90th percentile," since raw per-unit-share
coefficients aren't comparable across cities with very different real-world
ranges (e.g. Albuquerque's Black share only spans ~0.2%-6%, vs Oakland's
5%-37%). Result: **no single demographic variable or class story generalizes.**
Oakland's own pattern is Latino-share-specific (confirmed again here). But
Albuquerque independently shows a comparably-sized, significant Black-share
effect; Phoenix and El Paso show positive Asian-share effects while Albuquerque
shows a negative one (inconsistent in sign). Poverty rate is not significant
anywhere. 5 of 20 city-variable tests are significant at p<0.05 (chance alone
predicts ~1), suggestive but not confirmatory with no multiple-comparison
correction applied. Full writeup: report §8, Table 5.

## Suggested project layout (not yet created — build starts after this scope is confirmed)

```
analysis/latino-exposure/
├── SCOPE.md                 (this file)
├── data/                    (raw + processed; gitignore raw Census/crime pulls if large)
├── notebooks/               (exploratory work)
├── src/
│   ├── acquire.py           (Census API, crime portal, road network pulls)
│   ├── acquire_camera_history.py  (OSM node version-history pull -> panel of
│   │                                camera tagging dates per block group)
│   ├── spatial_join.py      (camera-to-block-group join, arterial density calc)
│   ├── models.py            (NB baseline, spatial lag/error, GWR)
│   ├── did_models.py        (event study, Callaway-Sant'Anna / Sun-Abraham DiD)
│   └── diagnostics.py       (Moran's I, VIF, residual maps, pre-trend checks)
├── requirements.txt         (geopandas, pysal/spreg, statsmodels, census, mgwr,
│                              linearmodels or `differences`/`csdid`-equivalent for DiD)
└── report/                  (final writeup + figures)
```

---

# Part 2: Difference-in-differences design

The cross-sectional design above (Phases 0-4) can only ever produce "correlated with,
net of observables" — it cannot rule out an unobserved confound that happens to track
both Latino share and camera placement. A DiD design adds a second axis of variation
(time, around a real policy event) that a pure cross-section doesn't have, and gets
closer to a causal claim about *marginal* siting decisions, if not the full stock of
cameras.

## Why this is actually feasible here, not just aspirational

Two pieces of data already exist in this repo that a DiD needs and that most "does
surveillance target minorities" studies don't have:

1. **Real treatment timing.** [`digest.json`](../../src/data/generated/digest.json)
   and [`surveillance-matters.json`](../../src/data/generated/surveillance-matters.json)
   carry `agenda_date`/`intro_date` plus a `status` field (`Passed` / `Failed` /
   `Withdrawn` / `Filed`) pulled from city council Legistar records. For Oakland
   specifically: a Flock contract **Failed** on agenda date 2025-12-02, then a
   "Community Safety Cameras Policy And FLOCK Agreement" **Passed** on 2025-12-16.
   That passage date is a real, externally-dated treatment event, not something we're
   inferring from the camera data itself.
2. **Cross-city variation in direction, not just timing.** Some cities in the
   `surveillance-matters.json` data are moving the opposite way — e.g. El Paso has a
   pending item to make the city "refrain from renewing any existing agreements ...
   with Flock Group Inc." That gives adopting and rejecting/exiting cities in the same
   dataset, which is the actual control-group variation a DiD needs (not just "some
   cities happen to have no Flock").

## What's missing and has to be built: a camera-count *panel*

`cameras.json` is a single snapshot (`fetchedAt: 2026-08-13`) — a cross-section, not a
time series. A DiD needs camera count (or presence) observed at multiple points in
time, before and after the treatment date. Two ways to get that, in order of
preference:

- **Retrospective, via OSM edit history (primary plan).** Every OSM node carries its
  own version history with timestamps, retrievable from the standard OSM API
  (`GET /api/0.6/node/{id}/history`) or a full-history Overpass query. Pulling the
  first-version timestamp for each of the 856 Oakland ALPR nodes reconstructs a
  "cumulative distinct cameras tagged by month" series per block group. This is new
  engineering (a script, not present in `ingest/` today — the closest existing piece
  is the plain `fetchAlprCameras` call in
  [`overpass.ts`](../../ingest/src/sources/overpass.ts), which only returns current
  state, not history).
- **Prospective, via repeated snapshots (fallback/supplement).** Re-run the existing
  Overpass camera pull on a recurring schedule going forward and accumulate genuine
  post-period observations. Cleaner data, but only useful once enough post-period time
  has passed — a multi-month wait, not something that produces results this quarter.
  Worth starting now regardless, since retrospective OSM-history timestamps carry the
  caveat below and a prospective series doesn't.

**Caveat that has to be named, same family as the Part 1 provenance issue**: OSM
*tagging* date is a mapper's action, not an *installation* date — a camera physically
installed in 2024 might not get tagged until 2026 if no volunteer surveyed that block
yet. This means the retrospective panel has right-censored, lagged "installation"
timing that could itself correlate with neighborhood mapper activity. Same mitigation
as Part 1: control for local OSM edit density as a proxy for mapper attention, and
treat any month-level precision in the retrospective series skeptically — quarter or
half-year bins are more defensible than monthly ones given likely tagging lag.

## Specification

**Design A — single-city event study (Oakland). Status: NOT VIABLE at current data
resolution** — see "Empirical finding" above. Kept here as the intended spec for
when a real panel exists (prospective snapshots, accumulating from 2026-08-23
onward), not as something to run today.

```
CameraCount_bg,t = β0 + β1·Post_t + β2·LatinoShare_bg + β3·(Post_t × LatinoShare_bg)
                    + block-group FE + quarter FE + controls_bg,t + ε
```

- `Post_t` = 1 for quarters on/after 2025-12-16 (Oakland's Flock agreement passage).
- `β3` is the coefficient of interest: does the post-adoption acceleration in camera
  count differ by block-group Latino share?
- Run as an **event-study** (leads and lags around the passage date, not just a single
  Post dummy) so the pre-period coefficients can be inspected directly for parallel
  trends, rather than assumed.
- Controls: same set as Part 1 (arterial road density, income, crime, population
  density), interacted with `Post_t` where a control itself plausibly changed
  post-adoption (e.g. if crime rates shifted).

**Design B — multi-city staggered DiD (Phase 2 of this part, gated on expanding
camera geocoding beyond Oakland per Part 1's Phase 5)**

- Treatment = city-level Flock passage date from `surveillance-matters.json` /
  `digest.json` (`status == "Passed"`, filtered to Flock-specific keywords).
- Comparison group = cities where equivalent legislation `Failed`/was `Withdrawn`, or
  where a Flock-exit item is pending (El Paso-style), plus never-treated cities.
- Staggered timing across ~30 cities means a naive two-way-fixed-effects regression is
  the wrong tool — recent econometrics (Goodman-Bacon 2021) shows TWFE can put
  negative weight on some treatment effects when timing varies and effects are
  heterogeneous. Use a heterogeneity-robust estimator instead: Callaway & Sant'Anna
  (2021) group-time ATT, or Sun & Abraham (2021) interaction-weighted estimator
  (`did` package in R, or `differences`/`csdid`-equivalent in Python).
- Triple-difference version: interact the city-level Post×Treated term with
  block-group Latino share, to ask the Part-1 question (does the *effect* of adoption
  fall disproportionately on Latino block groups) rather than just the Part-2 question
  (did adoption increase camera counts at all).

## Threats to validity specific to the DiD design

- **Parallel trends is an assumption, not a fact** — must be checked via the
  event-study pre-period coefficients (Design A) or Callaway-Sant'Anna's
  pre-treatment placebo estimates (Design B), not asserted.
- **Anticipation effects**: a contract "Failed" in Oct/Dec 2025 before "Passing" days
  later on a re-vote means the policy process itself was contested in real time —
  departments sometimes begin procurement/installation before final passage, or the
  press attention around a contested vote could itself change reported/tagged camera
  counts independent of actual installs. Check whether pre-passage OSM tagging shows
  any bump around the Oct 2025 failed vote.
- **Staggered-timing TWFE bias** (Design B only) — addressed by using
  Callaway-Sant'Anna/Sun-Abraham rather than plain TWFE, per above.
- **Selection into treatment timing**: if cities/council districts with faster-growing
  or already-larger Latino populations are also the ones that pass Flock contracts
  sooner (or later), timing itself is endogenous to demographics — this is exactly
  what the DiD is trying to detect, but it means "control cities" must be chosen for
  comparable underlying trends, not just convenience.
- **Legislative status ≠ operational reality**: `Passed` means the city council
  approved a contract/policy, not that cameras went live that day, and `Failed` for a
  *renewal* item doesn't necessarily mean pre-existing cameras were removed. Treatment
  timing from this data is a proxy for the policy shock, and the panel's actual camera
  counts are the check on whether it corresponds to a real change in the ground truth.

## How Part 2 folds into the phased plan

- Add to **Phase 0**: build the OSM node-history puller (new script,
  `src/acquire_camera_history.py`) and start a recurring prospective snapshot job now.
- Add to **Phase 2**: run Design A (Oakland event study) alongside the cross-sectional
  models — same data, additional temporal dimension.
- Design B multi-city DiD stays tied to Part 1's Phase 5 (multi-city expansion) — no
  point building it before more cities have geocoded camera panels.

---

## Prospective camera-count panel (started 2026-08-23)

The planned cloud-based monthly snapshot routine was blocked on GitHub App
access not being connected (`RemoteTrigger` create returned 401: "Connect your
GitHub account before saving a routine that uses a GitHub repository"). Per
decision, skipped the cloud automation and run
[`src/snapshot_oakland_cameras.py`](src/snapshot_oakland_cameras.py) locally
on request instead — no GitHub needed, saves straight into this worktree.
First snapshot: **2026-08-23, 880 cameras** (vs. 856 in the original
2026-08-13 pull — 24 more tagged in the intervening ~10 days), in
`data/raw/oakland_camera_snapshots/2026-08-23.json` with a running
`manifest.csv`. Ask for this to be re-run periodically (there's no automatic
schedule) to keep building the installation-date panel Part 2's DiD design
needs. Still subject to the same OSM-tagging-lag caveat as everything else in
Part 2 — a rising count over time could reflect either real installs or
delayed mapper attention, and can't be told apart from this data alone.

## Expansion to 15 cities + 6 more crime feeds (run 2026-08-23)

**Bug fix, important**: discovered and fixed a real templating bug in
[`report/build_report.py`](report/build_report.py) — double-brace `{{...}}`
placeholders (meant as a defensive habit) were actually being escaped to
literal text by the enclosing Python f-strings, so **Tables 4 and 5 had been
silently rendering as literal Python code instead of data in every published
version until this fix**. Verified fixed: 101 real `<tr>` rows now render.
Worth remembering: never use `{{ }}` inside an f-string when the goal is
evaluation — only `{ }`.

**Crime data found for 4 more cities** ([`src/fetch_city_crime_batch2.py`](src/fetch_city_crime_batch2.py),
[`src/add_crime_controls_batch2.py`](src/add_crime_controls_batch2.py)):
Fort Worth (official ArcGIS point layer, 625k incidents, 2016-2026), Denver
(official ArcGIS point layer, attribute lat/lon not geometry, 376k incidents,
2021-2026), Sacramento (official ArcGIS point layer, but only calendar-year
2025 — a single-year snapshot), Seattle (official Socrata feed, 1.16M
incidents 2008-2026 after filtering pre-2008 date errors and
`-1.0`/`"REDACTED"` location sentinels). San Jose has a real feed but only
block-range address strings, not points — skipped rather than geocoding
thousands of addresses (same call as El Paso). 6 of 8 crime-controlled models
converge (Oakland, Albuquerque, Denver, Fresno, Phoenix, Seattle); Fort Worth
and Sacramento's per-city models hit a singular-covariance error with the
crime term added and are excluded from that specific comparison.

**5 more cities added** ([`src/multi_city.py`](src/multi_city.py)): Dallas,
Kansas City, San Diego, Columbus, Charlotte — chosen via the same Overpass
camera-count feasibility check as before. Total now 15 cities, ~2,900 tracts.

**Updated findings**:
- Latino-only spec (§7): Oakland remains the only individually-significant
  city (β=2.45, p<0.0001). San Diego (p=0.058) and Seattle (p=0.072) are now
  both marginal — closer than the pure 10-city read suggested.
- Crime-controlled spec: Oakland's effect is essentially unchanged with crime
  added (β=2.37 vs 2.45 without) — still rules out missing-crime-control as
  the explanation. Crime rate itself is a large significant predictor in
  Fresno and Phoenix (read cautiously — their crime data is stale/grid-
  approximated respectively), not in Albuquerque, Denver, Oakland, or Seattle.
- **Race/class spec (§8) — the joint pooled model actually converges at 15
  cities** (unlike the Latino-only spec): pooled across all cities with one
  shared slope, **Asian share is significant and positive** (β=1.12,
  p<0.001). Per-city: Asian share replicates in 4 cities (Charlotte, Dallas,
  San Diego, Seattle, all positive — no sign reversals, unlike the earlier
  10-city read). Black share replicates in 3 (Albuquerque, Phoenix,
  Sacramento, all positive). Latino share replicates in 2 more beyond Oakland
  (Sacramento, San Diego) once other race shares are controlled for jointly —
  informative divergence from §7, not a contradiction. Poverty rate
  significant in 4 cities, split 3-positive/1-negative — still no coherent
  class story. 14/60 city-variable tests significant (~4.7x the ~3 expected
  by chance), no multiple-comparison correction applied.
- Numerical note: per-city independent models remain the robust default
  (joint models still fail for the pure Latino-only spec and for 2 of 8
  crime-controlled cities); wrap every per-city fit in try/except so one
  city's non-convergence doesn't kill the whole run.

Full writeup: report §7, §8 (rewritten), Tables 4-5, Figures 5-6, updated
abstract and conclusion.

**Figure 7 added** ([`report/build_race_class_matrix_figure.py`](report/build_race_class_matrix_figure.py)):
a city x variable dot-matrix visualizing all 60 of Table 5's results at a
glance (dot size = implied P10-P90 effect, filled = significant, colored by
sign, cities sorted by number of significant cells). Makes the Asian-share
column's four filled dots (all one color, no reversals) and San Diego's
three-significant-cells row visible immediately, versus reading 60 table
rows one at a time.

## Bayesian hierarchical model (run 2026-08-23)

Built to resolve the pooled-vs-per-city tension running through §7-§8: a
single pooled slope loses real city variation (and for the Latino-only spec
never converged); separate per-city regressions are numerically robust but
treat a noisy, small city (Seattle, narrow Latino-share range) as equally
trustworthy as a well-supported one (Oakland).

**Model** ([`src/hierarchical_model.py`](src/hierarchical_model.py), PyMC/NUTS):
tracts nested in 15 cities, negative-binomial likelihood. Latino share gets a
random intercept AND random slope by city (independent, non-centered
parameterization — not a correlated 2D normal via LKJ, since 15 groups can't
identify a full covariance structure). Black share, Asian share, poverty
rate, and controls (arterial, income, density) are population-level
(fixed-effect) only, for the same reason — can't give every one of 4
demographic variables its own random slope with only 15 groups.

**Diagnostics**: max R-hat 1.003, min ESS 1872, 0 divergent transitions
(4 chains × 1500 tune + 1500 draws, ~2933 tracts). Clean.

**Key findings**:
- Population-average Latino-share slope: 0.27, 94% CI [-0.51, 1.04] —
  includes zero.
- **SD of the Latino-share slope across cities: 1.34, 94% CI [0.82, 2.07] —
  clearly excludes zero.** This is the headline result: there IS real,
  credible city-to-city heterogeneity in this effect (not just noise), even
  though the population mean itself is indistinguishable from zero. Neither
  "universal effect" nor "no effect anywhere" is accurate; "some cities
  (Oakland, San Diego) show a real effect, others don't, and they average out
  near zero" is what the model actually estimates.
- **Asian share confirmed**: 1.42, 94% CI [0.82, 2.02], excludes zero —
  matches §8's simpler pooled-NB result via a completely different method.
- **Poverty rate reversal**: 0.79, 94% CI [0.04, 1.54], excludes zero
  (barely — lower bound just above 0) and POSITIVE. §8's simpler pooled model
  found poverty NOT significant (p=0.453). Not a contradiction: this model's
  random intercepts separate each city's own baseline camera intensity from
  the poverty-camera relationship, reducing confounding with unmodeled
  city-level differences. Read as suggestive support for a real, modest,
  positive effect — not proof, given how close to zero the lower bound sits.
- Black share still not significant at population level (0.18, CI includes
  zero). Density robustly negative, as in every earlier spec.
- Per-city shrunk (partially-pooled) Latino-share estimates with 94% CI
  clearly excluding zero: **San Diego** (1.80, [1.17, 2.45]), **Oakland**
  (1.70, [0.67, 2.79]), **San Jose** (1.38, [0.42, 2.32]) — positive; and
  **Phoenix** (-1.80, [-2.59, -1.01]) — negative. All other cities' shrunk
  estimates include zero.

**A real bug caught and fixed while building the shrinkage figure**: the
first draft of [`report/build_shrinkage_figure.py`](report/build_shrinkage_figure.py)
compared the hierarchical model's Latino-share slope (estimated jointly with
Black share, Asian share, and poverty rate as covariates) against the
Latino-only per-city estimates from `pooled_results.json` — an apples-to-oranges
comparison, since different adjustment sets produce different coefficients
for reasons that have nothing to do with pooling. Fixed to compare against
`multi_city_race_class_results.json`'s Latino-share estimates (same
covariates as the hierarchical model). Worth remembering for any future
shrinkage/comparison plot: always match the covariate set between the two
things being compared.

**Figure 8** (shrinkage plot): visualizes exactly this — Seattle's wildly
unstable per-city estimate (9.6) shrinks to ~0.6 under partial pooling;
Oakland and San Diego, both well-supported by their own data, barely move.

Full writeup: report §9 (new section), Table 6, Figure 8, updated abstract
and conclusion.

## Final polish pass (run 2026-08-24)

Full "finished product" audit requested: regenerate every graph fresh and
proofread every section for staleness/consistency.

**Environment bug found and fixed**: installing PyMC/ArviZ (for the
hierarchical model) had silently upgraded numpy to 2.5, which broke numba →
libpysal → `build_figures.py` (GWR/spatial models) with an import error.
Fixed by pinning `numpy<2.5` (numba 0.67.0, the latest release, still doesn't
support numpy 2.5). All figures regenerated after the fix and confirmed
byte-for-byte/number-for-number identical to the pre-fix versions — the
bug only affected re-running the pipeline, not any published numbers.
[`requirements.txt`](requirements.txt) updated with the pin and a comment
explaining why, plus `python-dateutil`, `pymc`, `arviz` which were missing
from it despite being load-bearing.

**Stale text found and fixed** (all written when this was an Oakland-only
report, never updated as the scope grew):
- Report subtitle and masthead "Geography" field still said "Oakland,
  California" / "Oakland, CA (pilot)" — now reflects all 15 cities.
- A Limitations bullet ("Single city, single snapshot... does not generalize
  to other cities") directly contradicted §§7-9, which are the whole point of
  the report by that point. Replaced with limitations that actually still
  apply (§4's spatial/attenuation diagnostics are Oakland-only; crime data
  covers 8 of 15 cities with only 6 converging; no multiple-comparison
  correction anywhere).
- §11 (DiD) said the prospective snapshot panel "has not yet started" — false;
  a second Oakland snapshot was pulled 2026-08-23 (880 cameras, up from 856).
  Updated to state the one data point honestly (not yet a usable panel, but
  started).
- Footer only listed the original Oakland-era source files/scripts and named
  Oakland's crime feed as the only crime source. Updated to list all the
  multi-city scripts and all 8 cities with crime data.
- §1 Introduction never previewed that the paper grows into a 15-city,
  multi-method analysis — added a roadmap paragraph.

Full pipeline re-run end to end after the numpy fix
(`build_figures.py` → `race_class_horserace.py` → `pooled_model.py` →
`multi_city_race_class.py` → all figure-build scripts) confirmed every
number in the report is reproducible from the current source data. The
hierarchical model (expensive, ~9 min MCMC) was not rerun since nothing
about the underlying data changed and its diagnostics were already clean.

## Open questions for next session

Resolved in Phase 0 (kept here, struck through, for the record):
- ~~Does Oakland's open-data portal have crime incidents at usable geographic
  resolution and recency?~~ Yes — `ppgh-7dqv`, 210k geocoded incidents 2023-2026.
- ~~Census API key needed~~ Obtained and activated 2026-08-23.
- ~~Is block-group or tract the right primary unit?~~ Tract, per the MOE check above.
- ~~Does OSM's node history API return usable version timestamps~~ Yes, but the
  timestamps reflect mapper survey passes, not installations — this answered the
  question in the negative direction (Design A not viable), which is itself the
  answer.

Still open:
- Confirm whether the Dec 2025 "Failed" → "Passed" sequence in `digest.json` for
  Oakland is two votes on the same underlying contract (re-vote) or two different
  proposals — changes how the treatment date and any anticipation-effect check should
  be framed. (Needs a manual read of the two Legistar items' full text/URLs, not an
  API call — worth doing before Design A is ever revisited.)
- Start the recurring prospective Overpass snapshot job (cadence TBD — monthly is
  probably the right default) so a real installation-date panel starts accumulating
  now rather than whenever this is next picked up.
- Phase 1 (spatial join) hasn't started yet: joining `cameras.json` to the tract
  boundaries in `oakland_block_groups_acs.geojson`, computing arterial road length
  per tract from `oakland_road_network.json`, and joining crime counts from
  `oakland_crime_2023_2026.json`.
